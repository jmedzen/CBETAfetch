"""
Targeted tests to maximize test coverage across edge-case branches.
"""

import os
import shutil
import tempfile
import time
import pytest
from unittest.mock import patch, MagicMock

from core.converter import convert_txt_file_to_md, resolve_output_directory
from core.downloader import SutraDownloader
from core.processor import extract_sutra_metadata, process_folder
from core.job_engine import JobEngine, JobStatus
from core.xml_repo import clone_or_update_xml_repo
from core.update_checker import get_zip_remote_metadata
from starlette.testclient import TestClient


def test_converter_same_path_and_sibling(temp_dir):
    # 1. txt_path == output_path (should not delete output)
    f = os.path.join(temp_dir, "same_path.txt")
    with open(f, "w", encoding="utf-8") as fp:
        fp.write("content")
    convert_txt_file_to_md(f, output_path=f, remove_source=True)
    assert os.path.exists(f)

    # 2. Sibling complete directory resolution
    sub_dir = os.path.join(temp_dir, "sub_project")
    sibling_comp = os.path.join(temp_dir, "complete")
    os.makedirs(sub_dir)
    os.makedirs(sibling_comp)
    with open(os.path.join(sibling_comp, "test.txt"), "w") as fp:
        fp.write("dummy")

    resolved = resolve_output_directory(sub_dir)
    assert resolved == sibling_comp


def test_processor_metadata_and_folder_removal_error(temp_dir):
    # 1. Line with brackets [cf. No. 1586]
    f = os.path.join(temp_dir, "T1585_001.txt")
    with open(f, "w", encoding="utf-8") as fp:
        fp.write("# Header\n# No. 1585 [cf. No. 1586] 成唯識論\n")
    _, name = extract_sutra_metadata(f)
    assert name == "成唯識論"

    # 2. Folder removal error handled gracefully
    test_fold = os.path.join(temp_dir, "rm_fold")
    os.makedirs(test_fold)
    with open(os.path.join(test_fold, "T1111_001.txt"), "w") as fp:
        fp.write("# H\n# Title\nText")

    with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
        logs = []
        out = process_folder(temp_dir, "rm_fold", os.path.join(temp_dir, "out"), remove_folder=True, logger=logs.append)
        assert out is not None
        assert any("Could not remove folder" in l for l in logs)


def test_job_engine_additional_branches():
    engine = JobEngine()

    # 1. Add empty log (should be ignored)
    engine.add_log("job1", "")
    assert len(engine.global_logs) == 0

    # 2. Broken listener handles exception gracefully
    def broken_listener(msg):
        raise RuntimeError("listener failure")

    engine.subscribe_logs(broken_listener)
    engine.add_log("job1", "test msg")
    assert len(engine.global_logs) == 1
    engine.unsubscribe_logs(broken_listener)

    # 3. get_active_job when job running
    j = engine.create_job("run_type")
    j.status = JobStatus.RUNNING
    active = engine.get_active_job()
    assert active is not None
    assert active.job_id == j.job_id


def test_xml_repo_unexpected_exception(temp_dir):
    # Exception during Popen
    with patch("subprocess.Popen", side_effect=Exception("Process spawn failure")):
        res = clone_or_update_xml_repo(target_dir=os.path.join(temp_dir, "fail_git"))
        assert res.success is False
        assert res.action == "error"
        assert "Process spawn failure" in res.message


def test_api_download_format_urls_and_example(client: TestClient, temp_dir):
    # Tests format_urls and example_url branching in /api/download
    payload = {
        "id_list": "T1585",
        "dest_dir": temp_dir,
        "example_url": "https://cbdata.dila.edu.tw/stable/download/text/T1585.txt.zip",
        "formats": ["txt", "html", "pdf", "epub", "mobi"],
        "html_url": "https://custom.org/download/html/T1585.html.zip",
        "pdf_url": "https://custom.org/download/pdf/T/T1585.pdf",
        "epub_url": "https://custom.org/download/epub/T/T1585.epub",
        "mobi_url": "https://custom.org/download/mobi/T/T1585.mobi"
    }
    with patch("core.downloader.SutraDownloader.download_from_ids"):
        res = client.post("/api/download", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "started"
