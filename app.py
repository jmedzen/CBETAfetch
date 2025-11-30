from flask import Flask, render_template, request, jsonify, Response
import os
import threading
import time
import json
from downloader import SutraDownloader
from process import process_project, convert_to_md

app = Flask(__name__)

# Global state
logs = []
current_task = None
lock = threading.Lock()

def add_log(msg):
    with lock:
        logs.append(f"{time.strftime('%H:%M:%S')} - {msg}")

def log_callback(msg):
    add_log(msg)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def get_logs():
    def generate():
        last_idx = 0
        while True:
            with lock:
                if last_idx < len(logs):
                    new_logs = logs[last_idx:]
                    last_idx = len(logs)
                    yield f"data: {json.dumps(new_logs)}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    id_list_str = data.get('id_list')
    dest_dir = data.get('dest_dir')
    example_url = data.get('example_url')
    formats = data.get('formats', ['txt'])  # Default to txt if not specified

    html_url = data.get('html_url')
    pdf_url = data.get('pdf_url')
    epub_url = data.get('epub_url')
    mobi_url = data.get('mobi_url')

    if not id_list_str or not dest_dir:
        return jsonify({'status': 'error', 'message': 'Missing arguments'}), 400

    base_url = None
    if example_url:
        # Extract base url from example url
        if '/download/' in example_url:
            base_url = example_url.split('/download/')[0] + '/download/'
            
    # Helper to extract base from format url
    def extract_base(url):
        if url and '/download/' in url:
            return url.split('/download/')[0] + '/download/'
        return url

    format_urls = {
        'html': extract_base(html_url),
        'pdf': extract_base(pdf_url),
        'epub': extract_base(epub_url),
        'mobi': extract_base(mobi_url)
    }

    def parse_id_list(input_str):
        ids = []
        lines = input_str.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle ranges (e.g. T1500-T1505)
            if '-' in line:
                parts = line.split('-')
                if len(parts) == 2:
                    start_id = parts[0].strip()
                    end_id = parts[1].strip()
                    
                    # Extract prefix and number
                    # Assuming format like T1500 (1 letter prefix) or JB234 (2 letter prefix)
                    # We need to be careful. Let's assume the non-numeric part is the prefix.
                    import re
                    match_start = re.match(r"([A-Za-z]+)(\d+)", start_id)
                    match_end = re.match(r"([A-Za-z]+)(\d+)", end_id)
                    
                    if match_start and match_end:
                        prefix = match_start.group(1)
                        start_num = int(match_start.group(2))
                        end_num = int(match_end.group(2))
                        width = len(match_start.group(2)) # Keep zero padding width
                        
                        if prefix == match_end.group(1):
                            for i in range(start_num, end_num + 1):
                                ids.append(f"{prefix}{str(i).zfill(width)}")
                        else:
                            # Prefixes don't match, just add them as is? Or warn?
                            # For simplicity, treat as individual IDs if range logic fails
                            ids.append(start_id)
                            ids.append(end_id)
                    else:
                        ids.append(start_id)
                        ids.append(end_id)
            else:
                ids.append(line)
        return ids

    ids = parse_id_list(id_list_str)

    def run_download():
        add_log("Starting download task...")
        add_log(f"Selected formats: {', '.join(formats)}")
        add_log(f"Processing {len(ids)} IDs...")
        if base_url:
            add_log(f"Using Base URL: {base_url}")
        downloader = SutraDownloader(dest_dir)
        downloader.download_from_ids(ids, base_url=base_url, format_urls=format_urls, formats=formats, progress_callback=log_callback)
        add_log("Download task completed.")

    threading.Thread(target=run_download, daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    project_dir = data.get('project_dir')
    remove_zip = data.get('remove_zip', False)

    if not project_dir:
        return jsonify({'status': 'error', 'message': 'Missing project directory'}), 400

    if not os.path.exists(project_dir):
        return jsonify({'status': 'error', 'message': 'Project directory not found'}), 400

    def run_process():
        add_log("Starting process task...")
        try:
            process_project(project_dir, remove_zip=remove_zip, logger=log_callback)
        except Exception as e:
            add_log(f"Error: {e}")
        add_log("Process task completed.")

    threading.Thread(target=run_process, daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/convert_md', methods=['POST'])
def convert_md():
    data = request.json
    project_dir = data.get('project_dir')

    if not project_dir:
        return jsonify({'status': 'error', 'message': 'Missing project directory'}), 400

    if not os.path.exists(project_dir):
        return jsonify({'status': 'error', 'message': 'Project directory not found'}), 400

    def run_convert():
        add_log("Starting conversion to MD...")
        try:
            convert_to_md(project_dir, logger=log_callback)
        except Exception as e:
            add_log(f"Error: {e}")
        add_log("Conversion task completed.")

    threading.Thread(target=run_convert, daemon=True).start()
    return jsonify({'status': 'started'})

if __name__ == '__main__':
    # Open browser automatically
    threading.Timer(1.5, lambda: os.system('open http://127.0.0.1:10066')).start()
    app.run(port=10066, debug=True, use_reloader=False)
