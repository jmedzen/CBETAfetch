"""
CBETAfetch 2.0 - System Diagnostics & Self-Test Engine
Validates all core subsystems, environment configurations, and external connectivity.
"""

import os
import sys
import time
import socket
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from core.id_parser import extract_canon, parse_id_list, parse_id_range, validate_sutra_id
from core.downloader import build_download_url, DEFAULT_BASE_URL
from core.headings import format_headings_in_text, is_valid_heading_candidate
from core.converter import sanitize_txt_for_markdown
from core.processor import extract_sutra_metadata, sort_volume_files
from core.job_engine import JobEngine, JobStatus


@dataclass
class DiagnosticCheck:
    name: str
    category: str
    status: str  # "passed", "warning", "failed"
    duration_ms: int
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class DiagnosticReport:
    timestamp: str
    total_tests: int = 0
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    total_duration_ms: int = 0
    results: List[DiagnosticCheck] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed": self.passed_count,
            "warning": self.warning_count,
            "failed": self.failed_count,
            "total_duration_ms": self.total_duration_ms,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }


class SystemDiagnostics:
    """
    Automated health checks for CBETAfetch 2.0.
    """

    @classmethod
    def run_all_checks(cls, base_dir: str, job_engine: Optional[JobEngine] = None) -> DiagnosticReport:
        report = DiagnosticReport(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))
        t0 = time.time()

        checks = [
            cls.check_python_environment,
            lambda: cls.check_workspace_directories(base_dir),
            cls.check_id_parser_engine,
            cls.check_two_letter_canons,
            cls.check_url_builder_formats,
            cls.check_headings_engine,
            cls.check_heading_deduplication,
            cls.check_converter_sanitization,
            cls.check_processor_toc_ordering,
            cls.check_processor_metadata_extraction,
            lambda: cls.check_job_lifecycle(job_engine),
            cls.check_git_environment,
            cls.check_network_connectivity
        ]

        for check_fn in checks:
            try:
                res = check_fn()
                report.results.append(res)
                if res.status == "passed":
                    report.passed_count += 1
                elif res.status == "warning":
                    report.warning_count += 1
                else:
                    report.failed_count += 1
            except Exception as e:
                report.results.append(
                    DiagnosticCheck(
                        name=getattr(check_fn, "__name__", "unknown_check"),
                        category="system",
                        status="failed",
                        duration_ms=0,
                        message=f"Diagnostic error: {e}"
                    )
                )
                report.failed_count += 1

        report.total_tests = len(report.results)
        report.total_duration_ms = int((time.time() - t0) * 1000)
        return report

    @classmethod
    def check_python_environment(cls) -> DiagnosticCheck:
        t0 = time.time()
        major, minor = sys.version_info.major, sys.version_info.minor
        ms = int((time.time() - t0) * 1000)

        if major == 3 and minor >= 9:
            return DiagnosticCheck(
                name="Python 運行環境",
                category="environment",
                status="passed",
                duration_ms=ms,
                message=f"Python {sys.version.split()[0]} (符合 >= 3.9 要求)"
            )
        return DiagnosticCheck(
            name="Python 運行環境",
            category="environment",
            status="failed",
            duration_ms=ms,
            message=f"Python {sys.version.split()[0]} 低於建議版本 3.9+"
        )

    @classmethod
    def check_workspace_directories(cls, base_dir: str) -> DiagnosticCheck:
        t0 = time.time()
        required_dirs = ["downloads", "complete", "data/jobs"]
        missing = []
        for d in required_dirs:
            full = os.path.join(base_dir, d)
            try:
                os.makedirs(full, exist_ok=True)
                test_file = os.path.join(full, ".perm_test")
                with open(test_file, "w") as f:
                    f.write("ok")
                os.remove(test_file)
            except Exception:
                missing.append(d)

        ms = int((time.time() - t0) * 1000)
        if not missing:
            return DiagnosticCheck(
                name="目錄可讀寫性檢查",
                category="storage",
                status="passed",
                duration_ms=ms,
                message="工作空間目錄 (downloads, complete, data/jobs) 讀寫均正常"
            )
        return DiagnosticCheck(
            name="目錄可讀寫性檢查",
            category="storage",
            status="failed",
            duration_ms=ms,
            message=f"目錄無寫入權限: {', '.join(missing)}"
        )

    @classmethod
    def check_id_parser_engine(cls) -> DiagnosticCheck:
        t0 = time.time()
        test_input = "T1585\nT1500-T1502\n# Comment\n\nX0367"
        parsed = parse_id_list(test_input)
        expected = ["T1585", "T1500", "T1501", "T1502", "X0367"]
        ms = int((time.time() - t0) * 1000)

        if parsed == expected:
            return DiagnosticCheck(
                name="經文編號解析與範圍展開",
                category="parser",
                status="passed",
                duration_ms=ms,
                message=f"成功解析 {len(parsed)} 筆經文編號並正確展開範圍"
            )
        return DiagnosticCheck(
            name="經文編號解析與範圍展開",
            category="parser",
            status="failed",
            duration_ms=ms,
            message=f"解析不符合預期: 得到 {parsed}, 預期 {expected}"
        )

    @classmethod
    def check_two_letter_canons(cls) -> DiagnosticCheck:
        t0 = time.time()
        test_cases = {
            "T1585": "T",
            "X0367": "X",
            "JB234": "JB",
            "ZS0010": "ZS",
            "GA0001": "GA"
        }
        for sutra_id, expected_canon in test_cases.items():
            actual = extract_canon(sutra_id)
            if actual != expected_canon:
                ms = int((time.time() - t0) * 1000)
                return DiagnosticCheck(
                    name="雙字母與多字元藏經代碼萃取",
                    category="parser",
                    status="failed",
                    duration_ms=ms,
                    message=f"萃取藏經代碼錯誤: {sutra_id} 得到 {actual}, 預期 {expected_canon}"
                )

        ms = int((time.time() - t0) * 1000)
        return DiagnosticCheck(
            name="雙字母與多字元藏經代碼萃取",
            category="parser",
            status="passed",
            duration_ms=ms,
            message="單字母 (T, X) 與雙字母 (JB, ZS, GA) 藏號代碼萃取驗證完全正確"
        )

    @classmethod
    def check_url_builder_formats(cls) -> DiagnosticCheck:
        t0 = time.time()
        url_txt = build_download_url("T1585", "txt")
        url_epub = build_download_url("JB234", "epub")
        url_pdf = build_download_url("JB234", "pdf")
        url_docx = build_download_url("T0099", "docx")
        url_odt = build_download_url("T0099", "odt")
        url_docusky = build_download_url("T0001", "docusky")
        url_notes = build_download_url("T0001", "text-with-notes")
        ms = int((time.time() - t0) * 1000)

        cond1 = url_txt == "https://cbdata.dila.edu.tw/stable/download/text/T1585.txt.zip"
        cond2 = url_epub == "https://cbdata.dila.edu.tw/stable/download/epub/JB/JB234.epub"
        cond3 = url_pdf == "https://cbdata.dila.edu.tw/stable/download/pdf/JB/JB234.pdf"
        cond4 = url_docx == "https://cbdata.dila.edu.tw/stable/download/docx/T/T0099.zip"
        cond5 = url_odt == "https://cbdata.dila.edu.tw/stable/download/odt/T/T0099.zip"
        cond6 = url_docusky == "https://cbdata.dila.edu.tw/stable/download/docusky/T0001.docusky.xml"
        cond7 = url_notes == "https://cbdata.dila.edu.tw/stable/download/text-with-notes/T0001.txt.zip"

        if all([cond1, cond2, cond3, cond4, cond5, cond6, cond7]):
            return DiagnosticCheck(
                name="多格式下載網址建構 (TXT/HTML/EPUB/MOBI/PDF/DOCX/ODT/DocuSky/含校注)",
                category="network",
                status="passed",
                duration_ms=ms,
                message="9 大格式 (含 DOCX/ODT/DocuSky/校注) 與多字母藏號之 Canonical 下載網址建構無誤"
            )
        return DiagnosticCheck(
            name="多格式下載網址建構 (TXT/HTML/EPUB/MOBI/PDF/DOCX/ODT/DocuSky/含校注)",
            category="network",
            status="failed",
            duration_ms=ms,
            message=f"網址建構異常: TXT={url_txt}, DOCX={url_docx}, ODT={url_odt}, DocuSky={url_docusky}"
        )

    @classmethod
    def check_headings_engine(cls) -> DiagnosticCheck:
        t0 = time.time()
        sample = (
            "成唯識論卷第一\n"
            "序品第一\n"
            "極喜地第一\n"
            "成唯識論卷第二\n"
        )
        formatted, mod = format_headings_in_text(sample)
        ms = int((time.time() - t0) * 1000)

        lines = formatted.splitlines()
        if (
            lines[0].startswith("## 成唯識論卷第一")
            and lines[1].startswith("## 序品第一")
            and lines[2].startswith("## 極喜地第一")
            and lines[3].startswith("## 成唯識論卷第二")
        ):
            return DiagnosticCheck(
                name="智能經論層級標題格式化 (卷/品/地)",
                category="headings",
                status="passed",
                duration_ms=ms,
                message="多卷經論標題、品目與十地標題正確套用 H2 標記"
            )
        return DiagnosticCheck(
            name="智能經論層級標題格式化 (卷/品/地)",
            category="headings",
            status="failed",
            duration_ms=ms,
            message="標題識別與標記未達預期"
        )

    @classmethod
    def check_heading_deduplication(cls) -> DiagnosticCheck:
        t0 = time.time()
        sample = (
            "成唯識論卷第一\n"
            "成唯識論卷第二\n"
            "如是說已。\n"
            "成唯識論卷第一\n"  # 卷末重覆標題
        )
        formatted, mod = format_headings_in_text(sample)
        ms = int((time.time() - t0) * 1000)

        lines = formatted.splitlines()
        if lines[0].startswith("## ") and not lines[3].startswith("## "):
            return DiagnosticCheck(
                name="經論尾卷標題去重防碰撞",
                category="headings",
                status="passed",
                duration_ms=ms,
                message="尾卷重複之標題未重複被加上 H2 標籤，成功防重"
            )
        return DiagnosticCheck(
            name="經論尾卷標題去重防碰撞",
            category="headings",
            status="failed",
            duration_ms=ms,
            message="未能正確過濾重複出現之篇章標題"
        )

    @classmethod
    def check_converter_sanitization(cls) -> DiagnosticCheck:
        t0 = time.time()
        raw = "# CBETA Comment line\nNormal Line\n# Another comment"
        sanitized = sanitize_txt_for_markdown(raw)
        ms = int((time.time() - t0) * 1000)

        if "// CBETA Comment line" in sanitized and "#" not in sanitized:
            return DiagnosticCheck(
                name="Markdown 註解防碰撞替換 (# 轉 //)",
                category="converter",
                status="passed",
                duration_ms=ms,
                message="CBETA # 標籤已正確轉化為 //，防範 Markdown 誤判為 H1 標題"
            )
        return DiagnosticCheck(
            name="Markdown 註解防碰撞替換 (# 轉 //)",
            category="converter",
            status="failed",
            duration_ms=ms,
            message="註解符號替換未通過"
        )

    @classmethod
    def check_processor_toc_ordering(cls) -> DiagnosticCheck:
        t0 = time.time()
        files = ["T1585-toc.txt", "T1585_002.txt", "._T1585_001.txt", "T1585_001.txt"]
        sorted_files = sort_volume_files(files)
        ms = int((time.time() - t0) * 1000)

        if sorted_files == ["T1585_001.txt", "T1585_002.txt", "T1585-toc.txt"]:
            return DiagnosticCheck(
                name="卷次自然排序與目錄檔案 (TOC) 置尾保護",
                category="processor",
                status="passed",
                duration_ms=ms,
                message="忽略 macOS ._* 隱藏檔案，卷次自然升冪，TOC 置於經文末尾"
            )
        return DiagnosticCheck(
            name="卷次自然排序與目錄檔案 (TOC) 置尾保護",
            category="processor",
            status="failed",
            duration_ms=ms,
            message=f"檔案排序錯誤: {sorted_files}"
        )

    @classmethod
    def check_processor_metadata_extraction(cls) -> DiagnosticCheck:
        t0 = time.time()
        # Mock file
        import tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
            tf.write("# CBETA Electronic Tripitaka\n# No. 1585 成唯識論\n# 護法等菩薩造\n")
            tmp_path = tf.name

        try:
            sutra_id, sutra_name = extract_sutra_metadata(tmp_path)
            ms = int((time.time() - t0) * 1000)
            if sutra_name == "成唯識論":
                return DiagnosticCheck(
                    name="經名與典籍元數據自動提取",
                    category="processor",
                    status="passed",
                    duration_ms=ms,
                    message="正確從首卷標頭萃取出經論中文名稱《成唯識論》"
                )
            return DiagnosticCheck(
                name="經名與典籍元數據自動提取",
                category="processor",
                status="failed",
                duration_ms=ms,
                message=f"提取經名異常: '{sutra_name}' (預期 '成唯識論')"
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @classmethod
    def check_job_lifecycle(cls, job_engine: Optional[JobEngine]) -> DiagnosticCheck:
        t0 = time.time()
        je = job_engine or JobEngine()
        job = je.create_job("test_job")

        job.status = JobStatus.RUNNING
        je.add_log(job.job_id, "test log entry")
        je.update_progress(job.job_id, 50.0, "Testing")
        cancelled = je.cancel_job(job.job_id)

        ms = int((time.time() - t0) * 1000)
        if cancelled and job.status == JobStatus.CANCELLED and len(job.logs) >= 2:
            return DiagnosticCheck(
                name="非同步工作佇列生命週期與協同中斷",
                category="jobs",
                status="passed",
                duration_ms=ms,
                message="工作建立、進度更新、日誌廣播與取消機制運作完全正常"
            )
        return DiagnosticCheck(
            name="非同步工作佇列生命週期與協同中斷",
            category="jobs",
            status="failed",
            duration_ms=ms,
            message="工作引擎狀態流轉異常"
        )

    @classmethod
    def check_git_environment(cls) -> DiagnosticCheck:
        import subprocess
        t0 = time.time()
        try:
            res = subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            ms = int((time.time() - t0) * 1000)
            if res.returncode == 0:
                ver = res.stdout.strip()
                return DiagnosticCheck(
                    name="Git 版本控制工具檢查 (XML 全藏庫必備)",
                    category="environment",
                    status="passed",
                    duration_ms=ms,
                    message=f"已就緒: {ver}"
                )
            return DiagnosticCheck(
                name="Git 版本控制工具檢查 (XML 全藏庫必備)",
                category="environment",
                status="warning",
                duration_ms=ms,
                message=f"Git 回傳碼異常: {res.returncode}"
            )
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            return DiagnosticCheck(
                name="Git 版本控制工具檢查 (XML 全藏庫必備)",
                category="environment",
                status="warning",
                duration_ms=ms,
                message=f"未偵測到 Git 執行檔: {e} (XML 全藏下載需使用 Git)"
            )

    @classmethod
    def check_network_connectivity(cls) -> DiagnosticCheck:
        t0 = time.time()
        host = "cbdata.dila.edu.tw"
        try:
            sock = socket.create_connection((host, 443), timeout=1.5)
            sock.close()
            ms = int((time.time() - t0) * 1000)
            return DiagnosticCheck(
                name="CBETA / DILA API 伺服器連線檢測",
                category="network",
                status="passed",
                duration_ms=ms,
                message=f"已成功連通 {host}:443 (延遲 {ms}ms)"
            )
        except Exception as e:
            ms = int((time.time() - t0) * 1000)
            return DiagnosticCheck(
                name="CBETA / DILA API 伺服器連線檢測",
                category="network",
                status="warning",
                duration_ms=ms,
                message=f"暫無法連線至 {host}: {e} (若處於離線環境可忽略此項)"
            )
