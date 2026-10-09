"""
CBETAfetch 2.0 - Text to Markdown Converter Engine
Converts combined CBETA .txt files to sanitized Markdown (.md),
normalizing `#` comment lines into `//` comments to prevent Markdown H1 collision,
and optionally triggering automated H2 heading formatting.
"""

import os
from typing import List, Optional, Callable
from core.headings import format_headings_in_text, format_md_file_headings


def sanitize_txt_for_markdown(content: str) -> str:
    """
    Sanitize CBETA text content for Markdown format:
    Replaces '#' headers/comments with '//'.
    """
    return content.replace("#", "//")


def convert_txt_file_to_md(
    txt_path: str,
    output_path: Optional[str] = None,
    auto_heading: bool = True,
    remove_source: bool = True,
    logger: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Convert a single .txt file to a .md file.
    
    Args:
        txt_path: Path to the source .txt file
        output_path: Optional destination .md path (defaults to same name with .md)
        auto_heading: Whether to apply H2 heading formatting
        remove_source: Whether to delete the original .txt file after successful conversion
        logger: Optional log callback
    """
    log = logger or (lambda msg: None)

    if not os.path.isfile(txt_path):
        log(f"Source file does not exist: {txt_path}")
        return False

    if not output_path:
        base_no_ext = os.path.splitext(txt_path)[0]
        # Clean trailing underscores if any
        base_clean = base_no_ext.rstrip("_")
        output_path = f"{base_clean}.md"

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        md_content = sanitize_txt_for_markdown(content)

        if auto_heading:
            md_content, _ = format_headings_in_text(md_content)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        if remove_source and os.path.abspath(txt_path) != os.path.abspath(output_path):
            os.remove(txt_path)

        log(f"Converted {os.path.basename(txt_path)} -> {os.path.basename(output_path)}")
        return True

    except Exception as e:
        log(f"Error converting {txt_path}: {e}")
        return False


def resolve_output_directory(working_dir: str, preferred_output: Optional[str] = None) -> str:
    """
    Determine the appropriate 'complete' directory for a working directory.
    If preferred_output is explicitly specified, uses that.
    Otherwise, checks if working_dir itself or child/sibling 'complete' exists.
    """
    if preferred_output:
        return os.path.abspath(preferred_output)

    abs_working = os.path.abspath(working_dir)

    # 1. If working_dir is named 'complete', use it directly
    if os.path.basename(abs_working).lower() == "complete":
        return abs_working

    # 2. If child directory 'complete' exists with .txt or .md files
    child_complete = os.path.join(abs_working, "complete")
    if os.path.isdir(child_complete):
        return child_complete

    # 3. If sibling directory 'complete' exists
    sibling_complete = os.path.join(os.path.dirname(abs_working), "complete")
    if os.path.isdir(sibling_complete):
        return sibling_complete

    # Default to creating sibling 'complete' if inside a downloads folder, otherwise child
    if os.path.basename(abs_working).lower() in ("downloads", "download"):
        return sibling_complete
    return child_complete


def convert_directory_to_md(
    target_dir: str,
    auto_heading: bool = True,
    remove_source: bool = True,
    logger: Optional[Callable[[str], None]] = None
) -> int:
    """
    Convert all .txt files in target_dir to .md files.
    
    Returns:
        Number of successfully converted files.
    """
    log = logger or (lambda msg: None)

    if not os.path.isdir(target_dir):
        log(f"Target directory does not exist: {target_dir}")
        return 0

    txt_files = [
        f for f in sorted(os.listdir(target_dir))
        if f.endswith(".txt") and not f.startswith(".")
    ]

    if not txt_files:
        log(f"No .txt files found in {target_dir}")
        return 0

    log(f"Converting {len(txt_files)} file(s) in {target_dir} to Markdown...")
    converted_count = 0

    for f in txt_files:
        txt_path = os.path.join(target_dir, f)
        clean_name = os.path.splitext(f)[0].rstrip("_") + ".md"
        md_path = os.path.join(target_dir, clean_name)

        if convert_txt_file_to_md(
            txt_path=txt_path,
            output_path=md_path,
            auto_heading=auto_heading,
            remove_source=remove_source,
            logger=logger
        ):
            converted_count += 1

    log(f"Conversion completed. {converted_count}/{len(txt_files)} files converted.")
    return converted_count


# Backward-compatible alias for legacy code
convert_to_md = convert_directory_to_md

