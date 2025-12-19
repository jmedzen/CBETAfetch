import os
import shutil
from process import process_folder

def run_test(name, files_to_create, expected_order):
    print(f"\n--- Testing Scenario: {name} ---")
    test_dir = f"test_dir_{name}"
    output_dir = f"test_out_{name}"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, content in files_to_create:
        with open(os.path.join(test_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)
            
    def mock_logger(msg): 
        if "processing" in msg.lower() or "finished" in msg.lower() or "order" in msg.lower():
            print(f"DEBUG: {msg}")
    
    # Process the folder
    process_folder(".", test_dir, output_dir, removeFolder=False, logger=mock_logger)
    
    # Verify result
    all_outputs = os.listdir(output_dir)
    print(f"DEBUG: All output files: {all_outputs}")
    output_file = [f for f in all_outputs if f.startswith("TTEST")][0]
    output_path = os.path.join(output_dir, output_file)
    
    with open(output_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.startswith("CONTENT:")]
        print(f"Result order: {lines}")
        
        expected_lines = [f"CONTENT: {c}" for c in expected_order]
        if lines == expected_lines:
            print(f"SUCCESS: {name}")
            shutil.rmtree(test_dir)
            shutil.rmtree(output_dir)
            return True
        else:
            print(f"FAILURE: {name}. Expected {expected_lines}, got {lines}")
            return False

def verify_all():
    results = []
    
    # 1. Sequential Volumes Only (T1811 case)
    results.append(run_test("Sequential_Only", [
        ("TTEST_001.txt", "# Header\nName\nCONTENT: 001\n"),
        ("TTEST_002.txt", "# Header\nName\nCONTENT: 002\n")
    ], ["001", "002"]))
    
    # 2. Volumes with TOC (T1516 case)
    # TOC is alphabetically first (TTEST-toc < TTEST_001)
    results.append(run_test("Volumes_with_TOC", [
        ("TTEST-toc.txt", "# Header\nName\nCONTENT: TOC\n"),
        ("TTEST_001.txt", "# Header\nName\nCONTENT: 001\n"),
        ("TTEST_002.txt", "# Header\nName\nCONTENT: 002\n")
    ], ["001", "002", "TOC"]))
    
    # 3. macOS Hidden files
    results.append(run_test("Hidden_Files", [
        ("._TTEST_001.txt", "Garbage"), 
        ("TTEST_001.txt", "# Header\nName\nCONTENT: 001\n"),
        ("TTEST_002.txt", "# Header\nName\nCONTENT: 002\n")
    ], ["001", "002"]))

    if all(results):
        print("\nALL ROBUST TESTS PASSED!")
    else:
        print("\nSOME TESTS FAILED.")

if __name__ == "__main__":
    verify_all()
