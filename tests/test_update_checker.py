"""
Unit tests for core.update_checker module.
"""

import os
from datetime import datetime, timezone
import pytest
from unittest.mock import patch, MagicMock

from core.update_checker import (
    format_iso_datetime,
    get_zip_remote_metadata,
    get_git_remote_metadata,
    get_all_remote_updates
)


def test_format_iso_datetime():
    dt = datetime(2026, 8, 4, 10, 40, 47)
    assert format_iso_datetime(dt) == "2026-08-04 10:40:47"


def test_get_zip_remote_metadata_mock():
    mock_resp = MagicMock()
    mock_resp.getheader.side_effect = lambda k: {
        "Last-Modified": "Tue, 04 Aug 2026 10:40:47 GMT",
        "Content-Length": "352216250",
        "ETag": '"14fe64ba-6583649a10c6b"'
    }.get(k)
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = get_zip_remote_metadata("https://example.com/test.zip")
        assert res["success"] is True
        assert res["last_modified"] == "2026-08-04 10:40:47"
        assert res["size_mb"] == 335.9
        assert res["etag"] == "14fe64ba-6583649a10c6b"


def test_get_git_remote_metadata_mock_github():
    mock_api_data = [{
        "sha": "dbdea41071e1e260ad84b72faefd4587333cf76d",
        "commit": {
            "committer": {
                "name": "heavenchou",
                "date": "2026-09-05T18:53:36Z"
            },
            "message": "CBETA 2026.R2 release"
        }
    }]
    import json
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_api_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = get_git_remote_metadata("https://github.com/cbeta-org/xml-p5")
        assert res["success"] is True
        assert res["commit_hash"] == "dbdea41"
        assert res["commit_message"] == "CBETA 2026.R2 release"
        assert res["author"] == "heavenchou"
        assert res["last_modified"] == "2026-09-05 18:53:36"


def test_get_all_remote_updates_mock():
    with patch("core.update_checker.get_zip_remote_metadata", return_value={"success": True, "size_mb": 335.9}):
        with patch("core.update_checker.get_git_remote_metadata", return_value={"success": True, "commit_hash": "dbdea41"}):
            res = get_all_remote_updates()
            assert res["zip_pack"]["size_mb"] == 335.9
            assert res["git_repo"]["commit_hash"] == "dbdea41"


def test_update_checker_error_and_fallback(temp_dir):
    # 1. Zip URL failure
    with patch("urllib.request.urlopen", side_effect=Exception("Connection Refused")):
        zip_res = get_zip_remote_metadata("https://example.com/bad.zip")
        assert zip_res["success"] is False
        assert "Connection Refused" in zip_res["error"]

    # 2. Git remote failure fallback to local repo
    local_repo = os.path.join(temp_dir, "local_git")
    os.makedirs(os.path.join(local_repo, ".git"))

    mock_git_log = MagicMock(
        returncode=0,
        stdout="2026-09-01T12:00:00+00:00\n1234abc\nLocal commit msg\nLocalAuthor\n"
    )
    with patch("urllib.request.urlopen", side_effect=Exception("GitHub API Error")):
        with patch("subprocess.run", return_value=mock_git_log):
            git_res = get_git_remote_metadata("https://github.com/cbeta-org/xml-p5", local_dir=local_repo)
            assert git_res["success"] is True
            assert git_res["source"] == "local_git"
            assert git_res["commit_hash"] == "1234abc"

    # 3. Total failure when no local repo either
    with patch("urllib.request.urlopen", side_effect=Exception("API Error")):
        res_fail = get_git_remote_metadata("https://unknown.org/repo.git", local_dir=os.path.join(temp_dir, "no_repo"))
        assert res_fail["success"] is False

