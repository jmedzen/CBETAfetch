"""
Unit tests for run.py entry point and CLI commands.
"""

import sys
import subprocess
import os


def test_cli_help():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = [sys.executable, "run.py", "--help"]
    res = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True)
    assert res.returncode == 0
    assert "CBETAfetch 2.0" in res.stdout
    assert "--port" in res.stdout
    assert "--self-test" in res.stdout


def test_cli_self_test():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = [sys.executable, "run.py", "--self-test"]
    res = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Running CBETAfetch 2.0 Diagnostics" in res.stdout
    assert "13/13 passed" in res.stdout
