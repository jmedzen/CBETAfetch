"""
CBETAfetch 2.0 - Sutra Text Processor Engine
Extracts zip archives, orders volume & TOC files, extracts scripture metadata,
combines multi-volume texts while filtering redundant comment blocks,
and manages batch processing for the entire CBETA text collection.
"""

import os
import re
import shutil
import zipfile
from glob import glob
from typing import List, Optional, Callable, Tuple, Dict, Any

from core.converter import convert_to_md, resolve_output_directory, convert_directory_to_md
from core.headings import format_md_headings_in_directory
from core.progress import format_progress_line


def default_logger(msg: str) -> None:
    print(msg)


def sanitize_filename(filename: str) -> str:
    """
    Remove characters that are invalid in Windows / POSIX file paths.
    """
    # Replace invalid chars with empty or underscore
    cleaned = re.sub(r'[\\/*?:"<>|]', '', filename)
    return cleaned.strip()


def extract_sutra_metadata(first_file_path: str) -> Tuple[str, str]:
    """
    Extract Sutra ID and Sutra Name from the first volume file.
    Follows CBETA convention where line 2 contains the scripture title.
    
    Returns:
        (sutra_id, sutra_name)
    """
    filename = os.path.basename(first_file_path)
    sutra_id = filename.split("_")[0].split(".")[0].strip()

    sutra_name = ""
    try:
        with open(first_file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline().strip() for _ in range(5)]

        # Line 2 typically has: '# No. 1585 成唯識論' or 'No. 1585 成唯識論' or '大乘百法明門論'
        # Check line index 1 (second line) first as in legacy CBETA convention
        candidate_lines = []
        if len(lines) >= 2 and lines[1]:
            candidate_lines.append(lines[1])
        # Add remaining non-empty lines as fallbacks
        for idx, l in enumerate(lines):
            if idx != 1 and l:
                candidate_lines.append(l)

        for line in candidate_lines:
            clean_line = line.lstrip("#").strip()
            # Remove publisher boilerplate if any
            if "CBETA" in clean_line or "Electronic Tripitaka" in clean_line:
                continue
            tokens = [t for t in re.split(r"\s+", clean_line) if t]
            if not tokens:
                continue

            # Pick last token, or second to last if last is empty
            candidate = tokens[-1]
            candidate = re.sub(r"^\[.*?\]", "", candidate).strip()
            if candidate and not candidate.startswith("No.") and not candidate.startswith("CBETA"):
                sutra_name = candidate
                break

    except Exception:
        pass

    sutra_name = sanitize_filename(sutra_name)
    return sutra_id, sutra_name


def sort_volume_files(file_paths: List[str]) -> List[str]:
    """
    Sort CBETA volume files:
    1. Regular volumes in natural alphabetical order (e.g., T1585_001, T1585_002)
    2. Table of Contents (TOC) files placed at the very end.
    3. Filters out hidden files (e.g., ._*)
    """
    # Filter hidden files
    visible_files = [
        f for f in file_paths
        if not os.path.basename(f).startswith(".")
    ]

    tocs = [
        f for f in visible_files
        if "-toc" in os.path.basename(f).lower() or "_toc" in os.path.basename(f).lower()
    ]
    volumes = [f for f in visible_files if f not in tocs]

    volumes.sort(key=lambda x: os.path.basename(x))
    tocs.sort(key=lambda x: os.path.basename(x))

    return volumes + tocs


def process_folder(
    parent_dir: str,
    folder_name: str,
    output_dir: str,
    remove_folder: bool = False,
    logger: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """
    Process a single folder containing CBETA .txt files:
    combines all volumes into a single file with format: {sutra_id}《{sutra_name}》.txt
    
    Returns:
        The path of the created combined file, or None if no files were processed.
    """
    log = logger or default_logger
    target_path = os.path.join(parent_dir, folder_name)
    log(f"Processing folder: {target_path}")

    # Gather .txt files
    txt_list = [
        os.path.join(target_path, f)
        for f in os.listdir(target_path)
        if f.endswith(".txt") and not f.startswith(".")
    ]

    if not txt_list:
        log(f"No .txt files found in {target_path}")
        return None

    # Sort volume files with TOCs at the end
    txt_list = sort_volume_files(txt_list)
    sutra_vols = len(txt_list)

    # Extract ID and Name
    sutra_id, sutra_name = extract_sutra_metadata(txt_list[0])
    if not sutra_name:
        sutra_name = folder_name

    log(f"SUTRA_ID: {sutra_id} | SUTRA_NAME: {sutra_name} | VOLS: {sutra_vols}")

    os.makedirs(output_dir, exist_ok=True)
    combined_filename = f"{sutra_id}《{sutra_name}》.txt"
    output_filepath = os.path.join(output_dir, combined_filename)

    # Combine volumes
    is_first_file = True
    last_line_ended_with_newline = True
    with open(output_filepath, "w", encoding="utf-8") as out:
        for fpath in txt_list:
            if not is_first_file and not last_line_ended_with_newline:
                out.write("\n")
            with open(fpath, "r", encoding="utf-8-sig", errors="replace") as infile:
                for line in infile:
                    clean_l = line.lstrip("\ufeff")
                    if clean_l.startswith("#"):
                        if is_first_file:
                            out.write(clean_l)
                    else:
                        out.write(clean_l)
                    last_line_ended_with_newline = clean_l.endswith("\n")
            is_first_file = False

    log(f"Finished processing: {output_filepath}")

    if remove_folder and os.path.isdir(target_path):
        try:
            shutil.rmtree(target_path)
        except Exception as e:
            log(f"Could not remove folder {target_path}: {e}")

    return output_filepath


def extract_all_zips(
    working_dir: str,
    remove_zip: bool = False,
    logger: Optional[Callable[[str], None]] = None
) -> int:
    """
    Recursively extract all .zip files under working_dir.
    
    Returns:
        Number of successfully extracted zip archives.
    """
    log = logger or default_logger
    extracted_count = 0

    zip_files = []
    for root, _, files in os.walk(working_dir):
        for f in files:
            if f.lower().endswith(".zip") and not f.startswith("."):
                zip_files.append(os.path.join(root, f))

    for zip_path in zip_files:
        filename = os.path.basename(zip_path)
        zip_dir = os.path.dirname(zip_path)

        # Name extract folder: strip .zip or .txt.zip
        m = re.search(r"(.*?)(?:\.txt)?\.zip$", filename, re.IGNORECASE)
        extract_name = m.group(1) if m else filename[:-4]
        extract_dir = os.path.join(zip_dir, extract_name)
        os.makedirs(extract_dir, exist_ok=True)

        log(f"Extracting {filename} to {extract_dir}...")
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_dir)
            extracted_count += 1
        except Exception as e:
            log(f"Error extracting zip {filename}: {e}")
            if os.path.isdir(extract_dir) and not os.listdir(extract_dir):
                try:
                    os.rmdir(extract_dir)
                except OSError:
                    pass
            continue

        if remove_zip:
            try:
                os.remove(zip_path)
            except Exception as e:
                log(f"Failed to remove zip {zip_path}: {e}")

    return extracted_count


def process_project(
    working_dir: str,
    output_dir: Optional[str] = None,
    remove_zip: bool = False,
    logger: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    High-level project processor:
    1. Extracts all zip files
    2. Identifies all sub-directories containing .txt files
    3. Combines volumes into the output directory ('complete')
    
    Returns:
        List of generated combined file paths.
    """
    log = logger or default_logger

    if not os.path.isdir(working_dir):
        log(f"Project directory not found: {working_dir}")
        return []

    log(f"Working directory: {working_dir}")

    # Determine output directory
    final_output_dir = resolve_output_directory(working_dir, preferred_output=output_dir)
    os.makedirs(final_output_dir, exist_ok=True)
    log(f"Target complete directory: {final_output_dir}")

    # 1. Extract zips
    extract_all_zips(working_dir, remove_zip=remove_zip, logger=logger)

    # 2. Find folders containing .txt files
    folders_to_process = []
    for root, _, files in os.walk(working_dir):
        # Do not process files inside the output complete directory itself!
        if os.path.abspath(root).startswith(os.path.abspath(final_output_dir)):
            continue
        txt_files = [f for f in files if f.endswith(".txt") and not f.startswith(".")]
        if txt_files:
            folders_to_process.append(root)

    total_folders = len(folders_to_process)
    log(f"Found {total_folders} folder(s) to process.")

    created_files = []
    for folder_path in sorted(folders_to_process):
        folder_name = os.path.basename(folder_path)
        parent = os.path.dirname(folder_path)
        res = process_folder(
            parent_dir=parent,
            folder_name=folder_name,
            output_dir=final_output_dir,
            remove_folder=remove_zip,
            logger=logger
        )
        if res:
            created_files.append(res)

    log(f"Process task completed. Generated {len(created_files)} combined scripture files.")
    return created_files


def process_cbeta_text_pack(
    zip_path: str,
    dest_dir: str,
    output_dir: Optional[str] = None,
    remove_zip: bool = False,
    convert_md: bool = True,
    auto_heading: bool = True,
    logger: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    Process the entire CBETA complete text pack (e.g. cbeta-text.zip).
    Unzips the archive, processes thousands of sutra folders,
    combines all volumes, and converts to Markdown with H2 headings.
    """
    log = logger or default_logger

    if not os.path.isfile(zip_path):
        log(f"Zip file not found: {zip_path}")
        return []

    extract_dir = os.path.join(dest_dir, "cbeta-text")
    os.makedirs(extract_dir, exist_ok=True)

    log(f"Unzipping complete pack {zip_path} to {extract_dir}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
    except Exception as e:
        log(f"Error unzipping pack: {e}")
        return []

    log("Unzip completed. Scanning for sutra folders...")

    final_output_dir = output_dir or os.path.join(dest_dir, "complete")
    os.makedirs(final_output_dir, exist_ok=True)

    folders_to_process = []
    for root, _, files in os.walk(extract_dir):
        txt_files = [f for f in files if f.endswith(".txt") and not f.startswith(".")]
        if txt_files:
            folders_to_process.append(root)

    total = len(folders_to_process)
    log(f"Found {total} sutra folders to process.")

    created_files = []
    for i, folder_path in enumerate(sorted(folders_to_process)):
        folder_name = os.path.basename(folder_path)
        parent = os.path.dirname(folder_path)

        if total > 0:
            percent = (i / total) * 100.0
            if (total > 50 and i % max(1, total // 50) == 0) or total <= 50 or i == total - 1:
                log(format_progress_line(
                    percent=percent,
                    current_count=i + 1,
                    total_count=total,
                    label=f"正在處理: {folder_name}"
                ))

        out = process_folder(
            parent_dir=parent,
            folder_name=folder_name,
            output_dir=final_output_dir,
            remove_folder=False,
            logger=logger
        )
        if out:
            created_files.append(out)

    log(f"Processing completed: {len(created_files)} combined scriptures created.")

    if convert_md:
        log("Converting combined scriptures to Markdown (.md)...")
        convert_directory_to_md(final_output_dir, auto_heading=auto_heading, logger=logger)
    else:
        log("Skipping Markdown conversion as requested.")

    if remove_zip:
        log(f"Removing source archive: {zip_path}")
        try:
            os.remove(zip_path)
        except OSError as e:
            log(f"Error removing source archive: {e}")

    log("All tasks completed successfully.")
    return created_files


def organize_downloaded_artifacts(
    working_dir: str,
    output_dir: str,
    logger: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    Organize non-txt e-books, documents, and data artifacts into the completed output library:
    - Collects and archives .pdf, .epub, .mobi, .docusky.xml, .docx, .odt
    - Unpacks docx/odt zip packages from CBETA into clean documents in output_dir
    
    Returns:
        List of organized deliverable paths.
    """
    log = logger or default_logger
    abs_working = os.path.abspath(working_dir)
    abs_output = os.path.abspath(output_dir)
    os.makedirs(abs_output, exist_ok=True)

    organized_paths = []
    doc_extensions = (".pdf", ".epub", ".mobi", ".docx", ".odt", ".docusky.xml")

    for root, _, files in os.walk(abs_working):
        if os.path.abspath(root).startswith(abs_output):
            continue
        for f in files:
            if f.startswith("."):
                continue
            src_path = os.path.join(root, f)
            f_lower = f.lower()

            # 1. Direct document/ebook files
            if any(f_lower.endswith(ext) for ext in doc_extensions):
                dest_path = os.path.join(abs_output, f)
                try:
                    shutil.copy2(src_path, dest_path)
                    organized_paths.append(dest_path)
                    log(f"已歸檔文件/電子書: {f}")
                except Exception as e:
                    log(f"歸檔檔案 {f} 失敗: {e}")

            # 2. CBETA docx/odt zip packages
            elif f_lower.endswith(".zip") and not f_lower.endswith(".txt.zip") and not f_lower.endswith(".html.zip"):
                try:
                    with zipfile.ZipFile(src_path, "r") as z:
                        names = z.namelist()
                        if any(n.lower().endswith((".docx", ".odt")) for n in names):
                            z.extractall(abs_output)
                            for n in names:
                                if n.lower().endswith((".docx", ".odt")):
                                    organized_paths.append(os.path.join(abs_output, n))
                            log(f"已解壓排版文檔包: {f}")
                except Exception as e:
                    log(f"檢查壓縮包 {f} 失敗: {e}")

    return organized_paths

