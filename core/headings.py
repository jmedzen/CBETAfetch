"""
CBETAfetch 2.0 - Markdown Headings Engine
Applies intelligent H2 (##) heading formatting to Buddhist scripture texts.
Rules:
1. Multi-volume: If file contains >= 2 distinct Juan (卷) titles, marks ONLY the FIRST occurrence
   of each volume (卷首) with '## '. The second occurrence at the end of the volume (卷尾)
   is strictly preserved as normal body text.
2. Single-volume: Preserves Juan title without '## ' (prevents redundant title duplication).
3. Chapters & Stages: Marks ONLY the FIRST occurrence of Pin (品) and Di (地) titles with '## '.
4. False-positive filtering: Excludes non-heading phrases (e.g., 地獄, 大地, 邊地) and punctuation.
5. End-of-volume / chapter markers: Lines ending with 終, 畢, 竟, 完, 結, 訖, 分 are recognized
   as endings and are never marked as H2.
6. Normalized Key Deduplication: Converts Chinese numerals (卷第一 vs 卷一) into unified keys
   to ensure variations at volume ends (卷尾) are never falsely tagged as new H2 headers.
"""

import os
import re
from typing import List, Set, Tuple, Optional, Callable, Union

# Chinese numeral mapping
CN_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "百": 100, "千": 1000
}

# Regex patterns
CN_NUM_PATTERN = r"[一二三四五六七八九十百千0-9]+"

RE_JUAN_EXTRACT = re.compile(r"卷(?:第?([一二三四五六七八九十百千0-9]+)|([上中下]))")
RE_JUAN_TITLE = re.compile(r"^[^\n]*?卷(?:第?" + CN_NUM_PATTERN + r"|[上下中])[^\n]*$")

RE_PIN_EXTRACT = re.compile(r"(?:品第?([一二三四五六七八九十百千0-9]+)|第([一二三四五六七八九十百千0-9]+)品)")
RE_PIN_TITLE = re.compile(
    r"^[^\n]*?(?:品第?" + CN_NUM_PATTERN + r"|第" + CN_NUM_PATTERN + r"品|品(?:第一|第二|第三|第四|第五|第六|第七|第八|第九|第十))[^\n]*$"
)

RE_DI_EXTRACT = re.compile(r"(?:地第?([一二三四五六七八九十百千0-9]+)|第([一二三四五六七八九十百千0-9]+)地)")
RE_DI_TITLE = re.compile(
    r"^[^\n]*?(?:地第?" + CN_NUM_PATTERN + r"|第" + CN_NUM_PATTERN + r"地|地(?:第一|第二|第三|第四|第五|第六|第七|第八|第九|第十))[^\n]*$"
)

PUNCTUATIONS = ("，", "。", "！", "？", "；", "「", "」", "『", "』", "：", "、", "．")

BAD_DI_WORDS = (
    "地獄", "大地", "邊地", "土地", "草地", "掃地", "平地", "黑地", "勝地", "心地觀",
    "如地", "住地", "地中", "心地印", "地水火風", "墓地", "露地", "偏僻地", "坐於地", "至地"
)

# Explicit end-of-volume/chapter characters in classical Buddhist texts
END_OF_VOLUME_CHARACTERS = ("終", "畢", "竟", "完", "結", "訖", "分")


def parse_cn_number(s: Optional[str]) -> Optional[Union[int, str]]:
    """
    Convert Chinese numeral strings (e.g. '一', '十', '二十一', '一百二十')
    or Arabic numbers to integer. Returns '上'/'中'/'下' as strings.
    """
    if not s:
        return None
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s in ("上", "中", "下"):
        return s

    total = 0
    curr = 0
    for char in s:
        if char in CN_NUM_MAP:
            val = CN_NUM_MAP[char]
            if val in (10, 100, 1000):
                total += (curr or 1) * val
                curr = 0
            else:
                curr = val
        else:
            return s
    return total + curr


def get_juan_key(line_str: str) -> Optional[Union[int, str]]:
    """
    Extract normalized volume key from a line containing 卷.
    Examples:
        '成唯識論卷第一' -> 1
        '成唯識論卷一'   -> 1
        '成唯識論卷第一終' -> 1
        '金剛經卷上'     -> '上'
    """
    m = RE_JUAN_EXTRACT.search(line_str)
    if m:
        num_str = m.group(1) or m.group(2)
        return parse_cn_number(num_str)
    return None


def get_pin_key(line_str: str) -> Optional[Union[int, str]]:
    """Extract normalized chapter key from a line containing 品."""
    m = RE_PIN_EXTRACT.search(line_str)
    if m:
        num_str = m.group(1) or m.group(2)
        return parse_cn_number(num_str)
    return None


def get_di_key(line_str: str) -> Optional[Union[int, str]]:
    """Extract normalized stage key from a line containing 地."""
    m = RE_DI_EXTRACT.search(line_str)
    if m:
        num_str = m.group(1) or m.group(2)
        return parse_cn_number(num_str)
    return None


def is_valid_heading_candidate(line_str: str) -> bool:
    """
    Check if a line can possibly be a canonical Buddhist heading.
    Filters out comments, long lines, publisher metadata, punctuation,
    and explicit volume/chapter endings (卷尾標記如 終, 畢, 竟, 完, 結, 訖).
    """
    if not line_str or line_str.startswith("//") or line_str.startswith("#"):
        return False
    if len(line_str) > 80:
        return False
    if "【" in line_str or "No." in line_str or "CBETA" in line_str:
        return False
    if any(p in line_str for p in PUNCTUATIONS):
        return False
    if "　　" in line_str:
        return False

    # Filter explicit volume/chapter endings (卷尾)
    for end_char in END_OF_VOLUME_CHARACTERS:
        if line_str.endswith(end_char) or f"{end_char}\n" in line_str:
            return False

    return True


def format_headings_in_text(content: str) -> Tuple[str, bool]:
    """
    Format headings within an in-memory Markdown string.
    Ensures that Juan (卷) titles appearing at both volume start (卷首)
    and volume end (卷尾) only receive '## ' on the FIRST occurrence.
    
    Returns:
        Tuple of (formatted_content, was_modified)
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return content, False

    # Pass 1: Collect unique volume keys to determine if multi-volume
    juan_keys: Set[Union[int, str]] = set()
    for line in lines:
        st = line.strip()
        # Strip existing ## if already present to parse cleanly
        if st.startswith("## "):
            st = st[3:].strip()
        if is_valid_heading_candidate(st) and RE_JUAN_TITLE.match(st):
            k = get_juan_key(st)
            if k is not None:
                juan_keys.add(k)

    has_multi_juan = len(juan_keys) >= 2

    modified = False
    new_lines: List[str] = []

    # Seen sets for deduplication
    seen_volume_keys: Set[Union[int, str]] = set()
    seen_pin_keys: Set[Union[int, str]] = set()
    seen_di_keys: Set[Union[int, str]] = set()
    seen_literal_lines: Set[str] = set()

    # Pass 2: Apply ## ONLY on the FIRST occurrence of each volume/chapter
    for line in lines:
        st = line.strip()

        # If line is already an H2 header (e.g. from prior conversion)
        if st.startswith("## "):
            actual_title = st[3:].strip()
            # Register volume key so subsequent 卷尾 are never tagged
            if RE_JUAN_TITLE.match(actual_title):
                k = get_juan_key(actual_title)
                if k is not None:
                    seen_volume_keys.add(k)
            seen_literal_lines.add(actual_title)
            new_lines.append(line)
            continue

        if not is_valid_heading_candidate(st):
            new_lines.append(line)
            continue

        is_j = bool(RE_JUAN_TITLE.match(st))
        is_p = bool(RE_PIN_TITLE.match(st))
        is_d = bool(RE_DI_TITLE.match(st)) and not any(bad in st for bad in BAD_DI_WORDS)

        if is_j:
            k = get_juan_key(st)
            # If we already encountered this volume number, this is 卷尾 (end of volume) -> DO NOT MARK H2!
            if k is not None and k in seen_volume_keys:
                new_lines.append(line)
                continue

            # Also check exact literal string deduplication
            if st in seen_literal_lines:
                new_lines.append(line)
                continue

            # First occurrence of this volume (卷首)
            if k is not None:
                seen_volume_keys.add(k)
            seen_literal_lines.add(st)

            if has_multi_juan:
                leading_spaces = line[: len(line) - len(line.lstrip())]
                line_ending = "\n" if line.endswith("\n") else ""
                new_lines.append(f"{leading_spaces}## {st}{line_ending}")
                modified = True
            else:
                new_lines.append(line)

        elif is_p:
            pk = get_pin_key(st)
            # If chapter number already seen, this is 品尾 (end of chapter) -> DO NOT MARK H2!
            if pk is not None and pk in seen_pin_keys:
                new_lines.append(line)
                continue
            if st in seen_literal_lines:
                new_lines.append(line)
                continue

            if pk is not None:
                seen_pin_keys.add(pk)
            seen_literal_lines.add(st)

            leading_spaces = line[: len(line) - len(line.lstrip())]
            line_ending = "\n" if line.endswith("\n") else ""
            new_lines.append(f"{leading_spaces}## {st}{line_ending}")
            modified = True

        elif is_d:
            dk = get_di_key(st)
            if dk is not None and dk in seen_di_keys:
                new_lines.append(line)
                continue
            if st in seen_literal_lines:
                new_lines.append(line)
                continue

            if dk is not None:
                seen_di_keys.add(dk)
            seen_literal_lines.add(st)

            leading_spaces = line[: len(line) - len(line.lstrip())]
            line_ending = "\n" if line.endswith("\n") else ""
            new_lines.append(f"{leading_spaces}## {st}{line_ending}")
            modified = True

        else:
            new_lines.append(line)

    return "".join(new_lines), modified


def format_md_file_headings(
    filepath: str,
    logger: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Format H2 headings in a single markdown file on disk.
    """
    log = logger or (lambda msg: None)
    try:
        with open(filepath, "r", encoding="utf-8") as fp:
            content = fp.read()
    except Exception as e:
        log(f"Error reading {filepath}: {e}")
        return False

    formatted_content, modified = format_headings_in_text(content)

    if modified:
        try:
            with open(filepath, "w", encoding="utf-8") as fp:
                fp.write(formatted_content)
            return True
        except Exception as e:
            log(f"Error writing {filepath}: {e}")
            return False

    return False


def format_md_headings_in_directory(
    target: str,
    logger: Optional[Callable[[str], None]] = None
) -> int:
    """
    Format H2 headings for a single markdown file or all markdown files in a directory recursively.
    
    Returns:
        Count of modified files.
    """
    log = logger or (lambda msg: None)

    if os.path.isfile(target):
        if target.endswith(".md"):
            log(f"Formatting headings in {target}...")
            return 1 if format_md_file_headings(target, logger=logger) else 0
        return 0

    if not os.path.isdir(target):
        log(f"Target path does not exist: {target}")
        return 0

    md_files = []
    for root, _, filenames in os.walk(target):
        for fn in filenames:
            if fn.endswith(".md") and not fn.startswith("."):
                md_files.append(os.path.join(root, fn))
    md_files.sort()

    if not md_files:
        log(f"No .md files found in {target}")
        return 0

    log(f"Formatting H2 headings in {len(md_files)} markdown files...")
    count = 0
    for filepath in md_files:
        if format_md_file_headings(filepath, logger=logger):
            count += 1
    log(f"Heading formatting complete. Modified {count} files.")
    return count


# Backward-compatible alias for legacy code
format_md_headings = format_md_headings_in_directory
