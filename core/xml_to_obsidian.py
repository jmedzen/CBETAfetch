"""
CBETAfetch 2.0 - CBETA TEI P5 XML to Obsidian Markdown Engine
Converts CBETA TEI P5 XML files into Obsidian-flavored Markdown with:
1. YAML Frontmatter (title, cbeta_id, canon, vol, no, author, extent)
2. Obsidian Callout Info Box (> [!info] 經文典籍資訊)
3. Structured Chapters & Juan headings (## 【卷名】, ## 目次)
4. Buddhist Verses & Gathas (> 偈頌排版)
5. Textual Apparatus & Variant Readings ([^1]: 異文校勘記)
6. Automatic gaiji / Unicode replacement
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple
import threading

from core.progress import format_progress_line

NS = {
    'tei': 'http://www.tei-c.org/ns/1.0',
    'cb': 'http://www.cbeta.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

SKIP_DIV_TYPES = {
    'apparatus', 'cbeta-notes', 'taisho-notes', 'add-notes', 'rest-notes', 'other-notes'
}


def clean_cjk_spacing(text: str) -> str:
    """Remove unnecessary spaces and linebreaks inside CJK prose."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    cjk_pattern = r'(?<=[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef])\s+(?=[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef])'
    text = re.sub(cjk_pattern, '', text)
    return text.strip()


def safe_text(elem: Optional[ET.Element], default: str = "") -> str:
    """Safely extract and strip text from an XML element, returning default if None or empty."""
    if elem is not None and elem.text is not None:
        val = elem.text.strip()
        return val if val else default
    return default


class CBETAXmlToObsidianConverter:
    """
    Parses a single CBETA TEI P5 XML file and produces Obsidian Markdown.
    """

    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.gaiji_map: Dict[str, str] = {}
        self.footnotes_list: List[Tuple[str, str]] = []
        self.footnote_counter = 0
        self.rendered_headings = set()

        self.title = ""
        self.author = ""
        self.canon = "T"
        self.vol = ""
        self.no = ""
        self.sutra_id = ""
        self.extent = ""

        self._parse_header()
        self._parse_gaiji()

    def _parse_header(self):
        r = self.root

        title_m = r.find('.//tei:titleStmt/tei:title[@level="m"]', NS)
        if title_m is not None and title_m.text:
            self.title = title_m.text.strip()
        else:
            title_main = r.find('.//tei:titleStmt/tei:title', NS)
            self.title = safe_text(title_main, default=self.xml_path.stem)

        author_elem = r.find('.//tei:titleStmt/tei:author', NS)
        self.author = safe_text(author_elem, default="未知")

        idno_canon = r.find('.//tei:publicationStmt/tei:idno/tei:idno[@type="canon"]', NS)
        idno_vol = r.find('.//tei:publicationStmt/tei:idno/tei:idno[@type="vol"]', NS)
        idno_no = r.find('.//tei:publicationStmt/tei:idno/tei:idno[@type="no"]', NS)

        self.canon = safe_text(idno_canon, default="T")
        self.vol = safe_text(idno_vol, default="")
        self.no = safe_text(idno_no, default="")
        self.sutra_id = f"{self.canon}{self.vol.zfill(2)}n{self.no.zfill(4)}" if self.vol and self.no else self.xml_path.stem

        extent_elem = r.find('.//tei:extent', NS)
        self.extent = safe_text(extent_elem, default="")

    def _parse_gaiji(self):
        for char in self.root.findall('.//tei:charDecl/tei:char', NS):
            cid = char.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
            if not cid:
                continue

            uni_elem = char.find('.//tei:mapping[@type="unicode"]', NS)
            if uni_elem is not None and uni_elem.text:
                val = uni_elem.text.strip()
                if val.startswith('U+'):
                    try:
                        self.gaiji_map[cid] = chr(int(val[2:], 16))
                        continue
                    except ValueError:
                        pass

            pua_elem = char.find('.//tei:mapping[@type="PUA"]', NS)
            if pua_elem is not None and pua_elem.text:
                val = pua_elem.text.strip()
                if val.startswith('U+'):
                    try:
                        self.gaiji_map[cid] = chr(int(val[2:], 16))
                        continue
                    except ValueError:
                        pass

            cname = char.find('.//tei:charName', NS)
            if cname is not None and cname.text:
                self.gaiji_map[cid] = f"〔{cname.text.strip()}〕"
            else:
                self.gaiji_map[cid] = f"〔{cid}〕"

    def convert(self, include_line_anchors: bool = False, include_page_marks: bool = False) -> str:
        lines = []

        # 1. Obsidian YAML Frontmatter
        lines.append("---")
        lines.append(f"title: \"{self.title}\"")
        lines.append(f"cbeta_id: \"{self.sutra_id}\"")
        lines.append(f"canon: \"{self.canon}\"")
        lines.append(f"vol: \"{self.vol}\"")
        lines.append(f"no: \"{self.no}\"")
        lines.append(f"author: \"{self.author}\"")
        lines.append(f"extent: \"{self.extent}\"")
        lines.append("tags:")
        lines.append("  - CBETA")
        lines.append("  - 佛典")
        lines.append("---\n")

        # 2. Main Title & Callout
        lines.append(f"# {self.title}\n")
        lines.append("> [!info] 經文典籍資訊")
        lines.append(f"> - **經名**：{self.title}")
        lines.append(f"> - **典籍編號**：{self.sutra_id} ({self.canon}藏 第 {self.vol} 冊 No. {self.no})")
        lines.append(f"> - **譯者/作者**：{self.author}")
        if self.extent:
            lines.append(f"> - **卷數**：{self.extent}")
        lines.append(f"> - **來源典藏**：[CBETA Online 電子佛典](https://cbetaonline.dila.edu.tw/zh/{self.sutra_id})\n")

        # 3. Body Conversion
        body = self.root.find('.//tei:body', NS)
        if body is not None:
            body_md = self._process_node(body, level=2, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks)
            lines.append(body_md)

        # 4. Footnotes Section
        if self.footnotes_list:
            lines.append("\n---\n")
            lines.append("## 校注與註釋\n")
            seen_fn = set()
            for fn_id, fn_text in self.footnotes_list:
                if fn_text not in seen_fn:
                    seen_fn.add(fn_text)
                    lines.append(f"[^{fn_id}]: {fn_text}")

        full_md = "\n".join(lines)
        full_md = re.sub(r'\n{3,}', '\n\n', full_md)
        return full_md

    def close(self):
        """Release ElementTree DOM memory immediately."""
        if hasattr(self, 'root') and self.root is not None:
            try:
                self.root.clear()
            except Exception:
                pass
        self.root = None
        self.tree = None
        self.gaiji_map.clear()
        self.footnotes_list.clear()
        self.rendered_headings.clear()

    def _process_node(self, node, level=2, include_line_anchors=False, include_page_marks=False) -> str:
        if level > 60:
            return ""
        chunks = []

        if node.text:
            chunks.append(node.text)

        for child in node:
            tag = child.tag.split('}')[-1]

            if (tag == 'div' and child.attrib.get('type') in SKIP_DIV_TYPES) or tag == 'docNumber':
                continue

            if tag == 'head':
                head_text = clean_cjk_spacing(self._get_node_text(child))
                if head_text and head_text not in self.rendered_headings:
                    self.rendered_headings.add(head_text)
                    h_prefix = '#' * min(level, 6)
                    chunks.append(f"\n\n{h_prefix} {head_text}\n\n")

            elif tag == 'mulu':
                mulu_text = clean_cjk_spacing(self._get_node_text(child))
                if mulu_text and mulu_text not in self.rendered_headings:
                    self.rendered_headings.add(mulu_text)
                    h_prefix = '#' * min(level, 6)
                    chunks.append(f"\n\n{h_prefix} {mulu_text}\n\n")

            elif tag == 'byline':
                by_text = clean_cjk_spacing(self._get_node_text(child))
                if by_text:
                    chunks.append(f"\n\n> *{by_text}*\n\n")

            elif tag == 'juan':
                jfun = child.attrib.get('fun', '')
                jtext = clean_cjk_spacing(self._get_node_text(child))
                if jfun == 'open':
                    chunks.append(f"\n\n## 【{jtext}】\n\n")
                elif jfun == 'close':
                    chunks.append(f"\n\n---\n> **【{jtext} 終】**\n\n")
                else:
                    if jtext:
                        chunks.append(f" **{jtext}** ")

            elif tag == 'p':
                p_raw = self._process_node(child, level=level+1, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks)
                p_clean = clean_cjk_spacing(p_raw)
                if p_clean:
                    chunks.append(f"\n\n{p_clean}\n\n")

            elif tag == 'lg':
                lg_lines = []
                for l in child.findall('.//tei:l', NS):
                    l_raw = self._process_node(l, level=level+1, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks)
                    l_clean = clean_cjk_spacing(l_raw)
                    if l_clean:
                        lg_lines.append(f"> {l_clean}  ")
                if lg_lines:
                    chunks.append("\n\n" + "\n".join(lg_lines) + "\n\n")

            elif tag == 'pb':
                if include_page_marks:
                    n = child.attrib.get('n', '')
                    ed = child.attrib.get('ed', '')
                    if n:
                        pb_id = f"p{n}"
                        chunks.append(f'<span class="cbeta-pb" id="{pb_id}">`〔{ed}{n}〕`</span>')

            elif tag == 'lb':
                n = child.attrib.get('n', '')
                if n and include_line_anchors:
                    chunks.append(f'`^{n}`')

            elif tag == 'app':
                lem = child.find('./tei:lem', NS)
                if lem is not None:
                    lem_text = clean_cjk_spacing(self._process_node(lem, level=level, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks))
                    rdgs = child.findall('./tei:rdg', NS)
                    if rdgs:
                        self.footnote_counter += 1
                        fn_id = str(self.footnote_counter)
                        var_texts = []
                        for r in rdgs:
                            wit = r.attrib.get('wit', '')
                            r_txt = clean_cjk_spacing(self._get_node_text(r))
                            var_texts.append(f"{wit}: {r_txt}")
                        fn_desc = f"**{lem_text}** （異文：{'; '.join(var_texts)}）"
                        self.footnotes_list.append((fn_id, fn_desc))
                        chunks.append(f"{lem_text}[^{fn_id}]")
                    else:
                        chunks.append(lem_text)
                else:
                    chunks.append(self._process_node(child, level=level, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks))

            elif tag == 'g':
                ref = child.attrib.get('ref', '').replace('#', '')
                char_str = self.gaiji_map.get(ref, f"〔{ref}〕")
                chunks.append(char_str)

            elif tag == 'space':
                qty = int(child.attrib.get('quantity', '1'))
                chunks.append('　' * qty)

            elif tag == 'note':
                ntype = child.attrib.get('type', '')
                if ntype in ['orig', 'mod', 'cb']:
                    n_text = clean_cjk_spacing(self._get_node_text(child))
                    if n_text:
                        self.footnote_counter += 1
                        fn_id = str(self.footnote_counter)
                        self.footnotes_list.append((fn_id, n_text))
                        chunks.append(f"[^{fn_id}]")

            elif tag in ['div', 'text', 'body']:
                sub_text = self._process_node(child, level=level+1, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks)
                chunks.append(sub_text)

            else:
                sub_text = self._process_node(child, level=level, include_line_anchors=include_line_anchors, include_page_marks=include_page_marks)
                chunks.append(sub_text)

            if child.tail:
                chunks.append(child.tail)

        return "".join(chunks)

    def _get_node_text(self, elem) -> str:
        res = []
        if elem.text:
            res.append(elem.text)
        for child in elem:
            ctag = child.tag.split('}')[-1]
            if ctag == 'g':
                ref = child.attrib.get('ref', '').replace('#', '')
                res.append(self.gaiji_map.get(ref, f"〔{ref}〕"))
            else:
                res.append(self._get_node_text(child))
            if child.tail:
                res.append(child.tail)
        return "".join(res).strip()


def convert_xml_file_to_obsidian_md(
    xml_path: str,
    output_dir: str = "./complete",
    include_line_anchors: bool = False,
    include_page_marks: bool = False
) -> Tuple[bool, str]:
    """
    Convert a single CBETA TEI P5 XML file to an Obsidian Markdown file.
    Output filename format: {canon}{no.zfill(4)}《{title}》.md
    """
    converter = None
    try:
        converter = CBETAXmlToObsidianConverter(xml_path)
        md_content = converter.convert(
            include_line_anchors=include_line_anchors,
            include_page_marks=include_page_marks
        )

        canon_no = f"{converter.canon}{converter.no.zfill(4)}" if converter.no else converter.sutra_id
        safe_title = re.sub(r'[\\/*?:"<>|]', '', converter.title)
        out_name = f"{canon_no}《{safe_title}》.md"

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return True, out_path

    except Exception as e:
        return False, str(e)
    finally:
        if converter:
            converter.close()


def convert_xml_directory_to_obsidian(
    xml_dir: str = "./downloads-xml",
    output_dir: str = "./complete",
    include_line_anchors: bool = False,
    include_page_marks: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None
) -> int:
    """
    Recursively scan xml_dir for .xml files and convert each to Obsidian Markdown.
    
    Returns:
        Number of successfully converted files.
    """
    log = progress_callback or (lambda msg: None)
    abs_xml = os.path.abspath(xml_dir)
    abs_out = os.path.abspath(output_dir)

    if not os.path.isdir(abs_xml):
        log(f"XML 目錄不存在: {abs_xml}")
        return 0

    os.makedirs(abs_out, exist_ok=True)
    log(f"開始掃描 XML 目錄: {abs_xml} ➔ 匯出至: {abs_out}")

    xml_files: List[str] = []
    for root, _, files in os.walk(abs_xml):
        if "/.git" in root or root.endswith(".git"):
            continue
        for f in sorted(files):
            if f.endswith(".xml") and not f.startswith("."):
                xml_files.append(os.path.join(root, f))

    total = len(xml_files)
    log(f"共發現 {total} 份 CBETA TEI P5 XML 經文檔案，開始轉換為 Obsidian Markdown...")

    if total == 0:
        log("目錄中未發現任何 XML 經文檔案，請先執行 XML 全藏庫同步。")
        return 0

    success_count = 0
    for idx, xf in enumerate(xml_files):
        if stop_event and stop_event.is_set():
            log(f"收到中斷請求，已停止 XML 轉 Obsidian 作業 (已完成 {success_count}/{total})。")
            break

        ok, res = convert_xml_file_to_obsidian_md(
            xf,
            output_dir=abs_out,
            include_line_anchors=include_line_anchors,
            include_page_marks=include_page_marks
        )

        if ok:
            success_count += 1
            percent = (success_count / total) * 100.0
            if total <= 20 or success_count % max(1, total // 50) == 0 or success_count == total:
                log(format_progress_line(
                    percent=percent,
                    current_count=success_count,
                    total_count=total,
                    label=f"已轉換: {os.path.basename(res)}"
                ))
        else:
            log(f"轉換失敗 ({os.path.basename(xf)}): {res}")

    log(f"✨ XML 轉 Obsidian Markdown 作業完成！成功產出 {success_count} 份標準 Obsidian 經文筆記。")
    return success_count
