"""
CBETAfetch 2.0 - FastAPI REST API & SSE Event Stream Routes
Supports both modern RESTful endpoints (/api/*) and backward-compatible endpoints.
"""

import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field

from core.id_parser import parse_id_list
from core.downloader import SutraDownloader, DEFAULT_BASE_URL, DEFAULT_TEXT_PACK_URL
from core.processor import process_project, process_cbeta_text_pack, organize_downloaded_artifacts
from core.converter import convert_directory_to_md
from core.headings import format_md_headings_in_directory
from core.job_engine import JobEngine, JobStatus, JobInfo
from core.diagnostics import SystemDiagnostics
from core.xml_repo import clone_or_update_xml_repo, get_xml_repo_status, DEFAULT_XML_P5_REPO
from core.preset_manager import PresetManager, PresetModel, DEFAULT_BUDDHIST_PRESETS
from core.update_checker import get_all_remote_updates
from core.xml_to_obsidian import convert_xml_directory_to_obsidian, convert_xml_file_to_obsidian_md

router = APIRouter()

# Global engine references configured during app creation
job_engine: JobEngine = JobEngine()
base_dir: str = os.getcwd()
preset_manager: PresetManager = PresetManager(storage_dir=os.path.join(base_dir, "data", "presets"))


# --- Pydantic Request Models ---

class DownloadPayload(BaseModel):
    id_list: str = Field(..., description="Newline or comma separated IDs or ranges e.g. T1585, T1500-T1505")
    dest_dir: str = Field(default="./downloads", description="Destination directory")
    example_url: Optional[str] = None
    formats: List[str] = Field(default=["txt"], description="List of formats: txt, html, epub, mobi, pdf, docx, odt, docusky, text-with-notes")
    html_url: Optional[str] = None
    pdf_url: Optional[str] = None
    epub_url: Optional[str] = None
    mobi_url: Optional[str] = None
    docx_url: Optional[str] = None
    odt_url: Optional[str] = None
    docusky_url: Optional[str] = None
    text_notes_url: Optional[str] = None


class ProcessPayload(BaseModel):
    project_dir: str = Field(default="./downloads", description="Directory containing downloaded files or zips")
    output_dir: Optional[str] = Field(default=None, description="Optional custom output directory")
    remove_zip: bool = Field(default=False, description="Remove zips after extraction")


class ConvertMdPayload(BaseModel):
    project_dir: str = Field(default="./downloads", description="Directory containing .txt files to convert")
    auto_heading: bool = Field(default=True, description="Apply H2 headings")
    remove_source: bool = Field(default=True, description="Delete .txt files after conversion")


class FormatHeadingsPayload(BaseModel):
    target_dir: Optional[str] = None
    project_dir: Optional[str] = None


class CompleteProcessPayload(BaseModel):
    edition: str = Field(default="txt", description="'txt' for zip pack or 'xml' for git repo")
    dest_dir: str = Field(default="./downloads", description="Directory for download and extraction")
    pack_url: str = Field(default=DEFAULT_TEXT_PACK_URL, description="URL of cbeta-text.zip")
    xml_repo_url: str = Field(default="https://github.com/cbeta-org/xml-p5", description="Git URL for CBETA TEI P5 XML repo")
    shallow: bool = Field(default=True, description="Shallow clone (--depth 1)")
    output_dir: Optional[str] = None
    convert_md: bool = True
    auto_heading: bool = True


class XmlSyncPayload(BaseModel):
    repo_url: str = Field(default="https://github.com/cbeta-org/xml-p5", description="Git URL of CBETA TEI P5 XML")
    dest_dir: str = Field(default="./downloads-xml", description="Local checkout path")
    shallow: bool = Field(default=True, description="Use shallow clone --depth 1")
    branch: Optional[str] = Field(default=None, description="Specific branch to clone")


class XmlToObsidianPayload(BaseModel):
    xml_dir: str = Field(default="./downloads-xml", description="Source XML directory containing CBETA .xml files")
    output_dir: str = Field(default="./complete", description="Output Obsidian Markdown directory")
    include_page_marks: bool = Field(default=False, description="Include page tags like 〔T0555c〕")
    include_line_anchors: bool = Field(default=False, description="Include line tags like ^001")


class PipelinePayload(BaseModel):
    id_list: str = Field(..., description="Sutra IDs or ranges to process through the full pipeline")
    dest_dir: str = Field(default="./downloads", description="Download cache directory")
    output_dir: Optional[str] = Field(default=None, description="Custom completed output directory")
    formats: List[str] = Field(default=["txt"], description="Download formats")
    remove_zip: bool = Field(default=True, description="Clean up zip archives after processing")
    auto_heading: bool = Field(default=True, description="Apply H2 headings to Markdown")



# --- UI & Static Routes ---

@router.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(base_dir, "templates", "index.html")
    if os.path.isfile(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>CBETAfetch 2.0</h3><p>Template file not found.</p>", status_code=404)


# --- System Status & Diagnostics ---

@router.get("/api/status")
async def get_system_status():
    active_job = job_engine.get_active_job()
    return {
        "status": "ready" if not active_job else "busy",
        "active_job": active_job.to_dict() if active_job else None,
        "total_jobs": len(job_engine.jobs)
    }


@router.get("/api/config")
async def get_config():
    return {
        "base_dir": base_dir,
        "default_download_dir": os.path.join(base_dir, "downloads"),
        "default_complete_dir": os.path.join(base_dir, "complete"),
        "default_base_url": DEFAULT_BASE_URL,
        "default_pack_url": DEFAULT_TEXT_PACK_URL
    }


@router.get("/api/remote/updates")
async def get_remote_updates_endpoint(
    zip_url: str = DEFAULT_TEXT_PACK_URL,
    git_url: str = "https://github.com/cbeta-org/xml-p5",
    local_xml_dir: Optional[str] = "./downloads-xml"
):
    """
    Fetch the last modified timestamps and metadata for both the ZIP pack and Git repo.
    """
    return get_all_remote_updates(zip_url=zip_url, git_url=git_url, local_xml_dir=local_xml_dir)


@router.get("/api/system/self-test")
async def run_self_test():
    report = SystemDiagnostics.run_all_checks(base_dir=base_dir, job_engine=job_engine)
    return report.to_dict()


# --- Job Management ---

@router.get("/api/jobs")
async def list_jobs():
    return job_engine.list_jobs()


@router.get("/api/jobs/{job_id}")
async def get_job_details(job_id: str):
    job = job_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    success = job_engine.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already stopped")
    return {"status": "cancelled", "job_id": job_id}


# --- SSE Streaming Logs ---

@router.get("/logs")
@router.get("/api/logs/stream")
async def stream_logs():
    """
    Server-Sent Events endpoint streaming global execution logs.
    Compatible with legacy CBETAfetch frontend polling.
    """
    async def event_generator():
        last_idx = 0
        try:
            while True:
                with job_engine.lock:
                    total_len = len(job_engine.global_logs)
                    # Protect against ring-buffer truncation where last_idx > total_len
                    if last_idx > total_len:
                        last_idx = max(0, total_len - 50)

                    if last_idx < total_len:
                        new_logs = job_engine.global_logs[last_idx:total_len]
                        last_idx = total_len
                        yield f"data: {json.dumps(new_logs)}\n\n"

                await asyncio.sleep(0.4)
        except (asyncio.CancelledError, GeneratorExit):
            # Client disconnected, terminate generator cleanly
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --- Core Action Routes ---

@router.post("/download")
@router.post("/api/download")
async def start_download(payload: DownloadPayload):
    ids = parse_id_list(payload.id_list)
    if not ids:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No valid IDs provided"})

    dest_dir = os.path.abspath(payload.dest_dir)
    formats = payload.formats or ["txt"]

    format_urls = {}
    if payload.html_url:
        format_urls["html"] = payload.html_url
    if payload.pdf_url:
        format_urls["pdf"] = payload.pdf_url
    if payload.epub_url:
        format_urls["epub"] = payload.epub_url
    if payload.mobi_url:
        format_urls["mobi"] = payload.mobi_url
    if payload.docx_url:
        format_urls["docx"] = payload.docx_url
    if payload.odt_url:
        format_urls["odt"] = payload.odt_url
    if payload.docusky_url:
        format_urls["docusky"] = payload.docusky_url
    if payload.text_notes_url:
        format_urls["text-with-notes"] = payload.text_notes_url

    base_url = None
    if payload.example_url and "/download/" in payload.example_url:
        base_url = payload.example_url.split("/download/")[0] + "/download/"

    def task(job: JobInfo, log):
        log(f"Starting download task for {len(ids)} sutras...")
        log(f"Target formats: {', '.join(formats)}")
        log(f"Destination: {dest_dir}")
        downloader = SutraDownloader(download_dir=dest_dir)

        def check_cancel_callback(msg):
            if job.is_cancelled():
                downloader.cancel()
            log(msg)

        summary = downloader.download_from_ids(
            ids=ids,
            formats=formats,
            base_url=base_url,
            format_urls=format_urls,
            progress_callback=check_cancel_callback
        )
        if job.is_cancelled():
            log("Download cancelled by user.")
        else:
            log(f"Download finished: {summary.succeeded} succeeded, {summary.failed} failed.")

    job = job_engine.submit_task("download", task, metadata={"ids_count": len(ids), "formats": formats})
    return {"status": "started", "job_id": job.job_id}


@router.post("/process")
@router.post("/api/process")
async def start_process(payload: ProcessPayload):
    project_dir = os.path.abspath(payload.project_dir)
    if not os.path.exists(project_dir):
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Project directory not found: {project_dir}"})

    def task(job: JobInfo, log):
        log(f"Starting process & combine task on {project_dir}...")
        files = process_project(
            working_dir=project_dir,
            output_dir=payload.output_dir,
            remove_zip=payload.remove_zip,
            logger=log
        )
        log(f"Processed {len(files)} scripture(s) into complete directory.")

    job = job_engine.submit_task("process", task, metadata={"project_dir": project_dir})
    return {"status": "started", "job_id": job.job_id}


@router.post("/convert_md")
@router.post("/api/convert_md")
async def start_convert_md(payload: ConvertMdPayload):
    target_dir = os.path.abspath(payload.project_dir)
    if not os.path.exists(target_dir):
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Target directory not found: {target_dir}"})

    def task(job: JobInfo, log):
        log(f"Starting Markdown conversion on {target_dir}...")
        count = convert_directory_to_md(
            target_dir=target_dir,
            auto_heading=payload.auto_heading,
            remove_source=payload.remove_source,
            logger=log
        )
        log(f"Markdown conversion completed: {count} files converted.")

    job = job_engine.submit_task("convert_md", task, metadata={"target_dir": target_dir})
    return {"status": "started", "job_id": job.job_id}


@router.post("/format_headings")
@router.post("/api/format_headings")
async def start_format_headings(payload: FormatHeadingsPayload):
    target = payload.target_dir or payload.project_dir
    if not target:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing target_dir or project_dir"})

    abs_target = os.path.abspath(target)
    if not os.path.exists(abs_target):
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Path not found: {abs_target}"})

    def task(job: JobInfo, log):
        log(f"Formatting H2 headings in {abs_target}...")
        count = format_md_headings_in_directory(abs_target, logger=log)
        log(f"Headings formatting completed. Modified {count} files.")

    job = job_engine.submit_task("format_headings", task, metadata={"target": abs_target})
    return {"status": "started", "job_id": job.job_id}


@router.post("/complete_process")
@router.post("/api/complete_process")
async def start_complete_process(payload: CompleteProcessPayload):
    dest_dir = os.path.abspath(payload.dest_dir)

    # Route based on edition: "xml" or "txt"
    if payload.edition.lower() == "xml":
        repo_url = payload.xml_repo_url or DEFAULT_XML_P5_REPO

        def xml_task(job: JobInfo, log):
            log(f"啟動 CBETA TEI P5 XML 全藏庫同步作業...")
            log(f"遠端 Repo: {repo_url}")
            log(f"本地目標: {dest_dir}")
            res = clone_or_update_xml_repo(
                repo_url=repo_url,
                target_dir=dest_dir,
                shallow=payload.shallow,
                progress_callback=log,
                stop_event=job._cancel_event
            )
            if res.success:
                log(f"XML 全藏庫同步圓滿完成！Commit: {res.commit_hash}")
            else:
                log(f"XML 同步失敗或已取消: {res.message}")

        job = job_engine.submit_task("xml_sync", xml_task, metadata={"dest_dir": dest_dir, "repo_url": repo_url})
        return {"status": "started", "job_id": job.job_id, "edition": "xml"}

    # Default to TXT pack
    pack_url = payload.pack_url or DEFAULT_TEXT_PACK_URL

    def task(job: JobInfo, log):
        log(f"Starting Complete Text Pack Process...")
        log(f"Source URL: {pack_url}")
        log(f"Destination: {dest_dir}")

        downloader = SutraDownloader(download_dir=dest_dir)
        log("Downloading full archive...")
        res = downloader.download_file(pack_url, dest_dir=dest_dir, progress_callback=log, log_progress_dots=True)

        if not res.success:
            log(f"Complete pack download failed: {res.error}")
            return

        zip_path = res.filepath or os.path.join(dest_dir, res.filename)
        log(f"Download successful: {zip_path}")

        process_cbeta_text_pack(
            zip_path=zip_path,
            dest_dir=dest_dir,
            output_dir=payload.output_dir,
            remove_zip=True,
            convert_md=payload.convert_md,
            auto_heading=payload.auto_heading,
            logger=log
        )
        log("Complete Text Pack Process finished.")

    job = job_engine.submit_task("complete_pack", task, metadata={"dest_dir": dest_dir, "pack_url": pack_url, "edition": "txt"})
    return {"status": "started", "job_id": job.job_id, "edition": "txt"}


@router.post("/api/xml_repo/sync")
async def sync_xml_repo(payload: XmlSyncPayload):
    dest_dir = os.path.abspath(payload.dest_dir)
    repo_url = payload.repo_url or DEFAULT_XML_P5_REPO

    def xml_task(job: JobInfo, log):
        log(f"啟動 CBETA TEI P5 XML 全藏庫同步作業...")
        log(f"遠端 Repo: {repo_url}")
        log(f"本地目標: {dest_dir}")
        res = clone_or_update_xml_repo(
            repo_url=repo_url,
            target_dir=dest_dir,
            shallow=payload.shallow,
            branch=payload.branch,
            progress_callback=log,
            stop_event=job._cancel_event
        )
        if res.success:
            log(f"XML 全藏庫同步圓滿完成！Commit: {res.commit_hash}")
        else:
            log(f"XML 同步失敗或已取消: {res.message}")

    job = job_engine.submit_task("xml_sync", xml_task, metadata={"dest_dir": dest_dir, "repo_url": repo_url})
    return {"status": "started", "job_id": job.job_id}


@router.get("/api/xml_repo/status")
async def get_xml_status(dest_dir: str = "./downloads-xml"):
    status = get_xml_repo_status(dest_dir)
    return status


@router.post("/api/xml_repo/convert_obsidian")
async def convert_xml_obsidian_endpoint(payload: XmlToObsidianPayload):
    xml_dir = os.path.abspath(payload.xml_dir)
    output_dir = os.path.abspath(payload.output_dir)

    def task(job: JobInfo, log):
        log(f"啟動 CBETA TEI P5 XML 轉 Obsidian Markdown 作業...")
        log(f"來源 XML 目錄: {xml_dir}")
        log(f"匯出目標目錄: {output_dir}")
        count = convert_xml_directory_to_obsidian(
            xml_dir=xml_dir,
            output_dir=output_dir,
            include_line_anchors=payload.include_line_anchors,
            include_page_marks=payload.include_page_marks,
            progress_callback=log,
            stop_event=job._cancel_event
        )
        if job.is_cancelled():
            log(f"XML 轉 Obsidian 作業已被使用者中斷 (共完成 {count} 部)。")
        else:
            log(f"✨ 轉換作業圓滿完成！共產出 {count} 份標準 Obsidian Markdown 經文筆記。")

    job = job_engine.submit_task("xml_to_obsidian", task, metadata={"xml_dir": xml_dir, "output_dir": output_dir})
    return {"status": "started", "job_id": job.job_id}


# --- Presets & Corpus Library ---

BUDDHIST_PRESETS = [
    {
        "id": "weishi",
        "title": "唯識根本經論",
        "category": "瑜伽唯識",
        "badge": "慈恩宗規",
        "description": "窺基大師會釋十師異義之《成唯識論》與無著世親根本論典",
        "sutras": [
            {"id": "T1585", "name": "成唯識論", "vols": "10卷", "author": "護法等菩薩造 玄奘譯"},
            {"id": "T1586", "name": "唯識三十論頌", "vols": "1卷", "author": "世親菩薩造 玄奘譯"},
            {"id": "T1590", "name": "唯識二十論", "vols": "1卷", "author": "世親菩薩造 玄奘譯"},
            {"id": "T1592", "name": "攝大乘論", "vols": "3卷", "author": "無著菩薩造 佛陀扇多譯"},
            {"id": "T1599", "name": "辯中邊論", "vols": "3卷", "author": "世親菩薩造 玄奘譯"}
        ],
        "default_ids": "T1585\nT1586\nT1590\nT1592\nT1599"
    },
    {
        "id": "prajna",
        "title": "般若波羅蜜多部",
        "category": "般若空宗",
        "badge": "斷疑生信",
        "description": "大乘空宗核心寶典，破執顯性、甚深般若直指菩提",
        "sutras": [
            {"id": "T0235", "name": "金剛般若波羅蜜經", "vols": "1卷", "author": "鳩摩羅什譯"},
            {"id": "T0251", "name": "般若波羅蜜多心經", "vols": "1卷", "author": "玄奘譯"},
            {"id": "T0261", "name": "大成大集地藏十輪經", "vols": "8卷", "author": "玄奘譯"},
            {"id": "T0220", "name": "大般若波羅蜜多經(精選)", "vols": "初分卷一", "author": "玄奘譯"}
        ],
        "default_ids": "T0235\nT0251\nT0261"
    },
    {
        "id": "agama",
        "title": "根本阿含部類",
        "category": "原始根本",
        "badge": "正法久住",
        "description": "初期佛教佛陀親炙言教，四阿含根本聖典選輯",
        "sutras": [
            {"id": "T0001", "name": "長阿含經", "vols": "22卷", "author": "後秦 佛陀耶舍共竺佛念譯"},
            {"id": "T0026", "name": "中阿含經", "vols": "60卷", "author": "東晉 僧伽提婆譯"},
            {"id": "T0099", "name": "雜阿含經", "vols": "50卷", "author": "劉宋 求那跋陀羅譯"}
        ],
        "default_ids": "T0001\nT0026\nT0099"
    },
    {
        "id": "saddharma",
        "title": "法華楞嚴楞伽部",
        "category": "法華涅槃",
        "badge": "如來藏識",
        "description": "一乘圓教與性相融通之傳世重典，直指如來藏真如妙心",
        "sutras": [
            {"id": "T0262", "name": "妙法蓮華經", "vols": "7卷", "author": "後秦 鳩摩羅什譯"},
            {"id": "T0945", "name": "大佛頂如來密因修證了義諸菩薩萬行首楞嚴經", "vols": "10卷", "author": "般剌密帝譯"},
            {"id": "T0670", "name": "楞伽阿跋多羅寶經", "vols": "4卷", "author": "劉宋 求那跋陀羅譯"}
        ],
        "default_ids": "T0262\nT0945\nT0670"
    },
    {
        "id": "chan",
        "title": "禪宗祖師要籍",
        "category": "禪門祖印",
        "badge": "直指人心",
        "description": "東土祖師真傳心印，不立文字，見性成佛之宗門寶鑑",
        "sutras": [
            {"id": "T2008", "name": "六祖大師法寶壇經", "vols": "1卷", "author": "唐 惠能大師說"},
            {"id": "T2076", "name": "景德傳燈錄", "vols": "30卷", "author": "宋 道原纂"}
        ],
        "default_ids": "T2008\nT2076"
    },
    {
        "id": "rare_canons",
        "title": "嘉興藏與卍續藏珍稀論著",
        "category": "明清嘉興",
        "badge": "雙字藏號",
        "description": "嘉興藏方冊本與續藏珍稀注疏（測試雙字元 JB、ZS 藏號解析能力）",
        "sutras": [
            {"id": "JB234", "name": "慈恩宗規", "vols": "1卷", "author": "明 嘉興大藏經"},
            {"id": "JB235", "name": "慈恩傳略", "vols": "1卷", "author": "明 嘉興大藏經"},
            {"id": "X0367", "name": "金剛經解註", "vols": "1卷", "author": "卍新纂續藏經"}
        ],
        "default_ids": "JB234\nJB235\nX0367"
    }
]


@router.get("/api/presets")
async def get_presets():
    """Return all Buddhist presets (built-in and user-customized)."""
    return preset_manager.list_presets()


@router.post("/api/presets")
async def save_preset_endpoint(preset: PresetModel):
    """Create or update a scripture preset."""
    saved = preset_manager.save_preset(preset.model_dump())
    return {"status": "saved", "preset": saved.model_dump()}


@router.delete("/api/presets/{preset_id}")
async def delete_preset_endpoint(preset_id: str):
    """Delete a scripture preset."""
    success = preset_manager.delete_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "deleted", "preset_id": preset_id}


@router.post("/api/presets/reset")
async def reset_presets_endpoint():
    """Reset presets to default Buddhist classics."""
    for p in DEFAULT_BUDDHIST_PRESETS:
        preset_manager.save_preset(p)
    return {"status": "reset", "presets": preset_manager.list_presets()}


# --- Complete Output File Management & Workbench ---

# --- Complete Output File Management & Workbench ---

@router.get("/api/complete/files")
async def list_complete_files(output_dir: Optional[str] = None):
    """
    List processed scripture files in the complete directory across all supported formats.
    """
    target = os.path.abspath(output_dir) if output_dir else os.path.join(base_dir, "complete")
    if not os.path.isdir(target):
        return []

    files_list = []
    type_map = {
        ".md": ("markdown", "sutra_md", "Markdown 經文"),
        ".txt": ("text", "sutra_md", "純文字經文"),
        ".pdf": ("pdf", "ebook", "PDF 文件"),
        ".epub": ("epub", "ebook", "EPUB 電子書"),
        ".mobi": ("mobi", "ebook", "MOBI 電子書"),
        ".docx": ("word", "document", "Word 文件"),
        ".odt": ("opendoc", "document", "ODT 開放文件"),
        ".xml": ("xml", "data", "XML 經文數據"),
        ".html": ("html", "data", "HTML 網頁")
    }

    for root, _, entries in os.walk(target):
        for entry in sorted(entries):
            if entry.startswith("."):
                continue
            full_path = os.path.join(root, entry)
            if not os.path.isfile(full_path):
                continue

            size = os.path.getsize(full_path)
            mtime = os.path.getmtime(full_path)

            ext = os.path.splitext(entry)[1].lower()
            if entry.lower().endswith(".docusky.xml"):
                ext = ".xml"

            if ext in type_map:
                ftype, category, label = type_map[ext]
                rel_path = os.path.relpath(full_path, target)
                files_list.append({
                    "filename": entry,
                    "rel_path": rel_path,
                    "path": full_path,
                    "size_kb": round(size / 1024, 1),
                    "modified": mtime,
                    "type": ftype,
                    "category": category,
                    "label": label,
                    "is_binary": ext in (".pdf", ".epub", ".mobi", ".docx", ".odt")
                })

    # Sort latest modified first
    files_list.sort(key=lambda x: x["modified"], reverse=True)
    return files_list


@router.get("/api/complete/file")
async def get_complete_file_content(filename: str, output_dir: Optional[str] = None):
    """
    Safely retrieve content or metadata of a file in the complete directory.
    If binary file (PDF, EPUB, DOCX, ODT, MOBI), returns metadata without attempting UTF-8 read.
    """
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in ('.', '..'):
        raise HTTPException(status_code=400, detail="Invalid filename")

    target_dir = os.path.abspath(output_dir) if output_dir else os.path.join(base_dir, "complete")
    full_path = os.path.normpath(os.path.join(target_dir, safe_name))

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(safe_name)[1].lower()
    is_binary = ext in (".pdf", ".epub", ".mobi", ".docx", ".odt")

    if is_binary:
        return {
            "filename": safe_name,
            "is_binary": True,
            "size_kb": round(os.path.getsize(full_path) / 1024, 1),
            "type": ext.lstrip("."),
            "content": None
        }

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        line_count = len(content.splitlines())
        word_count = len(content)

        return {
            "filename": safe_name,
            "is_binary": False,
            "content": content,
            "line_count": line_count,
            "char_count": word_count,
            "type": "markdown" if safe_name.endswith(".md") else "text"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")


@router.get("/api/complete/download")
async def download_complete_file(filename: str, output_dir: Optional[str] = None):
    """Directly stream/download any file from complete directory to browser."""
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name in ('.', '..'):
        raise HTTPException(status_code=400, detail="Invalid filename")

    target_dir = os.path.abspath(output_dir) if output_dir else os.path.join(base_dir, "complete")
    full_path = os.path.normpath(os.path.join(target_dir, safe_name))
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path, filename=safe_name)


# --- End-to-End Fluent 4-Step Smart Adaptive Pipeline ---

@router.post("/api/pipeline/run")
async def run_pipeline(payload: PipelinePayload):
    """
    Smart Adaptive Multi-Stream Pipeline:
    1. Parse IDs -> 2. Batch Download ->
    3. (If TXT formats): Unzip & Combine -> Convert MD & Format H2 Headings
    4. (If E-Book / Docs formats): Organize & Extract Artifacts -> Ready in Workbench
    """
    ids = parse_id_list(payload.id_list)
    if not ids:
        return JSONResponse(status_code=400, content={"status": "error", "message": "No valid sutra IDs provided"})

    dest_dir = os.path.abspath(payload.dest_dir)
    final_output_dir = os.path.abspath(payload.output_dir) if payload.output_dir else os.path.join(base_dir, "complete")
    formats = payload.formats or ["txt"]

    TEXT_FORMATS = {"txt", "text-with-notes", "txt_notes", "txt-notes"}
    has_text_formats = any(f.lower() in TEXT_FORMATS for f in formats)
    has_other_formats = any(f.lower() not in TEXT_FORMATS for f in formats)

    def pipeline_task(job: JobInfo, log):
        job_engine.update_progress(job.job_id, 5.0, "步驟一：驗證與解析經號")
        log(f"=== ☸ CBETA 智慧適應型研讀流水線啟動 (共 {len(ids)} 筆經號) ===")
        log(f"目標清單: {', '.join(ids[:10])}{' ...' if len(ids) > 10 else ''}")
        log(f"下載格式: {', '.join(formats)} | 暫存路徑: {dest_dir} | 產出目錄: {final_output_dir}")

        if has_text_formats and has_other_formats:
            log("模式偵測: 雙軌流 (純文字經文合併排版 ＋ 電子書排版文檔自動歸檔)")
        elif has_text_formats:
            log("模式偵測: 純文字與 Markdown 研讀流 (解壓 ➔ 卷次排序 ➔ 合併 ➔ H2排版)")
        else:
            log("模式偵測: 電子書與排版文件流 (直接下載 ➔ 格式校驗 ➔ 歸檔至文檔庫)")

        # Stage 1: Download all requested formats
        job_engine.update_progress(job.job_id, 15.0, "步驟二：批次下載資源中")
        log("\n--- [步驟二：多格式並行批次下載] ---")
        downloader = SutraDownloader(download_dir=dest_dir)

        def cb(msg):
            if job.is_cancelled():
                downloader.cancel()
            log(msg)

        summary = downloader.download_from_ids(
            ids=ids,
            formats=formats,
            progress_callback=cb
        )

        if job.is_cancelled():
            log("流水線在下載階段被中斷。")
            return

        log(f"下載階段完成：成功 {summary.succeeded} / 總共 {summary.total}")

        # Stage 2 & 3: Text Pipeline (Only if text formats selected)
        if has_text_formats:
            job_engine.update_progress(job.job_id, 45.0, "步驟三：解壓卷次與智能合併")
            log("\n--- [文字排版流：解壓縮與卷次自然排序合併] ---")
            created_files = process_project(
                working_dir=dest_dir,
                output_dir=final_output_dir,
                remove_zip=payload.remove_zip,
                logger=log
            )
            log(f"合併完成：產出 {len(created_files)} 部完整典籍純文字檔")

            if job.is_cancelled():
                log("流水線在合併階段被中斷。")
                return

            job_engine.update_progress(job.job_id, 75.0, "步驟四：Markdown 轉換與 H2 卷品地排版")
            log("\n--- [文字排版流：Markdown 轉換、防撞註解與 H2 標題排版] ---")
            conv_count = convert_directory_to_md(
                target_dir=final_output_dir,
                auto_heading=payload.auto_heading,
                remove_source=True,
                logger=log
            )
            log(f"排版轉換完成：共 {conv_count} 部典籍轉換為標準 Markdown")
        else:
            log("\n--- [智慧跳過：未包含純文字格式，自動略過純文字卷次合併與 Markdown 轉換步驟] ---")

        # Stage 4: Artifact Organizing for E-Books / Docs / Data
        if has_other_formats:
            job_engine.update_progress(job.job_id, 85.0, "電子書與排版文件自動歸檔")
            log("\n--- [電子書與文件流：自動歸檔排版文檔至成果庫] ---")
            docs = organize_downloaded_artifacts(dest_dir, final_output_dir, logger=log)
            log(f"歸檔完成：共 {len(docs)} 份電子書/排版文件已就緒！")

        job_engine.update_progress(job.job_id, 100.0, "流水線全流程圓滿完成")
        log("\n=== ✨ CBETA 適應型研讀流水線全流程圓滿完成！請至研讀工作台查閱 ===")

    job = job_engine.submit_task("pipeline", pipeline_task, metadata={"ids_count": len(ids), "formats": formats})
    return {"status": "started", "job_id": job.job_id}

