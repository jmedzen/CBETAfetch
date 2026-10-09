"""
Unit tests for core.id_parser module.
"""

import os
import pytest
from core.id_parser import (
    extract_canon,
    validate_sutra_id,
    parse_id_range,
    parse_id_list,
    parse_id_file
)


def test_extract_canon_single_and_multi_letter():
    assert extract_canon("T1585") == "T"
    assert extract_canon("X0367") == "X"
    assert extract_canon("A0001") == "A"
    assert extract_canon("JB234") == "JB"
    assert extract_canon("ZS0010") == "ZS"
    assert extract_canon("GA0050") == "GA"
    assert extract_canon("t1585") == "T"
    assert extract_canon("jb234") == "JB"
    assert extract_canon("") == ""
    assert extract_canon("1234") == ""


def test_validate_sutra_id():
    assert validate_sutra_id("T1585") is True
    assert validate_sutra_id("X0367") is True
    assert validate_sutra_id("JB234") is True
    assert validate_sutra_id("T1588a") is True
    assert validate_sutra_id("ZS0010") is True

    # Invalid IDs
    assert validate_sutra_id("") is False
    assert validate_sutra_id("1585") is False
    assert validate_sutra_id("T") is False
    assert validate_sutra_id("None") is False
    assert validate_sutra_id("@#$$") is False


def test_parse_id_range_sequential():
    result = parse_id_range("T1500-T1505")
    expected = ["T1500", "T1501", "T1502", "T1503", "T1504", "T1505"]
    assert result == expected

    # Double-letter canon range
    jb_res = parse_id_range("JB010-JB013")
    assert jb_res == ["JB010", "JB011", "JB012", "JB013"]


def test_parse_id_range_edge_cases():
    # Different canons: returns both endpoints
    diff_res = parse_id_range("T1500-X1505")
    assert diff_res == ["T1500", "X1505"]

    # Inverted range: returns endpoints
    inv_res = parse_id_range("T1505-T1500")
    assert inv_res == ["T1505", "T1500"]

    # Non-range single input
    single_res = parse_id_range("T1585")
    assert single_res == ["T1585"]


def test_parse_id_list():
    raw_input = """
    # Comments should be ignored
    T1585
    T1500-T1502

    # Duplicates should be filtered
    T1585
    JB234
    
    # URL or file format
    https://example.com/download/text/X0367.txt.zip
    """
    parsed = parse_id_list(raw_input)
    assert parsed == ["T1585", "T1500", "T1501", "T1502", "JB234", "X0367"]


def test_parse_id_list_comma_and_semicolon():
    raw_input = "T1585, T1586; T1587"
    assert parse_id_list(raw_input) == ["T1585", "T1586", "T1587"]


def test_parse_id_file(temp_dir):
    file_path = os.path.join(temp_dir, "ids.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# Sutra List\nT1585\nT1501-T1503\nJB234\n")

    result = parse_id_file(file_path)
    assert result == ["T1585", "T1501", "T1502", "T1503", "JB234"]
