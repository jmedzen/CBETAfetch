"""
Unit tests for core.xml_repo module (CBETA TEI P5 XML Git Repository Manager).
"""

import os
import subprocess
import threading
import pytest
from unittest.mock import patch, MagicMock

from core.xml_repo import (
    check_git_installed,
    get_xml_repo_status,
    clone_or_update_xml_repo,
    GitSyncResult,
    DEFAULT_XML_P5_REPO
)


def test_check_git_installed():
    ok, ver = check_git_installed()
    assert ok is True
    assert "git" in ver.lower()


def test_get_xml_repo_status_nonexistent(temp_dir):
    nonexistent = os.path.join(temp_dir, "does_not_exist")
    st = get_xml_repo_status(nonexistent)
    assert st["exists"] is False
    assert st["is_git"] is False


def test_get_xml_repo_status_non_git_dir(temp_dir):
    d = os.path.join(temp_dir, "empty_dir")
    os.makedirs(d)
    st = get_xml_repo_status(d)
    assert st["exists"] is True
    assert st["is_git"] is False


def test_get_xml_repo_status_real_repo(temp_dir):
    # Initialize a dummy git repo
    repo_dir = os.path.join(temp_dir, "test_repo")
    os.makedirs(repo_dir)
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # Add dummy XML file
    xml_file = os.path.join(repo_dir, "T08n0251.xml")
    with open(xml_file, "w", encoding="utf-8") as f:
        f.write("<TEI><text><body><p>心經</p></body></text></TEI>")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)

    st = get_xml_repo_status(repo_dir)
    assert st["exists"] is True
    assert st["is_git"] is True
    assert st["commit"] is not None
    assert st["xml_file_count"] == 1


def test_clone_or_update_xml_repo_mock_clone(temp_dir):
    target = os.path.join(temp_dir, "mock_xml")

    mock_proc = MagicMock()
    stream = iter(["Cloning into 'mock_xml'...\n", "Receiving objects: 100%\n", ""])
    mock_proc.stdout.readline.side_effect = lambda: next(stream, "")
    mock_proc.poll.return_value = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("core.xml_repo.get_xml_repo_status", return_value={"commit": "abc1234", "xml_file_count": 100}):
            logs = []
            res = clone_or_update_xml_repo(
                repo_url=DEFAULT_XML_P5_REPO,
                target_dir=target,
                shallow=True,
                progress_callback=logs.append
            )
            assert res.success is True
            assert res.action == "clone"
            assert any("Cloning" in l for l in logs)
            assert res.commit_hash == "abc1234"


def test_clone_or_update_xml_repo_mock_pull(temp_dir):
    target = os.path.join(temp_dir, "existing_git")
    os.makedirs(os.path.join(target, ".git"))

    mock_proc = MagicMock()
    stream = iter(["Already up to date.\n", ""])
    mock_proc.stdout.readline.side_effect = lambda: next(stream, "")
    mock_proc.poll.return_value = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch("core.xml_repo.get_xml_repo_status", return_value={"commit": "def5678", "xml_file_count": 100}):
            logs = []
            res = clone_or_update_xml_repo(
                repo_url=DEFAULT_XML_P5_REPO,
                target_dir=target,
                progress_callback=logs.append
            )
            assert res.success is True
            assert res.action == "pull"
            assert any("pull" in l for l in logs)
            assert res.commit_hash == "def5678"


def test_clone_or_update_xml_repo_cancellation(temp_dir):
    target = os.path.join(temp_dir, "cancel_git")
    stop_event = threading.Event()
    stop_event.set()

    mock_proc = MagicMock()
    mock_proc.stdout.readline.return_value = "line\n"
    mock_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=mock_proc):
        res = clone_or_update_xml_repo(
            target_dir=target,
            stop_event=stop_event
        )
        assert res.success is False
        assert res.action == "cancelled"


def test_clone_or_update_xml_repo_git_not_found(temp_dir):
    with patch("core.xml_repo.check_git_installed", return_value=(False, "No git binary")):
        res = clone_or_update_xml_repo(target_dir=os.path.join(temp_dir, "test"))
        assert res.success is False
        assert res.action == "error"
        assert "not installed" in res.message


def test_clone_or_update_xml_repo_returncode_error(temp_dir):
    target = os.path.join(temp_dir, "error_git")
    mock_proc = MagicMock()
    mock_proc.stdout.readline.side_effect = ["fatal: repository not found\n", ""]
    mock_proc.poll.return_value = 128

    with patch("subprocess.Popen", return_value=mock_proc):
        res = clone_or_update_xml_repo(target_dir=target)
        assert res.success is False
        assert res.action == "error"
        assert "128" in res.message


def test_clone_or_update_xml_repo_branch_option(temp_dir):
    target = os.path.join(temp_dir, "branch_git")
    mock_proc = MagicMock()
    mock_proc.stdout.readline.return_value = ""
    mock_proc.poll.return_value = 0

    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        with patch("core.xml_repo.get_xml_repo_status", return_value={"commit": "xyz999"}):
            res = clone_or_update_xml_repo(target_dir=target, branch="custom-branch")
            assert res.success is True
            # Check -b custom-branch in call arguments
            cmd_args = mock_popen.call_args[0][0]
            assert "-b" in cmd_args
            assert "custom-branch" in cmd_args

