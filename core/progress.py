"""
CBETAfetch 2.0 - Standardized Visual Progress Bar Engine
Provides terminal Unicode progress bars, transfer rate formatting, and ETA calculation.
"""

from typing import Optional


def render_progress_bar(
    percent: float,
    width: int = 20,
    filled_char: str = "█",
    empty_char: str = "░"
) -> str:
    """
    Renders an ASCII/Unicode progress bar string.
    Example: [██████████░░░░░░░░░░]  50.0%
    """
    clamped = max(0.0, min(100.0, percent))
    filled_len = int(width * (clamped / 100.0))
    empty_len = width - filled_len
    bar = f"{filled_char * filled_len}{empty_char * empty_len}"
    return f"[{bar}] {clamped:5.1f}%"


def format_bytes(num_bytes: int) -> str:
    """Format bytes count into human-readable B, KB, MB, GB string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_speed(bytes_per_sec: float) -> str:
    """Format download speed into KB/s or MB/s."""
    if bytes_per_sec <= 0:
        return "0 KB/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"


def format_eta(seconds: float) -> str:
    """Format remaining estimated time."""
    if seconds <= 0 or seconds > 86400:
        return "0s"
    sec = int(seconds)
    if sec < 60:
        return f"{sec}s"
    elif sec < 3600:
        mins = sec // 60
        s = sec % 60
        return f"{mins}m {s}s"
    else:
        hrs = sec // 3600
        mins = (sec % 3600) // 60
        return f"{hrs}h {mins}m"


def format_progress_line(
    percent: float,
    current_bytes: Optional[int] = None,
    total_bytes: Optional[int] = None,
    speed_bps: float = 0.0,
    eta_sec: float = 0.0,
    current_count: Optional[int] = None,
    total_count: Optional[int] = None,
    label: str = ""
) -> str:
    """
    Format a complete standardized [PROGRESS] log line.
    Prefix '[PROGRESS]' allows client terminal to update in-place smoothly.
    """
    bar_str = render_progress_bar(percent, width=20)
    parts = ["[PROGRESS]", bar_str]

    if current_bytes is not None and total_bytes is not None and total_bytes > 0:
        parts.append(f"({format_bytes(current_bytes)} / {format_bytes(total_bytes)})")

    if current_count is not None and total_count is not None and total_count > 0:
        parts.append(f"({current_count}/{total_count})")

    if speed_bps > 0:
        parts.append(f"· {format_speed(speed_bps)}")

    if eta_sec > 0:
        parts.append(f"· ETA: {format_eta(eta_sec)}")

    if label:
        parts.append(f"· {label}")

    return " ".join(parts)
