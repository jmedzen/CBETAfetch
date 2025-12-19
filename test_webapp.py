import threading
import time
import requests
import os
import shutil
import sys
from app import app

def run_server():
    app.run(port=10066, use_reloader=False)

def test_webapp():
    print("Starting Web App for testing...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2) # Wait for server to start

    base_url = "http://127.0.0.1:10066"

    # Test Index
    try:
        resp = requests.get(base_url + "/")
        if resp.status_code == 200:
            print("Index Page: OK")
        else:
            print(f"Index Page: Failed {resp.status_code}")
    except Exception as e:
        print(f"Index Page: Error {e}")

    # Test Download Endpoint (with fake data)
    # Create dummy url file
    with open("test_urls_web.txt", "w") as f:
        f.write("http://example.com/fake.zip\n")
    
    payload = {
        "url_file": os.path.abspath("test_urls_web.txt"),
        "dest_dir": os.path.abspath("test_download_web"),
        "example_url": "http://example.com/override/fake.zip"
    }
    
    try:
        resp = requests.post(base_url + "/download", json=payload)
        print(f"Download Endpoint: {resp.json()}")
    except Exception as e:
        print(f"Download Endpoint: Error {e}")

    # Test Process Endpoint (with fake data)
    os.makedirs("test_project_web", exist_ok=True)
    payload = {
        "project_dir": os.path.abspath("test_project_web"),
        "remove_zip": False
    }
    
    try:
        resp = requests.post(base_url + "/process", json=payload)
        print(f"Process Endpoint: {resp.json()}")
    except Exception as e:
        print(f"Process Endpoint: Error {e}")

    # Cleanup
    if os.path.exists("test_urls_web.txt"):
        os.remove("test_urls_web.txt")
    if os.path.exists("test_download_web"):
        shutil.rmtree("test_download_web")
    if os.path.exists("test_project_web"):
        shutil.rmtree("test_project_web")
    
    print("Web App Test Finished")

if __name__ == "__main__":
    test_webapp()
