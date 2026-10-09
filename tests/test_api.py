"""
Integration tests for FastAPI REST API & SSE routes.
"""

import os
import pytest
from starlette.testclient import TestClient


def test_index_route(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "CBETA" in response.text


def test_get_status(client: TestClient):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ready", "busy")


def test_get_config(client: TestClient):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "base_dir" in data
    assert "default_download_dir" in data
    assert "default_base_url" in data


def test_self_test_endpoint(client: TestClient):
    response = client.get("/api/system/self-test")
    assert response.status_code == 200
    report = response.json()
    assert "total_tests" in report
    assert "passed" in report
    assert report["passed"] >= 10


from unittest.mock import patch, MagicMock
from core.downloader import BatchSummary, DownloadResult


def test_post_download_valid(client: TestClient, temp_dir):
    payload = {
        "id_list": "T1585\nT1500-T1502",
        "dest_dir": temp_dir,
        "formats": ["txt"]
    }
    with patch("core.downloader.SutraDownloader.download_from_ids", return_value=BatchSummary(total=4, succeeded=4)):
        response = client.post("/api/download", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "job_id" in data


def test_post_download_invalid(client: TestClient):
    payload = {
        "id_list": "",
        "dest_dir": "./downloads"
    }
    response = client.post("/api/download", json=payload)
    assert response.status_code == 400


def test_post_process(client: TestClient, temp_dir):
    payload = {
        "project_dir": temp_dir,
        "remove_zip": False
    }
    response = client.post("/api/process", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_post_convert_md(client: TestClient, temp_dir):
    payload = {
        "project_dir": temp_dir,
        "auto_heading": True
    }
    response = client.post("/api/convert_md", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_post_format_headings(client: TestClient, temp_dir):
    payload = {
        "target_dir": temp_dir
    }
    response = client.post("/api/format_headings", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_post_complete_process(client: TestClient, temp_dir):
    payload = {
        "dest_dir": temp_dir,
        "pack_url": "https://example.com/mock.zip"
    }
    with patch("core.downloader.SutraDownloader.download_file", return_value=DownloadResult(url="https://example.com/mock.zip", filename="mock.zip", success=True)):
        response = client.post("/api/complete_process", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "started"


def test_cancel_job_endpoint(client: TestClient, temp_dir):
    # Start a download job
    payload = {
        "id_list": "T1585",
        "dest_dir": temp_dir,
        "formats": ["txt"]
    }
    with patch("core.downloader.SutraDownloader.download_from_ids", return_value=BatchSummary()):
        res = client.post("/api/download", json=payload)
        job_id = res.json()["job_id"]

        # Cancel it
        cancel_res = client.post(f"/api/jobs/{job_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"


def test_legacy_routes_compat(client: TestClient, temp_dir):
    # Verify legacy routes without /api/ prefix
    with patch("core.downloader.SutraDownloader.download_from_ids", return_value=BatchSummary()):
        p1 = client.post("/download", json={"id_list": "T1585", "dest_dir": temp_dir})
        assert p1.status_code == 200

    p2 = client.post("/process", json={"project_dir": temp_dir})
    assert p2.status_code == 200

    p3 = client.post("/convert_md", json={"project_dir": temp_dir})
    assert p3.status_code == 200


def test_get_presets_endpoint(client: TestClient):
    response = client.get("/api/presets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert any(p["id"] == "weishi" for p in data)


def test_create_and_delete_preset_api(client: TestClient):
    # 1. Create a custom preset
    new_preset = {
        "id": "test_preset",
        "title": "測試自訂典籍組合",
        "category": "測試宗",
        "badge": "自訂",
        "description": "測試用途",
        "default_ids": "T1585\nT1586",
        "is_custom": True
    }
    res = client.post("/api/presets", json=new_preset)
    assert res.status_code == 200
    assert res.json()["status"] == "saved"

    # 2. Verify it is listed
    list_res = client.get("/api/presets")
    assert any(p["id"] == "test_preset" for p in list_res.json())

    # 3. Delete the preset
    del_res = client.delete("/api/presets/test_preset")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 4. Verify deletion
    list_res2 = client.get("/api/presets")
    assert not any(p["id"] == "test_preset" for p in list_res2.json())


def test_reset_presets_api(client: TestClient):
    res = client.post("/api/presets/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "reset"
    assert len(res.json()["presets"]) >= 6


def test_complete_files_endpoints(client: TestClient, temp_dir):
    complete_dir = os.path.join(temp_dir, "complete")
    os.makedirs(complete_dir, exist_ok=True)
    sample_file = os.path.join(complete_dir, "T1585《成唯識論》.md")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("# 成唯識論\n## 卷第一\n經文內容...")

    # 1. List files
    res = client.get(f"/api/complete/files?output_dir={complete_dir}")
    assert res.status_code == 200
    files = res.json()
    assert len(files) == 1
    assert files[0]["filename"] == "T1585《成唯識論》.md"
    assert files[0]["type"] == "markdown"

    # 2. Get file content
    content_res = client.get(f"/api/complete/file?filename=T1585《成唯識論》.md&output_dir={complete_dir}")
    assert content_res.status_code == 200
    file_data = content_res.json()
    assert file_data["filename"] == "T1585《成唯識論》.md"
    assert "經文內容..." in file_data["content"]
    assert file_data["line_count"] == 3

    # 3. File not found
    notFound_res = client.get(f"/api/complete/file?filename=nonexistent.md&output_dir={complete_dir}")
    assert notFound_res.status_code == 404

    # 4. Multi-format binary file (PDF)
    pdf_file = os.path.join(complete_dir, "T1585.pdf")
    with open(pdf_file, "wb") as fp:
        fp.write(b"%PDF-1.4 mock")

    pdf_content = client.get(f"/api/complete/file?filename=T1585.pdf&output_dir={complete_dir}")
    assert pdf_content.status_code == 200
    pdata = pdf_content.json()
    assert pdata["is_binary"] is True
    assert pdata["type"] == "pdf"
    assert pdata["content"] is None

    # 5. Direct file download
    dl_res = client.get(f"/api/complete/download?filename=T1585.pdf&output_dir={complete_dir}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"


def test_pipeline_run_endpoint(client: TestClient, temp_dir):
    # 1. Text format pipeline
    payload = {
        "id_list": "T1585\nT1586",
        "dest_dir": temp_dir,
        "output_dir": os.path.join(temp_dir, "complete"),
        "formats": ["txt"]
    }
    with patch("core.downloader.SutraDownloader.download_from_ids", return_value=BatchSummary(total=2, succeeded=2)):
        response = client.post("/api/pipeline/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "job_id" in data

    # 2. Non-text ebook format pipeline (skips text combine)
    payload_ebook = {
        "id_list": "T1585",
        "dest_dir": temp_dir,
        "output_dir": os.path.join(temp_dir, "complete"),
        "formats": ["pdf", "epub"]
    }
    with patch("core.downloader.SutraDownloader.download_from_ids", return_value=BatchSummary(total=2, succeeded=2)):
        with patch("server.routes.organize_downloaded_artifacts", return_value=["test.pdf"]):
            response_eb = client.post("/api/pipeline/run", json=payload_ebook)
            assert response_eb.status_code == 200
            assert response_eb.json()["status"] == "started"



def test_xml_sync_endpoint(client: TestClient, temp_dir):
    payload = {
        "repo_url": "https://github.com/cbeta-org/xml-p5",
        "dest_dir": os.path.join(temp_dir, "xml-p5"),
        "shallow": True
    }
    with patch("core.xml_repo.clone_or_update_xml_repo", return_value=MagicMock(success=True, commit_hash="abc1234")):
        res = client.post("/api/xml_repo/sync", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "started"


def test_xml_status_endpoint(client: TestClient, temp_dir):
    res = client.get(f"/api/xml_repo/status?dest_dir={temp_dir}")
    assert res.status_code == 200
    data = res.json()
    assert "exists" in data
    assert "is_git" in data


def test_complete_process_xml_edition(client: TestClient, temp_dir):
    payload = {
        "edition": "xml",
        "dest_dir": os.path.join(temp_dir, "xml-p5"),
        "xml_repo_url": "https://github.com/cbeta-org/xml-p5",
        "shallow": True
    }
    with patch("core.xml_repo.clone_or_update_xml_repo", return_value=MagicMock(success=True, commit_hash="abc1234")):
        res = client.post("/api/complete_process", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "started"
        assert res.json()["edition"] == "xml"


def test_remote_updates_endpoint(client: TestClient):
    mock_updates = {
        "zip_pack": {"success": True, "last_modified": "2026-08-04 10:40:47", "size_mb": 335.9},
        "git_repo": {"success": True, "last_modified": "2026-09-05 18:53:36", "commit_hash": "dbdea41"}
    }
    with patch("server.routes.get_all_remote_updates", return_value=mock_updates):
        res = client.get("/api/remote/updates")
        assert res.status_code == 200
        data = res.json()
        assert "zip_pack" in data
        assert "git_repo" in data
        assert data["zip_pack"]["last_modified"] == "2026-08-04 10:40:47"
        assert data["git_repo"]["commit_hash"] == "dbdea41"


def test_api_404_and_400_edge_cases(client: TestClient, temp_dir):
    # 1. Job details 404
    assert client.get("/api/jobs/nonexistent_id").status_code == 404

    # 2. Cancel nonexistent job 404
    assert client.post("/api/jobs/nonexistent_id/cancel").status_code == 404

    # 3. Process with nonexistent directory 400
    p_bad = client.post("/api/process", json={"project_dir": os.path.join(temp_dir, "nonexistent")})
    assert p_bad.status_code == 400

    # 4. Convert MD with nonexistent directory 400
    c_bad = client.post("/api/convert_md", json={"project_dir": os.path.join(temp_dir, "nonexistent")})
    assert c_bad.status_code == 400

    # 5. Format headings with missing target 400
    h_bad = client.post("/api/format_headings", json={})
    assert h_bad.status_code == 400

    # 6. Format headings with nonexistent target 400
    h_bad2 = client.post("/api/format_headings", json={"target_dir": os.path.join(temp_dir, "nonexistent")})
    assert h_bad2.status_code == 400

    # 7. Delete nonexistent preset 404
    assert client.delete("/api/presets/nonexistent_preset").status_code == 404

    # 8. Pipeline run with empty IDs 400
    pipe_bad = client.post("/api/pipeline/run", json={"id_list": ""})
    assert pipe_bad.status_code == 400


def test_api_xml_to_obsidian_endpoint(client: TestClient, temp_dir):
    payload = {
        "xml_dir": temp_dir,
        "output_dir": os.path.join(temp_dir, "complete"),
        "include_page_marks": False,
        "include_line_anchors": False
    }
    with patch("server.routes.convert_xml_directory_to_obsidian", return_value=10):
        res = client.post("/api/xml_repo/convert_obsidian", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "started"
        assert "job_id" in res.json()





