"""
Unit tests for core.downloader module.
"""

import os
import io
import pytest
from unittest.mock import patch, MagicMock

from core.downloader import (
    build_download_url,
    SutraDownloader,
    DownloadResult,
    BatchSummary,
    DEFAULT_BASE_URL
)


def test_build_download_url_standard():
    assert build_download_url("T1585", "txt") == f"{DEFAULT_BASE_URL}text/T1585.txt.zip"
    assert build_download_url("T1585", "html") == f"{DEFAULT_BASE_URL}html/T1585.html.zip"
    assert build_download_url("T1585", "epub") == f"{DEFAULT_BASE_URL}epub/T/T1585.epub"
    assert build_download_url("T1585", "mobi") == f"{DEFAULT_BASE_URL}mobi/T/T1585.mobi"
    assert build_download_url("T1585", "pdf") == f"{DEFAULT_BASE_URL}pdf/T/T1585.pdf"
    assert build_download_url("T0099", "docx") == f"{DEFAULT_BASE_URL}docx/T/T0099.zip"
    assert build_download_url("T0099", "odt") == f"{DEFAULT_BASE_URL}odt/T/T0099.zip"
    assert build_download_url("T0001", "docusky") == f"{DEFAULT_BASE_URL}docusky/T0001.docusky.xml"
    assert build_download_url("T0001", "docuxml") == f"{DEFAULT_BASE_URL}docusky/T0001.docusky.xml"
    assert build_download_url("T0001", "text-with-notes") == f"{DEFAULT_BASE_URL}text-with-notes/T0001.txt.zip"
    assert build_download_url("T0001", "txt_notes") == f"{DEFAULT_BASE_URL}text-with-notes/T0001.txt.zip"


def test_build_download_url_two_letter_canons():
    # Canon for JB234 is JB
    assert build_download_url("JB234", "epub") == f"{DEFAULT_BASE_URL}epub/JB/JB234.epub"
    assert build_download_url("JB234", "pdf") == f"{DEFAULT_BASE_URL}pdf/JB/JB234.pdf"
    assert build_download_url("ZS0010", "mobi") == f"{DEFAULT_BASE_URL}mobi/ZS/ZS0010.mobi"


def test_build_download_url_custom_base():
    custom_base = "https://mirror.cbeta.org/download/"
    url = build_download_url("T1585", "txt", base_url=custom_base)
    assert url == "https://mirror.cbeta.org/download/text/T1585.txt.zip"

    # Format specific overrides
    format_urls = {"pdf": "https://pdf-mirror.cbeta.org/download/"}
    url_pdf = build_download_url("T1585", "pdf", format_urls=format_urls)
    assert url_pdf == "https://pdf-mirror.cbeta.org/download/pdf/T/T1585.pdf"


def test_build_download_url_invalid_format():
    with pytest.raises(ValueError):
        build_download_url("T1585", "xlsx")


def test_download_file_mock_success(temp_dir):
    fake_data = b"PK\x03\x04fake_zip_content_here"
    mock_response = MagicMock()
    mock_response.read.side_effect = [fake_data, b""]
    mock_response.getheader.return_value = str(len(fake_data))
    mock_response.__enter__.return_value = mock_response

    downloader = SutraDownloader(download_dir=temp_dir)
    with patch("urllib.request.urlopen", return_value=mock_response):
        logs = []
        res = downloader.download_file("https://example.com/test.zip", progress_callback=logs.append)
        assert res.success is True
        assert res.filename == "test.zip"
        assert os.path.exists(res.filepath)
        with open(res.filepath, "rb") as f:
            assert f.read() == fake_data


def test_download_file_retry_logic(temp_dir):
    fake_data = b"payload"

    def make_mock_resp():
        m = MagicMock()
        m.getheader.return_value = str(len(fake_data))
        stream = iter([fake_data, b""])
        m.read.side_effect = lambda *a, **k: next(stream, b"")
        m.__enter__.return_value = m
        return m

    downloader = SutraDownloader(download_dir=temp_dir)
    # Fail on first attempt, succeed on second attempt
    with patch("urllib.request.urlopen", side_effect=[Exception("Network Error"), make_mock_resp()]):
        res = downloader.download_file("https://example.com/retry.zip", retries=1)
        assert res.success is True
        assert os.path.exists(res.filepath)


def test_download_file_cancellation(temp_dir):
    downloader = SutraDownloader(download_dir=temp_dir)
    downloader.cancel()

    res = downloader.download_file("https://example.com/cancel.zip")
    assert res.success is False
    assert res.error == "Cancelled"


def test_download_batch_ids_mock(temp_dir):
    fake_data = b"zip content"

    def mock_urlopen(req, *args, **kwargs):
        m = MagicMock()
        m.getheader.return_value = str(len(fake_data))
        stream = iter([fake_data, b""])
        m.read.side_effect = lambda *a, **k: next(stream, b"")
        m.__enter__.return_value = m
        return m

    downloader = SutraDownloader(download_dir=temp_dir, max_workers=2)
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        summary = downloader.download_from_ids(
            ids=["T1585", "X0367"],
            formats=["txt"]
        )
        assert summary.total == 2
        assert summary.succeeded == 2
        assert summary.failed == 0
        assert len(summary.results) == 2


def test_build_download_url_normalization_branches():
    # Base URL without trailing slash
    url = build_download_url("T1585", "txt", base_url="https://mirror.org/download")
    assert url == "https://mirror.org/download/text/T1585.txt.zip"

    # Base URL with subpath
    url2 = build_download_url("T1585", "txt", base_url="https://mirror.org/download/extra/")
    assert url2 == "https://mirror.org/download/text/T1585.txt.zip"


def test_download_file_stop_mid_stream(temp_dir):
    downloader = SutraDownloader(download_dir=temp_dir)
    mock_resp = MagicMock()
    # First chunk returned, then cancel triggered, then second chunk
    def chunk_generator(*args, **kwargs):
        downloader.cancel()
        return b"chunk"

    mock_resp.read.side_effect = chunk_generator
    mock_resp.getheader.return_value = "100"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = downloader.download_file("https://example.com/mid_cancel.zip")
        assert res.success is False
        assert res.error == "Cancelled"
        assert not os.path.exists(os.path.join(temp_dir, "mid_cancel.zip"))


def test_download_file_progress_dots(temp_dir):
    downloader = SutraDownloader(download_dir=temp_dir)
    big_chunk = b"X" * (6 * 1024 * 1024)  # 6MB
    mock_resp = MagicMock()
    mock_resp.read.side_effect = [big_chunk, b""]
    mock_resp.getheader.return_value = str(len(big_chunk))
    mock_resp.__enter__.return_value = mock_resp

    dots = []
    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = downloader.download_file("https://example.com/big.zip", progress_callback=dots.append, log_progress_dots=True)
        assert res.success is True
        assert any("[PROGRESS]" in d for d in dots)


def test_download_from_ids_empty_and_unknown_format(temp_dir):
    downloader = SutraDownloader(download_dir=temp_dir)
    completed = []
    summary = downloader.download_from_ids(
        ids=[],
        completion_callback=lambda: completed.append(True)
    )
    assert summary.total == 0
    assert len(completed) == 1

    # Unknown format skipped
    logs = []
    summary2 = downloader.download_from_ids(
        ids=["T1585"],
        formats=["unknown_format"],
        progress_callback=logs.append
    )
    assert summary2.total == 0


def test_download_from_file_cases(temp_dir):
    downloader = SutraDownloader(download_dir=temp_dir)
    
    # 1. Non-existent file
    logs = []
    s1 = downloader.download_from_file(os.path.join(temp_dir, "nonexistent.txt"), progress_callback=logs.append)
    assert s1.total == 0
    assert any("not found" in l for l in logs)

    # 2. Valid file with mock
    id_file = os.path.join(temp_dir, "ids.txt")
    with open(id_file, "w") as fp:
        fp.write("T1585\n# Comment\n")

    fake_data = b"content"
    def mock_urlopen(req, *args, **kwargs):
        m = MagicMock()
        m.getheader.return_value = str(len(fake_data))
        stream = iter([fake_data, b""])
        m.read.side_effect = lambda *a, **k: next(stream, b"")
        m.__enter__.return_value = m
        return m

    done = []
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        s2 = downloader.download_from_file(
            id_file,
            formats=["txt"],
            completion_callback=lambda: done.append(True)
        )
        assert s2.total == 1
        assert s2.succeeded == 1
        assert len(done) == 1

