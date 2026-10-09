"""
Unit tests for core.headings module.
"""

import os
import pytest
from core.headings import (
    format_headings_in_text,
    format_md_file_headings,
    format_md_headings_in_directory,
    is_valid_heading_candidate,
    BAD_DI_WORDS
)


def test_is_valid_heading_candidate():
    assert is_valid_heading_candidate("成唯識論卷第一") is True
    assert is_valid_heading_candidate("序品第一") is True
    assert is_valid_heading_candidate("# Comment") is False
    assert is_valid_heading_candidate("// Comment") is False
    assert is_valid_heading_candidate("【大正藏】") is False
    assert is_valid_heading_candidate("CBETA 2026") is False
    assert is_valid_heading_candidate("有句號結尾。") is False
    assert is_valid_heading_candidate("有，逗號") is False
    assert is_valid_heading_candidate("經文卷終") is False


def test_multi_volume_headings():
    content = (
        "// Header\n"
        "長阿含經卷第一\n"
        "經文內容一\n"
        "長阿含經卷第一\n"  # 卷末重覆標題
        "長阿含經卷第二\n"
        "經文內容二\n"
    )
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[1] == "## 長阿含經卷第一"
    assert lines[3] == "長阿含經卷第一"  # 去重，不加 ##
    assert lines[4] == "## 長阿含經卷第二"


def test_single_volume_headings():
    content = (
        "// Header\n"
        "金剛般若波羅蜜經卷上\n"
        "序品第一\n"
        "內容...\n"
    )
    # 單卷經文不對卷名加 ##，但會對品名加 ##
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[1] == "金剛般若波羅蜜經卷上"  # 單卷不標記 ##
    assert lines[2] == "## 序品第一"


def test_pin_and_di_headings():
    content = (
        "序品第一\n"
        "第二品\n"
        "極喜地第一\n"
        "離垢地第二\n"
    )
    formatted, mod = format_headings_in_text(content)
    lines = formatted.splitlines()
    assert lines[0] == "## 序品第一"
    assert lines[1] == "## 第二品"
    assert lines[2] == "## 極喜地第一"
    assert lines[3] == "## 離垢地第二"


def test_bad_di_words_filtering():
    content = (
        "眾生墮於地獄\n"
        "大地震動\n"
        "遊行邊地\n"
        "極喜地第一\n"
    )
    formatted, mod = format_headings_in_text(content)
    lines = formatted.splitlines()
    assert lines[0] == "眾生墮於地獄"
    assert lines[1] == "大地震動"
    assert lines[2] == "遊行邊地"
    assert lines[3] == "## 極喜地第一"


def test_indentation_preservation():
    content = "  序品第一\n"
    formatted, mod = format_headings_in_text(content)
    assert formatted == "  ## 序品第一\n"


def test_format_md_headings_in_directory(temp_dir):
    f1 = os.path.join(temp_dir, "doc1.md")
    f2 = os.path.join(temp_dir, "doc2.md")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("序品第一\n經文\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("歡喜地第一\n經文\n")

    mod_count = format_md_headings_in_directory(temp_dir)
    assert mod_count == 2

    with open(f1, "r", encoding="utf-8") as f:
        assert f.readline().startswith("## 序品第一")


def test_juan_appears_twice_with_end_markers():
    """Test volume endings with classical suffix characters (終, 畢, 竟, 完) are never tagged with ##."""
    content = (
        "佛說長阿含經卷第一\n"
        "如是我聞...\n"
        "佛說長阿含經卷第一終\n"
        "佛說長阿含經卷第二\n"
        "爾時世尊...\n"
        "佛說長阿含經卷第二畢\n"
    )
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[0] == "## 佛說長阿含經卷第一"
    assert lines[2] == "佛說長阿含經卷第一終"  # 卷尾帶終字，不標記 ##
    assert lines[3] == "## 佛說長阿含經卷第二"
    assert lines[5] == "佛說長阿含經卷第二畢"  # 卷尾帶畢字，不標記 ##


def test_juan_appears_twice_num_format_variation():
    """Test volume start (卷第一) vs volume end (卷一) deduplication."""
    content = (
        "成唯識論卷第一\n"
        "護法菩薩造...\n"
        "成唯識論卷一\n"
        "成唯識論卷第二\n"
        "安慧菩薩造...\n"
        "成唯識論卷二\n"
    )
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[0] == "## 成唯識論卷第一"
    assert lines[2] == "成唯識論卷一"  # 卷尾無第字，同卷歸一化去重，不標記 ##
    assert lines[3] == "## 成唯識論卷第二"
    assert lines[5] == "成唯識論卷二"  # 卷尾無第字，同卷歸一化去重，不標記 ##


def test_juan_appears_twice_shortened_and_bare_title():
    """Test volume start with full title vs volume end with shortened or bare volume title."""
    content = (
        "大乘廣百論釋論卷第一\n"
        "經文內容...\n"
        "廣百論釋論卷第一\n"
        "大乘廣百論釋論卷第二\n"
        "經文內容...\n"
        "卷第二\n"
    )
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[0] == "## 大乘廣百論釋論卷第一"
    assert lines[2] == "廣百論釋論卷第一"  # 卷尾簡稱，同卷去重，不標記 ##
    assert lines[3] == "## 大乘廣百論釋論卷第二"
    assert lines[5] == "卷第二"  # 卷尾單獨卷號，同卷去重，不標記 ##


def test_pin_and_di_appears_twice_start_and_end():
    """Test Pin (品) and Di (地) appearing at both start and end of chapter."""
    content = (
        "序品第一\n"
        "內容...\n"
        "序品第一\n"
        "方便品第二\n"
        "內容...\n"
        "方便品第二\n"
    )
    formatted, mod = format_headings_in_text(content)
    assert mod is True
    lines = formatted.splitlines()

    assert lines[0] == "## 序品第一"
    assert lines[2] == "序品第一"  # 品尾，不重複加 ##
    assert lines[3] == "## 方便品第二"
    assert lines[5] == "方便品第二"  # 品尾，不重複加 ##


def test_headings_parsing_and_candidate_edge_cases(temp_dir):
    from core.headings import parse_cn_number, get_juan_key, get_pin_key, get_di_key

    # 1. Number parser
    assert parse_cn_number(None) is None
    assert parse_cn_number("100") == 100
    assert parse_cn_number("上") == "上"
    assert parse_cn_number("invalid_number") == "invalid_number"

    # 2. Key extractors on non-matching lines
    assert get_juan_key("無卷之文字") is None
    assert get_pin_key("無品之文字") is None
    assert get_di_key("無地之文字") is None

    # 3. Heading candidate rejections
    assert is_valid_heading_candidate("A" * 85) is False
    assert is_valid_heading_candidate("前段　　後段") is False
    assert is_valid_heading_candidate("成唯識論卷第一終") is False
    assert is_valid_heading_candidate("成唯識論卷第一訖") is False

    # 4. In-memory formatting empty and already formatted ##
    assert format_headings_in_text("") == ("", False)
    already = "## 成唯識論卷第一\n經文\n"
    res, mod = format_headings_in_text(already)
    assert "## ##" not in res
    assert "## 成唯識論卷第一" in res

    # 5. Directory formatting edge cases
    assert format_md_headings_in_directory(os.path.join(temp_dir, "nonexistent")) == 0
    empty_md_dir = os.path.join(temp_dir, "empty_md")
    os.makedirs(empty_md_dir)
    assert format_md_headings_in_directory(empty_md_dir) == 0


