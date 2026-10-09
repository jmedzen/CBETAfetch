"""
Unit tests for core.converter module.
"""

import os
import pytest
from core.converter import (
    sanitize_txt_for_markdown,
    convert_txt_file_to_md,
    convert_directory_to_md,
    resolve_output_directory
)


def test_sanitize_txt_for_markdown():
    raw = "# Line 1\nContent # with hash\n# Line 2"
    sanitized = sanitize_txt_for_markdown(raw)
    assert sanitized == "// Line 1\nContent // with hash\n// Line 2"


def test_convert_txt_file_to_md(temp_dir):
    txt_path = os.path.join(temp_dir, "T1585_《成唯識論》_.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# Comment\n序品第一\n經文內容\n")

    md_path = os.path.join(temp_dir, "T1585《成唯識論》.md")
    success = convert_txt_file_to_md(
        txt_path=txt_path,
        output_path=md_path,
        auto_heading=True,
        remove_source=True
    )

    assert success is True
    assert not os.path.exists(txt_path)  # Source removed
    assert os.path.exists(md_path)

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "// Comment" in content
    assert "## 序品第一" in content


def test_convert_directory_to_md(temp_dir):
    f1 = os.path.join(temp_dir, "sutra1.txt")
    f2 = os.path.join(temp_dir, "sutra2.txt")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("# C1\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("# C2\n")

    count = convert_directory_to_md(temp_dir, remove_source=True)
    assert count == 2
    assert not os.path.exists(f1)
    assert not os.path.exists(f2)
    assert os.path.exists(os.path.join(temp_dir, "sutra1.md"))
    assert os.path.exists(os.path.join(temp_dir, "sutra2.md"))


def test_resolve_output_directory(temp_dir):
    # 1. Custom preferred output
    custom = os.path.join(temp_dir, "my_complete")
    assert resolve_output_directory(temp_dir, preferred_output=custom) == custom

    # 2. Complete child dir exists
    child = os.path.join(temp_dir, "complete")
    os.makedirs(child)
    assert resolve_output_directory(temp_dir) == child

    # 3. Working dir named 'complete'
    assert resolve_output_directory(child) == child

    # 4. Working dir named 'downloads' defaults to sibling complete
    dl_dir = os.path.join(temp_dir, "downloads")
    os.makedirs(dl_dir)
    assert resolve_output_directory(dl_dir) == os.path.join(temp_dir, "complete")


def test_convert_txt_file_edge_cases(temp_dir):
    # 1. Non-existent file
    assert convert_txt_file_to_md(os.path.join(temp_dir, "nonexistent.txt")) is False

    # 2. Output path auto-generated and remove_source=False
    f = os.path.join(temp_dir, "test_auto_.txt")
    with open(f, "w", encoding="utf-8") as fp:
        fp.write("content")
    ok = convert_txt_file_to_md(f, remove_source=False)
    assert ok is True
    assert os.path.exists(f)
    assert os.path.exists(os.path.join(temp_dir, "test_auto.md"))

    # 3. Directory non-existent
    assert convert_directory_to_md(os.path.join(temp_dir, "no_dir")) == 0

    # 4. Directory with no txt files
    empty_d = os.path.join(temp_dir, "empty")
    os.makedirs(empty_d)
    assert convert_directory_to_md(empty_d) == 0

