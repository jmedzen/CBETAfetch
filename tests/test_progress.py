"""
Unit tests for core.progress module (Progress Bar, Formatting, and ETA).
"""

from core.progress import (
    render_progress_bar,
    format_bytes,
    format_speed,
    format_eta,
    format_progress_line
)


def test_render_progress_bar_bounds_and_width():
    # 0%
    b0 = render_progress_bar(0.0, width=10)
    assert "░░░░░░░░░░" in b0
    assert "0.0%" in b0

    # 50%
    b50 = render_progress_bar(50.0, width=10)
    assert "█████░░░░░" in b50
    assert "50.0%" in b50

    # 100%
    b100 = render_progress_bar(100.0, width=10)
    assert "██████████" in b100
    assert "100.0%" in b100

    # Clamping negative and > 100
    b_neg = render_progress_bar(-10.0, width=10)
    assert "0.0%" in b_neg
    b_over = render_progress_bar(150.0, width=10)
    assert "100.0%" in b_over


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024 * 2) == "2.0 KB"
    assert format_bytes(1024 * 1024 * 350) == "350.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.00 GB"


def test_format_speed():
    assert format_speed(0) == "0 KB/s"
    assert format_speed(1024 * 500) == "500.0 KB/s"
    assert format_speed(1024 * 1024 * 12.5) == "12.5 MB/s"


def test_format_eta():
    assert format_eta(0) == "0s"
    assert format_eta(-5) == "0s"
    assert format_eta(45) == "45s"
    assert format_eta(125) == "2m 5s"
    assert format_eta(3665) == "1h 1m"


def test_format_progress_line():
    line = format_progress_line(
        percent=50.0,
        current_bytes=1024 * 1024 * 100,
        total_bytes=1024 * 1024 * 200,
        speed_bps=1024 * 1024 * 10,
        eta_sec=10,
        label="下載中"
    )
    assert "[PROGRESS]" in line
    assert "50.0%" in line
    assert "100.0 MB / 200.0 MB" in line
    assert "10.0 MB/s" in line
    assert "ETA: 10s" in line
    assert "下載中" in line
