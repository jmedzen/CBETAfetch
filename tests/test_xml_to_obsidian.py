"""
Unit tests for core.xml_to_obsidian module (CBETA TEI P5 XML to Obsidian Markdown).
"""

import os
import threading
import pytest

from core.xml_to_obsidian import (
    clean_cjk_spacing,
    CBETAXmlToObsidianConverter,
    convert_xml_file_to_obsidian_md,
    convert_xml_directory_to_obsidian
)

SAMPLE_XML_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:cb="http://www.cbeta.org/ns/1.0" xml:id="T08n0251">
<teiHeader>
    <fileDesc>
        <titleStmt>
            <title level="m">般若波羅蜜多心經</title>
            <author>唐 玄奘譯</author>
        </titleStmt>
        <publicationStmt>
            <idno>
                <idno type="canon">T</idno>
                <idno type="vol">08</idno>
                <idno type="no">0251</idno>
            </idno>
        </publicationStmt>
        <sourceDesc>
            <extent>1卷</extent>
        </sourceDesc>
    </fileDesc>
    <encodingDesc>
        <charDecl>
            <char xml:id="CB00001">
                <mapping type="unicode">U+4E00</mapping>
            </char>
        </charDecl>
    </encodingDesc>
</teiHeader>
<text>
<body>
    <div type="jing">
        <juan fun="open"><jhead>般若波羅蜜多心經</jhead></juan>
        <byline>唐三藏法師玄奘奉詔譯</byline>
        <p>觀自在菩薩行深般若波羅蜜多時<note type="orig">校勘備註內容</note>，照見五蘊皆空，度一切苦厄。</p>
        <lg>
            <l>色不異空，空不異色。</l>
            <l>色即是空，空即是色。</l>
        </lg>
        <juan fun="close"><jhead>般若波羅蜜多心經</jhead></juan>
    </div>
</body>
</text>
</TEI>"""


def test_clean_cjk_spacing():
    raw = "觀自在 菩薩 \n 行深 般若"
    cleaned = clean_cjk_spacing(raw)
    assert cleaned == "觀自在菩薩行深般若"


def test_convert_xml_file_to_obsidian_md(temp_dir):
    xml_path = os.path.join(temp_dir, "T08n0251.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_XML_CONTENT)

    out_dir = os.path.join(temp_dir, "obsidian_complete")
    ok, out_path = convert_xml_file_to_obsidian_md(xml_path, output_dir=out_dir)

    assert ok is True
    assert os.path.exists(out_path)
    assert "T0251《般若波羅蜜多心經》.md" in os.path.basename(out_path)

    with open(out_path, "r", encoding="utf-8") as f:
        md = f.read()

    # 1. YAML Frontmatter check
    assert "title: \"般若波羅蜜多心經\"" in md
    assert "cbeta_id: \"T08n0251\"" in md
    assert "author: \"唐 玄奘譯\"" in md
    assert "- CBETA" in md

    # 2. Callout check
    assert "> [!info] 經文典籍資訊" in md
    assert "玄奘" in md

    # 3. Headings check
    assert "## 【般若波羅蜜多心經】" in md
    assert "【般若波羅蜜多心經 終】" in md

    # 4. Byline & Gathas check
    assert "> *唐三藏法師玄奘奉詔譯*" in md
    assert "> 色不異空，空不異色。" in md

    # 5. Footnote check
    assert "[^1]: 校勘備註內容" in md


def test_convert_xml_directory_to_obsidian(temp_dir):
    xml_dir = os.path.join(temp_dir, "xml_repo")
    os.makedirs(xml_dir)
    out_dir = os.path.join(temp_dir, "complete")

    f1 = os.path.join(xml_dir, "sutra1.xml")
    f2 = os.path.join(xml_dir, "sutra2.xml")
    with open(f1, "w", encoding="utf-8") as fp:
        fp.write(SAMPLE_XML_CONTENT)
    with open(f2, "w", encoding="utf-8") as fp:
        fp.write(SAMPLE_XML_CONTENT.replace("0251", "0252").replace("心經", "他經"))

    count = convert_xml_directory_to_obsidian(xml_dir, output_dir=out_dir)
    assert count == 2
    assert os.path.exists(os.path.join(out_dir, "T0251《般若波羅蜜多心經》.md"))
    assert os.path.exists(os.path.join(out_dir, "T0252《般若波羅蜜多他經》.md"))


def test_convert_xml_directory_cancellation_and_missing(temp_dir):
    # 1. Missing directory
    assert convert_xml_directory_to_obsidian(os.path.join(temp_dir, "no_dir")) == 0

    # 2. Empty directory
    empty_d = os.path.join(temp_dir, "empty")
    os.makedirs(empty_d)
    assert convert_xml_directory_to_obsidian(empty_d) == 0

    # 3. Cancelled during execution
    xml_dir = os.path.join(temp_dir, "cancel_xml")
    os.makedirs(xml_dir)
    with open(os.path.join(xml_dir, "s.xml"), "w", encoding="utf-8") as fp:
        fp.write(SAMPLE_XML_CONTENT)

    stop = threading.Event()
    stop.set()
    count = convert_xml_directory_to_obsidian(xml_dir, stop_event=stop)
    assert count == 0


def test_convert_xml_detailed_features(temp_dir):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:cb="http://www.cbeta.org/ns/1.0" xml:id="T08n0235">
<teiHeader>
    <fileDesc>
        <titleStmt>
            <title>金剛般若波羅蜜經</title>
            <author>姚秦 鳩摩羅什譯</author>
        </titleStmt>
    </fileDesc>
    <encodingDesc>
        <charDecl>
            <char xml:id="CB00002">
                <mapping type="PUA">U+E000</mapping>
            </char>
            <char xml:id="CB00003">
                <charName>特殊字</charName>
            </char>
            <char xml:id="CB00004">
            </char>
        </charDecl>
    </encodingDesc>
</teiHeader>
<text>
<body>
    <head>金剛般若波羅蜜經序</head>
    <mulu>序文</mulu>
    <p>
        <pb n="0748c" ed="T"/>
        <lb n="0748c01"/>
        測試段落<g ref="#CB00002"/><g ref="#CB00003"/><g ref="#CB00004"/><space quantity="2"/>結尾。
    </p>
    <juan><b>卷全</b></juan>
</body>
</text>
</TEI>"""

    xml_path = os.path.join(temp_dir, "T08n0235.xml")
    with open(xml_path, "w", encoding="utf-8") as fp:
        fp.write(xml_content)

    converter = CBETAXmlToObsidianConverter(xml_path)
    md = converter.convert(include_line_anchors=True, include_page_marks=True)

    assert "金剛般若波羅蜜經序" in md
    assert "序文" in md
    assert "cbeta-pb" in md  # Page mark
    assert "^0748c01" in md  # Line anchor
    assert "特殊字" in md    # Gaiji charName
    assert "CB00004" in md   # Gaiji fallback

    # Error handling on invalid xml path
    ok, err = convert_xml_file_to_obsidian_md(os.path.join(temp_dir, "nonexistent.xml"))
    assert ok is False

