"""
CBETAfetch 2.0 - Sutra Downloader Engine
Supports multi-format downloading (TXT, HTML, EPUB, MOBI, PDF) with parallel workers,
streaming progress callbacks, SSL resilience, and cooperative cancellation.
"""

import os
import ssl
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass, field

from core.id_parser import extract_canon, parse_id_list, parse_id_file
from core.progress import format_progress_line, render_progress_bar

DEFAULT_BASE_URL = "https://cbdata.dila.edu.tw/stable/download/"
DEFAULT_TEXT_PACK_URL = "https://cbdata.dila.edu.tw/stable/download/cbeta-text.zip"
SUPPORTED_FORMATS = (
    "txt", "html", "epub", "mobi", "pdf",
    "docx", "odt", "docusky", "text-with-notes"
)


@dataclass
class DownloadResult:
    url: str
    filename: str
    filepath: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    size_bytes: int = 0
    duration_s: float = 0.0


@dataclass
class BatchSummary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: bool = False
    results: List[DownloadResult] = field(default_factory=list)


def build_download_url(
    sutra_id: str,
    fmt: str = "txt",
    base_url: Optional[str] = None,
    format_urls: Optional[Dict[str, str]] = None
) -> str:
    """
    Construct the canonical CBETA download URL for a given Sutra ID and format.
    
    Args:
        sutra_id: e.g. 'T1585', 'JB234'
        fmt: 'txt', 'html', 'epub', 'mobi', or 'pdf'
        base_url: Global base URL override
        format_urls: Format-specific base URL overrides dict
    """
    fmt = fmt.lower().strip()
    sutra_id = sutra_id.strip()
    canon = extract_canon(sutra_id)

    # Determine base root URL
    base = None
    if format_urls and fmt in format_urls and format_urls[fmt]:
        base = format_urls[fmt]
    elif base_url:
        base = base_url
    else:
        base = DEFAULT_BASE_URL

    # Ensure trailing slash
    if not base.endswith("/"):
        base += "/"

    # Normalize base if user passed sub-path
    if "/download/" in base and not base.endswith("/download/"):
        base = base.split("/download/")[0] + "/download/"

    # Normalize aliases
    if fmt in ("docuxml", "docusky"):
        fmt = "docusky"
    elif fmt in ("txt-notes", "txt_notes", "text-with-notes"):
        fmt = "text-with-notes"

    if fmt == "txt":
        return f"{base}text/{sutra_id}.txt.zip"
    elif fmt == "html":
        return f"{base}html/{sutra_id}.html.zip"
    elif fmt == "epub":
        return f"{base}epub/{canon}/{sutra_id}.epub"
    elif fmt == "mobi":
        return f"{base}mobi/{canon}/{sutra_id}.mobi"
    elif fmt == "pdf":
        return f"{base}pdf/{canon}/{sutra_id}.pdf"
    elif fmt == "docx":
        return f"{base}docx/{canon}/{sutra_id}.zip"
    elif fmt == "odt":
        return f"{base}odt/{canon}/{sutra_id}.zip"
    elif fmt == "docusky":
        return f"{base}docusky/{sutra_id}.docusky.xml"
    elif fmt == "text-with-notes":
        return f"{base}text-with-notes/{sutra_id}.txt.zip"
    else:
        raise ValueError(f"Unsupported format '{fmt}'. Supported: {SUPPORTED_FORMATS}")


class SutraDownloader:
    """
    High-performance Sutra Downloader with progress tracking and cooperative cancellation.
    """

    def __init__(self, download_dir: str = "./downloads", max_workers: int = 5, timeout: int = 30):
        self.download_dir = os.path.abspath(os.path.normpath(download_dir))
        self.max_workers = max_workers
        self.timeout = timeout
        self.stop_event = threading.Event()
        self.executor: Optional[ThreadPoolExecutor] = None

    def cancel(self):
        """Signal all in-flight and pending downloads to stop."""
        self.stop_event.set()
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)

    def is_cancelled(self) -> bool:
        return self.stop_event.is_set()

    def reset(self):
        """Reset the cancellation flag for a new run."""
        self.stop_event.clear()

    def download_file(
        self,
        url: str,
        dest_dir: Optional[str] = None,
        filename_override: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        log_progress_dots: bool = False,
        retries: int = 1
    ) -> DownloadResult:
        """
        Download a single file from a URL to the designated destination directory.
        """
        if self.stop_event.is_set():
            return DownloadResult(url=url, filename="", success=False, error="Cancelled")

        target_dir = os.path.abspath(os.path.normpath(dest_dir or self.download_dir))
        os.makedirs(target_dir, exist_ok=True)

        filename = filename_override or url.split("/")[-1]
        filepath = os.path.join(target_dir, filename)

        start_time = time.time()

        for attempt in range(retries + 1):
            if self.stop_event.is_set():
                return DownloadResult(url=url, filename=filename, success=False, error="Cancelled")

            try:
                if progress_callback:
                    attempt_str = f" (attempt {attempt+1})" if attempt > 0 else ""
                    progress_callback(f"Starting download: {filename}{attempt_str}")

                # Configure SSL Context (CBETA and DILA servers)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "CBETAfetch/2.0 (Buddhist Digital Humanities Tool)"}
                )

                with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context) as response:
                    total_size = int(response.getheader("Content-Length") or 0)
                    block_size = 32768  # 32 KB chunks
                    wrote = 0
                    last_progress_time = start_time
                    last_progress_percent = -1.0
                    last_log_size = 0
                    log_interval = 5 * 1024 * 1024  # 5 MB

                    with open(filepath, "wb") as f:
                        while True:
                            if self.stop_event.is_set():
                                break
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            wrote += len(chunk)

                            now = time.time()
                            if progress_callback:
                                if total_size > 0:
                                    percent = (wrote / total_size) * 100.0
                                    if (now - last_progress_time >= 0.7) or (percent - last_progress_percent >= 5.0) or wrote == total_size:
                                        elapsed = max(0.001, now - start_time)
                                        speed = wrote / elapsed
                                        eta = ((total_size - wrote) / speed) if speed > 0 and total_size > wrote else 0.0
                                        prog_line = format_progress_line(
                                            percent=percent,
                                            current_bytes=wrote,
                                            total_bytes=total_size,
                                            speed_bps=speed,
                                            eta_sec=eta,
                                            label=f"下載 {filename}"
                                        )
                                        progress_callback(prog_line)
                                        last_progress_time = now
                                        last_progress_percent = percent
                                elif log_progress_dots:
                                    if wrote - last_log_size >= log_interval:
                                        progress_callback(".")
                                        last_log_size = wrote

                if self.stop_event.is_set():
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    return DownloadResult(url=url, filename=filename, success=False, error="Cancelled")

                duration = time.time() - start_time
                if progress_callback:
                    size_kb = wrote / 1024
                    progress_callback(f"Finished download: {filename} ({size_kb:.1f} KB in {duration:.2f}s)")

                return DownloadResult(
                    url=url,
                    filename=filename,
                    filepath=filepath,
                    success=True,
                    size_bytes=wrote,
                    duration_s=duration
                )

            except Exception as e:
                err_msg = str(e)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass

                if attempt < retries and not self.stop_event.is_set():
                    if progress_callback:
                        progress_callback(f"Retry {attempt+1}/{retries} for {filename} after error: {err_msg}")
                    time.sleep(1.0)
                    continue

                if progress_callback:
                    progress_callback(f"Error downloading {filename}: {err_msg}")

                return DownloadResult(
                    url=url,
                    filename=filename,
                    success=False,
                    error=err_msg,
                    duration_s=time.time() - start_time
                )

        return DownloadResult(url=url, filename=filename, success=False, error="Exhausted retries")

    def download_from_ids(
        self,
        ids: List[str],
        formats: Optional[List[str]] = None,
        base_url: Optional[str] = None,
        format_urls: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        completion_callback: Optional[Callable[[], None]] = None
    ) -> BatchSummary:
        """
        Download multiple sutras for specified formats with thread pool parallelism.
        """
        self.reset()
        active_formats = [f.lower() for f in (formats or ["txt"])]
        summary = BatchSummary()

        # Build list of URLs to download
        download_queue: List[Tuple[str, str]] = []  # (url, filename)
        for sutra_id in ids:
            sutra_id = sutra_id.strip()
            if not sutra_id:
                continue
            for fmt in active_formats:
                try:
                    url = build_download_url(sutra_id, fmt, base_url=base_url, format_urls=format_urls)
                    download_queue.append((url, url.split("/")[-1]))
                except ValueError as err:
                    if progress_callback:
                        progress_callback(f"Skipping {sutra_id} ({fmt}): {err}")

        total_urls = len(download_queue)
        summary.total = total_urls

        if total_urls == 0:
            if progress_callback:
                progress_callback("No valid URLs generated to download.")
            if completion_callback:
                completion_callback()
            return summary

        os.makedirs(self.download_dir, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        completed_count = 0
        future_map = {
            self.executor.submit(self.download_file, url, self.download_dir, filename, progress_callback): (url, filename)
            for url, filename in download_queue
        }

        try:
            for future in as_completed(future_map):
                if self.stop_event.is_set():
                    summary.cancelled = True
                    break

                res: DownloadResult = future.result()
                summary.results.append(res)
                if res.success:
                    summary.succeeded += 1
                else:
                    summary.failed += 1

                completed_count += 1
                if progress_callback:
                    progress_callback(f"Progress: {completed_count}/{total_urls}")

        finally:
            self.executor.shutdown(wait=False, cancel_futures=True)

        if completion_callback:
            completion_callback()

        return summary

    def download_from_file(
        self,
        url_file_path: str,
        formats: Optional[List[str]] = None,
        base_url: Optional[str] = None,
        format_urls: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        completion_callback: Optional[Callable[[], None]] = None
    ) -> BatchSummary:
        """
        Download sutras listed in a text file.
        """
        if not os.path.exists(url_file_path):
            if progress_callback:
                progress_callback(f"ID/URL file not found: {url_file_path}")
            return BatchSummary()

        ids = parse_id_file(url_file_path)
        return self.download_from_ids(
            ids=ids,
            formats=formats,
            base_url=base_url,
            format_urls=format_urls,
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
