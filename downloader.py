import os
import urllib.request
import urllib.error
import ssl
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class SutraDownloader:
    def __init__(self, download_dir, max_workers=5):
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.stop_event = threading.Event()
        self.executor = None

    def download_file(self, url, progress_callback=None, log_progress_dots=False):
        if self.stop_event.is_set():
            return False, "Cancelled"
            
        filename = url.split('/')[-1]
        # Normalize download directory for cross-platform compatibility
        download_dir = os.path.abspath(os.path.normpath(self.download_dir))
        filepath = os.path.join(download_dir, filename)
        
        try:
            if progress_callback:
                progress_callback(f"Starting download: {filename}")
            
            # Create SSL context that doesn't verify certificates
            # This is safe for trusted sources like CBETA
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Use urllib to download
            with urllib.request.urlopen(url, timeout=30, context=ssl_context) as response:
                total_size = int(response.getheader('Content-Length') or 0)
                block_size = 8192
                wrote = 0
                last_log_size = 0
                log_interval = 5 * 1024 * 1024 # 5MB
                
                with open(filepath, 'wb') as f:
                    while True:
                        if self.stop_event.is_set():
                            break
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        wrote += len(chunk)
                        
                        if log_progress_dots and progress_callback:
                            if wrote - last_log_size >= log_interval:
                                progress_callback(".")
                                last_log_size = wrote
            
            if self.stop_event.is_set():
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False, "Cancelled"

            if progress_callback:
                progress_callback(f"Finished download: {filename}")
            return True, filename
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error downloading {filename}: {str(e)}")
            return False, str(e)

    def download_from_file(self, url_file_path, base_url=None, format_urls=None, formats=None, progress_callback=None, completion_callback=None):
        """
        Download files from a list, optionally overriding formats.
        
        Args:
            url_file_path: Path to file containing URLs or IDs
            base_url: Optional base URL (e.g., "https://cbdata.dila.edu.tw/stable/download/")
            format_urls: Optional dict of base URLs per format (e.g. {'html': '...', 'pdf': '...'})
            formats: Optional list of formats to download (e.g., ["txt", "epub", "pdf"])
            progress_callback: Optional callback for progress updates
            completion_callback: Optional callback when complete
        """
        if not os.path.exists(url_file_path):
            if progress_callback:
                progress_callback("URL file not found.")
            return

        # Read IDs from file
        with open(url_file_path, 'r') as f:
            lines = []
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                lines.append(line)

    def download_from_ids(self, ids, base_url=None, format_urls=None, formats=None, progress_callback=None, completion_callback=None):
        """
        Download files from a list of IDs.
        """
        # Determine base root URL
        root_base = None
        if base_url:
            if '/download/' in base_url:
                root_base = base_url.split('/download/')[0] + '/download/'
            else:
                root_base = base_url

        # Build URL list
        urls = []
        for id_str in ids:
            if not id_str:
                continue
                
            # Extract canon code (first letter)
            canon = id_str[0] if id_str else ''
            
            # Determine which formats to download
            download_formats = formats if formats else ['txt']  # Default to txt if not specified
            
            for fmt in download_formats:
                fmt = fmt.lower()
                
                # Construct URL based on format
                if format_urls and fmt in format_urls and format_urls[fmt]:
                    base = format_urls[fmt]
                elif root_base:
                    base = root_base
                else:
                    base = "https://cbdata.dila.edu.tw/stable/download/"
                
                if fmt == 'txt':
                    url = f"{base}text/{id_str}.txt.zip"
                elif fmt == 'html':
                    url = f"{base}html/{id_str}.html.zip"
                elif fmt == 'epub':
                    url = f"{base}epub/{canon}/{id_str}.epub"
                elif fmt == 'mobi':
                    url = f"{base}mobi/{canon}/{id_str}.mobi"
                elif fmt == 'pdf':
                    url = f"{base}pdf/{canon}/{id_str}.pdf"
                else:
                    if progress_callback:
                        progress_callback(f"Unknown format: {fmt}")
                    continue
                    
                urls.append(url)

        # Normalize and resolve the download directory path for cross-platform compatibility
        download_dir = os.path.abspath(os.path.normpath(self.download_dir))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        self.stop_event.clear()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        total_urls = len(urls)
        completed_count = 0
        
        def task_wrapper(url):
            return self.download_file(url, progress_callback)

        futures = [self.executor.submit(task_wrapper, url) for url in urls]
        
        for future in as_completed(futures):
            if self.stop_event.is_set():
                break
            success, result = future.result()
            completed_count += 1
            if progress_callback:
                progress_callback(f"Progress: {completed_count}/{total_urls}")

        self.executor.shutdown(wait=False)
        if completion_callback:
            completion_callback()

    def download_from_file(self, url_file_path, base_url=None, format_urls=None, formats=None, progress_callback=None, completion_callback=None):
        """
        Download files from a list, optionally overriding formats.
        """
        if not os.path.exists(url_file_path):
            if progress_callback:
                progress_callback("URL file not found.")
            return

        # Read IDs from file
        ids = []
        with open(url_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Extract ID from line (could be a full URL or just an ID)
                id_str = line.split('/')[-1]  # Get filename
                id_str = id_str.split('.')[0]  # Remove extension
                ids.append(id_str)

        self.download_from_ids(ids, base_url, format_urls, formats, progress_callback, completion_callback)

    def cancel(self):
        self.stop_event.set()
        if self.executor:
            self.executor.shutdown(wait=False)
