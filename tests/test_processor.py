"""
Unit tests for core.processor module.
"""

import os
import zipfile
import pytest

from core.processor import (
    sanitize_filename,
    extract_sutra_metadata,
    sort_volume_files,
    process_folder,
    extract_all_zips,
    process_project,
    process_cbeta_text_pack
)


def test_sanitize_filename():
    assert sanitize_filename('test:name/with?invalid*chars"<>|') == "testnamewithinvalidchars"
    assert sanitize_filename(" 成唯識論 ") == "成唯識論"


def test_extract_sutra_metadata(temp_dir):
    file_path = os.path.join(temp_dir, "T1585_001.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# CBETA Electronic Tripitaka\n")
        f.write("# No. 1585 成唯識論\n")
        f.write("# 護法等菩薩造 三藏法師玄奘奉詔譯\n")
        f.write("成唯識論卷第一\n")

    sutra_id, sutra_name = extract_sutra_metadata(file_path)
    assert sutra_id == "T1585"
    assert sutra_name == "成唯識論"


def test_sort_volume_files():
    input_files = [
        "T1585_002.txt",
        "T1585-toc.txt",
        "._T1585_001.txt",
        "T1585_001.txt",
        "T1585_010.txt"
    ]
    sorted_files = sort_volume_files(input_files)
    # Ignored hidden ._*, ordered volumes, TOC at the end
    assert sorted_files == ["T1585_001.txt", "T1585_002.txt", "T1585_010.txt", "T1585-toc.txt"]


def test_process_folder(temp_dir):
    sutra_dir = os.path.join(temp_dir, "T1585")
    os.makedirs(sutra_dir)
    out_dir = os.path.join(temp_dir, "complete")
    os.makedirs(out_dir)

    vol1 = os.path.join(sutra_dir, "T1585_001.txt")
    with open(vol1, "w", encoding="utf-8") as f:
        f.write("# Header Comment\n# No. 1585 成唯識論\n成唯識論卷第一\nVolume 1 body\n")

    vol2 = os.path.join(sutra_dir, "T1585_002.txt")
    with open(vol2, "w", encoding="utf-8") as f:
        f.write("# Comment in Vol 2 should be omitted\n成唯識論卷第二\nVolume 2 body\n")

    toc = os.path.join(sutra_dir, "T1585-toc.txt")
    with open(toc, "w", encoding="utf-8") as f:
        f.write("# TOC Comment\nTOC Body\n")

    out_file = process_folder(temp_dir, "T1585", out_dir)
    assert out_file is not None
    assert os.path.basename(out_file) == "T1585《成唯識論》.txt"
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Vol 1 comment retained
    assert "# Header Comment" in content
    # Vol 2 comment stripped
    assert "# Comment in Vol 2 should be omitted" not in content
    # Order: Vol 1 -> Vol 2 -> TOC
    v1_idx = content.find("Volume 1 body")
    v2_idx = content.find("Volume 2 body")
    toc_idx = content.find("TOC Body")
    assert v1_idx < v2_idx < toc_idx


def test_extract_all_zips(temp_dir):
    zip_path = os.path.join(temp_dir, "test_archive.txt.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("test_archive_001.txt", "Hello World")

    count = extract_all_zips(temp_dir, remove_zip=True)
    assert count == 1
    assert not os.path.exists(zip_path)  # Zip removed
    extracted_txt = os.path.join(temp_dir, "test_archive", "test_archive_001.txt")
    assert os.path.exists(extracted_txt)


def test_process_project_end_to_end(temp_dir):
    # Setup project dir with a zip
    proj_dir = os.path.join(temp_dir, "downloads")
    os.makedirs(proj_dir)
    out_dir = os.path.join(temp_dir, "complete")

    zip_path = os.path.join(proj_dir, "T0001.zip")
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("T0001_001.txt", "# Header\n# No. 0001 長阿含經\n長阿含經卷第一\n")
        z.writestr("T0001_002.txt", "# Header2\n長阿含經卷第二\n")

    created = process_project(proj_dir, output_dir=out_dir, remove_zip=False)
    assert len(created) == 1
    assert os.path.basename(created[0]) == "T0001《長阿含經》.txt"
    assert os.path.exists(created[0])


def test_process_cbeta_text_pack(temp_dir):
    # Create fake cbeta-text.zip
    pack_zip = os.path.join(temp_dir, "cbeta-text.zip")
    with zipfile.ZipFile(pack_zip, "w") as z:
        z.writestr("cbeta-text/T/T0001/T0001_001.txt", "# Comment\n# No. 0001 長阿含經\n長阿含經卷第一\n")

    dest_dir = os.path.join(temp_dir, "full_dest")
    out_dir = os.path.join(temp_dir, "full_complete")

    created = process_cbeta_text_pack(
        zip_path=pack_zip,
        dest_dir=dest_dir,
        output_dir=out_dir,
        remove_zip=False,
        convert_md=True,
        auto_heading=True
    )
    assert len(created) == 1
    # Check Markdown output created
    md_file = os.path.join(out_dir, "T0001《長阿含經》.md")
    assert os.path.exists(md_file)
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()
    # Check comment replaced with //
    assert "// Comment" in md_text


def test_processor_edge_cases(temp_dir):
    # 1. Metadata fallback on empty file
    empty_f = os.path.join(temp_dir, "T9999_001.txt")
    with open(empty_f, "w", encoding="utf-8") as fp:
        fp.write("")
    sid, sname = extract_sutra_metadata(empty_f)
    assert sid == "T9999"
    assert sname == ""

    # 2. Process folder empty
    empty_d = os.path.join(temp_dir, "empty_folder")
    os.makedirs(empty_d)
    out = process_folder(temp_dir, "empty_folder", os.path.join(temp_dir, "out"))
    assert out is None

    # 3. Process folder with remove_folder=True
    rm_folder = os.path.join(temp_dir, "rm_dir")
    os.makedirs(rm_folder)
    with open(os.path.join(rm_folder, "T8888_001.txt"), "w", encoding="utf-8") as fp:
        fp.write("Line 1\nLine 2 SutraTitle\nContent")
    res_out = process_folder(temp_dir, "rm_dir", os.path.join(temp_dir, "out2"), remove_folder=True)
    assert res_out is not None
    assert not os.path.exists(rm_folder)

    # 4. Extract corrupted zip
    bad_zip = os.path.join(temp_dir, "bad.txt.zip")
    with open(bad_zip, "wb") as fp:
        fp.write(b"not a valid zip binary content")
    count = extract_all_zips(temp_dir)
    assert count == 0

    # 5. Process project with nonexistent folder
    res = process_project(os.path.join(temp_dir, "no_proj"))
    assert res == []

    # 6. Process cbeta text pack with nonexistent file
    res_pack = process_cbeta_text_pack(os.path.join(temp_dir, "no.zip"), temp_dir)
    assert res_pack == []

    # 7. Process cbeta text pack with convert_md=False and remove_zip=True
    pack_zip = os.path.join(temp_dir, "cbeta_txt_pack.zip")
    with zipfile.ZipFile(pack_zip, "w") as z:
        z.writestr("cbeta-text/X/X0001/X0001_001.txt", "Line 1\nLine 2 Title\nContent\n")

    res2 = process_cbeta_text_pack(
        zip_path=pack_zip,
        dest_dir=temp_dir,
        output_dir=os.path.join(temp_dir, "out_txt_only"),
        remove_zip=True,
        convert_md=False
    )
    assert len(res2) == 1
    assert not os.path.exists(pack_zip)  # Zip removed
    txt_out = os.path.join(temp_dir, "out_txt_only", "X0001《Title》.txt")
    assert os.path.exists(txt_out)


def test_organize_downloaded_artifacts(temp_dir):
    from core.processor import organize_downloaded_artifacts

    dl_dir = os.path.join(temp_dir, "downloads")
    out_dir = os.path.join(temp_dir, "complete")
    os.makedirs(dl_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # 1. Create a PDF and an EPUB file
    pdf_file = os.path.join(dl_dir, "T1585.pdf")
    with open(pdf_file, "wb") as fp:
        fp.write(b"%PDF-1.4 mock")

    epub_file = os.path.join(dl_dir, "T1585.epub")
    with open(epub_file, "wb") as fp:
        fp.write(b"mock epub")

    # 2. Create a zip containing DOCX
    docx_zip = os.path.join(dl_dir, "T0099.zip")
    with zipfile.ZipFile(docx_zip, "w") as z:
        z.writestr("T0099_001.docx", b"mock docx content")

    organized = organize_downloaded_artifacts(dl_dir, out_dir)
    assert len(organized) == 3
    assert os.path.exists(os.path.join(out_dir, "T1585.pdf"))
    assert os.path.exists(os.path.join(out_dir, "T1585.epub"))
    assert os.path.exists(os.path.join(out_dir, "T0099_001.docx"))


