#!/usr/bin/env python3
"""Test script for format selector feature"""
import sys
sys.path.insert(0, '/Users/jm/Drive/F2-antigravity/scratch/cbget')

from downloader import SutraDownloader
import os

def test_format_selector():
    print("=== Testing Format Selector ===\n")
    
    # Create test file
    test_file = "test_format_ids.txt"
    test_dir = "test_format_downloads"
    
    # Clean up if exists
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    
    def log(msg):
        print(f"LOG: {msg}")
    
    # Test 1: Single format (txt)
    print("Test 1: Single format (txt)")
    downloader = SutraDownloader(test_dir + "/test1")
    downloader.download_from_file(test_file, formats=['txt'], progress_callback=log)
    print()
    
    # Test 2: Multiple formats
    print("Test 2: Multiple formats (epub, pdf)")
    downloader2 = SutraDownloader(test_dir + "/test2")
    downloader2.download_from_file(test_file, formats=['epub', 'pdf'], progress_callback=log)
    print()
    
    # Test 3: With base URL override
    print("Test 3: With base URL (custom server)")
    downloader3 = SutraDownloader(test_dir + "/test3")
    downloader3.download_from_file(
        test_file, 
        base_url="https://cbdata.dila.edu.tw/stable/download/",
        formats=['mobi'],
        progress_callback=log
    )
    print()
    
    print("=== Format Selector Test Complete ===")
    print("Note: Downloads may fail due to network issues, but URL construction should be correct")

if __name__ == "__main__":
    test_format_selector()
