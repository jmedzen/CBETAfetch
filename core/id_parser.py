"""
CBETAfetch 2.0 - Sutra ID Parser & Validator
Handles single CBETA IDs, ranges, 1-letter and 2-letter canon prefixes, and comments.
"""

import re
from typing import List, Tuple, Optional


# Pattern matching CBETA Canon prefix (1-3 alpha characters) and serial number
CBETA_ID_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)([a-zA-Z]?)$")
CANON_PREFIX_PATTERN = re.compile(r"^([A-Za-z]+)")


def extract_canon(sutra_id: str) -> str:
    """
    Extract the canon code prefix from a CBETA sutra ID.
    Examples:
        'T1585'  -> 'T'
        'X0367'  -> 'X'
        'JB234'  -> 'JB'
        'ZS0010' -> 'ZS'
        'A0001'  -> 'A'
    """
    sutra_id = sutra_id.strip()
    match = CANON_PREFIX_PATTERN.match(sutra_id)
    if match:
        return match.group(1).upper()
    return ""


def validate_sutra_id(sutra_id: str) -> bool:
    """
    Validate whether a given string is a valid CBETA sutra ID.
    """
    if not sutra_id or not isinstance(sutra_id, str):
        return False
    return bool(CBETA_ID_PATTERN.match(sutra_id.strip()))


def parse_id_range(range_expr: str) -> List[str]:
    """
    Parse a range expression like 'T1500-T1505' or 'JB001-JB005'.
    If prefixes match, expands the range sequentially.
    If prefixes do not match or format is invalid, returns the distinct parsed parts.
    """
    parts = range_expr.split("-")
    if len(parts) != 2:
        clean = range_expr.strip()
        return [clean] if clean else []

    start_raw = parts[0].strip()
    end_raw = parts[1].strip()

    match_start = CBETA_ID_PATTERN.match(start_raw)
    match_end = CBETA_ID_PATTERN.match(end_raw)

    if not match_start or not match_end:
        # Fallback: if not standard patterned, return valid non-empty parts
        return [p for p in [start_raw, end_raw] if p]

    prefix_start, num_start_str, suffix_start = match_start.groups()
    prefix_end, num_end_str, suffix_end = match_end.groups()

    # Normalise prefixes to uppercase
    prefix_start = prefix_start.upper()
    prefix_end = prefix_end.upper()

    if prefix_start != prefix_end:
        # Cross-canon range is not expandable sequentially, return both endpoints
        return [f"{prefix_start}{num_start_str}{suffix_start}", f"{prefix_end}{num_end_str}{suffix_end}"]

    num_start = int(num_start_str)
    num_end = int(num_end_str)

    if num_start > num_end:
        # Descending or inverted, return both endpoints
        return [f"{prefix_start}{num_start_str}{suffix_start}", f"{prefix_end}{num_end_str}{suffix_end}"]

    width = len(num_start_str)
    results = []
    for i in range(num_start, num_end + 1):
        padded_num = str(i).zfill(width)
        results.append(f"{prefix_start}{padded_num}")

    return results


def parse_id_list(input_str: str, deduplicate: bool = True) -> List[str]:
    """
    Parse a multiline or delimiter-separated string containing CBETA IDs and ranges.
    Ignores empty lines and comments starting with '#'.
    
    Args:
        input_str: Multiline string of IDs or ranges
        deduplicate: If True, preserves first occurrence order and eliminates duplicates
    
    Returns:
        List of parsed CBETA IDs
    """
    if not input_str:
        return []

    collected: List[str] = []
    lines = input_str.replace(",", "\n").replace(";", "\n").splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "-" in line:
            expanded = parse_id_range(line)
            collected.extend(expanded)
        else:
            # Single ID - clean filename extensions or URLs if user pasted raw filenames
            cleaned = line.split("/")[-1].split(".")[0].strip()
            if cleaned:
                collected.append(cleaned.upper())

    if deduplicate:
        # Preserve insertion order while removing duplicates
        seen = set()
        unique_list = []
        for item in collected:
            if item not in seen:
                seen.add(item)
                unique_list.append(item)
        return unique_list

    return collected


def parse_id_file(file_path: str, deduplicate: bool = True) -> List[str]:
    """
    Parse IDs from a text file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_id_list(content, deduplicate=deduplicate)
