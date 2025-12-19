import os
import shutil
from downloader import SutraDownloader
from process import process_project

def test_downloader():
    print("Testing Downloader...")
    # Create a dummy url file
    with open("test_urls.txt", "w") as f:
        # Use a small file for testing if possible, or just check if it handles errors gracefully
        # Let's try to download a small file from a reliable source or just mock it?
        # Since I can't easily mock network, I'll test the class structure and error handling with a fake URL
        f.write("http://example.com/nonexistent_file.zip\n")
    
    downloader = SutraDownloader("test_download")
    
    def progress(msg):
        print(f"Downloader: {msg}")
        
    def complete():
        print("Downloader: Complete")
        
    downloader.download_from_file("test_urls.txt", progress_callback=progress, completion_callback=complete)
    
    # Clean up
    if os.path.exists("test_urls.txt"):
        os.remove("test_urls.txt")
    if os.path.exists("test_download"):
        shutil.rmtree("test_download")
    print("Downloader Test Finished (Expected errors for fake URL)")

def test_process():
    print("\nTesting Processor...")
    # Create a dummy project structure
    os.makedirs("test_project/T0001", exist_ok=True)
    with open("test_project/T0001/T0001_001.txt", "w") as f:
        f.write("# Comment\n")
        f.write("Line 1\n")
        f.write("Line 2 SutraName\n")
    
    # Create a dummy zip to test extraction logic (mocking it by just creating the file)
    # Actually, process_project expects zips. Let's create a real zip.
    import zipfile
    with open("dummy.txt", "w") as f:
        f.write("dummy content")
    
    with zipfile.ZipFile("test_project/test.txt.zip", "w") as z:
        z.write("dummy.txt")
    os.remove("dummy.txt")
    
    def logger(msg):
        print(f"Processor: {msg}")
        
    process_project("test_project", remove_zip=False, logger=logger)
    
    # Check if extracted
    if os.path.exists("test_project/test"):
        print("Processor: Extraction successful")
    else:
        print("Processor: Extraction failed or skipped")
        
    # Clean up
    shutil.rmtree("test_project")
    print("Processor Test Finished")

if __name__ == "__main__":
    test_downloader()
    test_process()
