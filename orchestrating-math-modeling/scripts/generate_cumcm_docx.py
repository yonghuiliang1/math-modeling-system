#!/usr/bin/env python3
"""
CUMCM 论文生成包装脚本
基于 chinese-thesis-workbench 的 generate_thesis_docx.py，叠加 CUMCM 国赛特有格式。

用法:
    python generate_cumcm_docx.py <source.md> <target.docx> [--image-map <map.json>]

叠加的 CUMCM 格式:
    1. 国赛标准字号（标题16pt / 一级14pt / 二级12pt / 三级12pt / 正文12pt）
    2. 行距 1.3
    3. 一级标题居中，二/三级左对齐
    4. 三线表样式
    5. blockquote 过滤（编辑者注释不进正文）
    6. 页码从摘要页开始（页脚中部，阿拉伯数字）
    7. 图片自适应缩放（最大宽度 14.5cm）
    8. 附录/参考文献重新起页

注意：脚本不处理公式，MD 中的公式文本原样写入 docx。
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


# ============================================================
# 1. 加载原始模块
# ============================================================

def _find_original_script() -> Path:
    """定位 chinese-thesis-workbench 的 generate_thesis_docx.py：先项目内，再全局 skills"""
    candidates = [
        Path(__file__).resolve().parents[1]
        / "chinese-thesis-workbench" / "scripts" / "docx" / "generate_thesis_docx.py",
        Path.home() / ".trae-cn" / "skills" / "chinese-thesis-workbench"
        / "scripts" / "docx" / "generate_thesis_docx.py",
        Path.home() / ".trae" / "skills" / "chinese-thesis-workbench"
        / "scripts" / "docx" / "generate_thesis_docx.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("; ".join(str(c) for c in candidates))


try:
    ORIGINAL_SCRIPT = _find_original_script()
except FileNotFoundError as e:
    print(
        "错误: 未找到 chinese-thesis-workbench 的 generate_thesis_docx.py。\n"
        f"  已搜索路径: {e}\n"
        "  请检查 chinese-thesis-workbench 是否已安装，以及其安装位置是否正确。\n"
        "  该脚本依赖 chinese-thesis-workbench 提供 docx 生成基础能力。",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _load_original():
    try:
        spec = importlib.util.spec_from_file_location("generate_thesis_docx", ORIGINAL_SCRIPT)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load original module: {ORIGINAL_SCRIPT}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(
            f"错误: 加载 generate_thesis_docx 模块失败: {e}\n"
            f"  已搜索路径: {ORIGINAL_SCRIPT}\n"
            "  请检查 chinese-thesis-workbench 是否已安装，以及其安装位置是否正确。",
            file=sys.stderr,
        )
        raise SystemExit(1)


_orig = _load_original()


# ============================================================
# 2. CUMCM 页面设置
# ============================================================

def apply_cumcm_page_setup(section) -> None:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.header_distance = Cm(1.27)
    section.footer_distance = Cm(1.27)


# ============================================================
# 3. CUMCM 样式覆盖
# ============================================================

def cumcm_style_profile() -> dict[str, Any]:
    profile = _orig.default_style_profile()
    s = profile["styles"]

    s["title"] = _orig.centered_style("黑体", "Times New Roman", 16, bold=True)

    s["heading1"] = _orig.paragraph_style(
        "黑体", "Times New Roman", 14, bold=True, alignment="center",
        line_spacing=1.3, space_before=12, space_after=6,
    )
    s["heading2"] = _orig.paragraph_style(
        "黑体", "Times New Roman", 12, bold=False, alignment="left",
        line_spacing=1.3, space_before=8, space_after=4,
    )
    s["heading3"] = _orig.paragraph_style(
        "宋体", "Times New Roman", 12, bold=False, alignment="left",
        line_spacing=1.3, space_before=6, space_after=3,
    )

    s["abstract_heading_cn"] = _orig.centered_style(
        "黑体", "Times New Roman", 16, bold=True, page_break_before=False,
    )
    s["appendix_heading"] = _orig.centered_style(
        "黑体", "Times New Roman", 16, bold=True, page_break_before=True,
    )
    s["references_heading"] = _orig.centered_style(
        "黑体", "Times New Roman", 16, bold=True, page_break_before=True,
    )

    s["body_cn"] = _orig.paragraph_style(
        "宋体", "Times New Roman", 12, first_line_indent=24, line_spacing=1.3,
    )
    s["equation"] = _orig.centered_style(
        "Times New Roman", "Times New Roman", 12, line_spacing=1.3,
    )
    s["figure_caption"] = _orig.centered_style(
        "宋体", "Times New Roman", 10.5, line_spacing=1, line_spacing_rule="single",
    )
    s["table_caption"] = _orig.centered_style(
        "宋体", "Times New Roman", 10.5, line_spacing=1, line_spacing_rule="single",
    )
    s["table_text"] = _orig.centered_style("宋体", "Times New Roman", 10.5)
    s["references_body"] = _orig.paragraph_style(
        "宋体", "Times New Roman", 10.5, first_line_indent=-21, left_indent=21,
        line_spacing=1.3,
    )
    s["keywords_paragraph"] = _orig.paragraph_style(
        "宋体", "Times New Roman", 12, first_line_indent=0, line_spacing=1.3,
    )

    return profile


# ============================================================
# 4. 三线表
# ============================================================


def set_cell_content(cell, text: str) -> None:
    """清空单元格并写入内容"""
    cell.text = ""
    cell.paragraphs[0].add_run(text)


def _set_cell_border(cell, **kwargs):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.find(qn("w:tcBorders"))
    if tcBorders is None:
        tcBorders = OxmlElement("w:tcBorders")
        tcPr.append(tcBorders)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kwargs:
            border = tcBorders.find(qn(f"w:{edge}"))
            if border is None:
                border = OxmlElement(f"w:{edge}")
                tcBorders.append(border)
            for attr, val in kwargs[edge].items():
                border.set(qn(f"w:{attr}"), val)


def add_three_line_table(doc, lines: list[str], styles: dict[str, Any]) -> None:
    rows = []
    for row in lines:
        cells = [_orig.normalize_text(c.strip()) for c in row.strip().strip("|").split("|")]
        if all(re.fullmatch(r"[:\- ]+", c or "") for c in cells):
            continue
        rows.append(cells)
    if len(rows) < 2:
        return

    headers = rows[0]
    data_rows = rows[1:]
    table = doc.add_table(rows=1 + len(data_rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for idx, text in enumerate(headers):
        set_cell_content(table.rows[0].cells[idx], text)
    for r_idx, row in enumerate(data_rows, start=1):
        for c_idx, text in enumerate(row):
            if c_idx < len(table.rows[r_idx].cells):
                set_cell_content(table.rows[r_idx].cells[c_idx], text)

    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                _orig.apply_paragraph_style(p, styles["table_text"])

    thick = {"val": "single", "sz": "12", "color": "000000"}
    thin = {"val": "single", "sz": "6", "color": "000000"}

    for cell in table.rows[0].cells:
        _set_cell_border(cell, top=thick, bottom=thin, left={"val": "nil"}, right={"val": "nil"})
    for cell in table.rows[-1].cells:
        _set_cell_border(cell, bottom=thick, left={"val": "nil"}, right={"val": "nil"})
    for row in table.rows[1:-1]:
        for cell in row.cells:
            _set_cell_border(cell, left={"val": "nil"}, right={"val": "nil"},
                             top={"val": "nil"}, bottom={"val": "nil"})


# ============================================================
# 5. 页码
# ============================================================

def build_section_page_numbers(doc: Document, pages_config: dict[str, Any] | None = None) -> None:
    """配置并写入页脚页码。

    pages_config 支持以下配置项:
        - alignment: 页码对齐方式，默认 WD_ALIGN_PARAGRAPH.CENTER（页脚中部）
        - start_at_abstract: 是否从摘要页开始编号（默认 True，预留配置项）
    """
    config = pages_config or {}
    alignment = config.get("alignment", WD_ALIGN_PARAGRAPH.CENTER)
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p.alignment = alignment
        run = p.add_run()

        fld1 = OxmlElement("w:fldChar")
        fld1.set(qn("w:fldCharType"), "begin")
        run._element.append(fld1)

        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        run._element.append(instr)

        fld2 = OxmlElement("w:fldChar")
        fld2.set(qn("w:fldCharType"), "end")
        run._element.append(fld2)


# ============================================================
# 6. 图片自适应
# ============================================================

def add_auto_image(doc: Document, path: Path) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    max_width_cm = 14.5
    try:
        from PIL import Image
        img = Image.open(str(path))
        w, _h = img.size
        natural_cm = w / 96 * 2.54
        width_cm = min(natural_cm, max_width_cm)
    except Exception:
        width_cm = max_width_cm
    paragraph.add_run().add_picture(str(path), width=Cm(width_cm))


# ============================================================
# 7. CUMCM build_doc（辅助函数 + 主函数）
# ============================================================

def build_tables(doc: Document, md_content: str, image_map: dict[str, Path], styles: dict[str, Any], index: int) -> int:
    """处理从 index 开始的三线表块，返回下一个未处理的行索引。

    三线表块为连续以 | 开头的行；表题（表 X-Y）由主循环单独处理。
    """
    lines = md_content.splitlines()
    tlines = []
    while index < len(lines) and lines[index].strip().startswith("|"):
        tlines.append(lines[index].strip())
        index += 1
    add_three_line_table(doc, tlines, styles)
    return index


def build_images(doc: Document, md_content: str, image_map: dict[str, Path], styles: dict[str, Any], index: int, pending_mermaid: bool) -> tuple[int, bool]:
    """处理 index 处的图片占位符或图题行，返回 (下一个行索引, pending_mermaid)。

    图片占位符（SCREENSHOT_PLACEHOLDER_RE）直接插入图片或缺失占位；
    图题（图 X-Y）在 pending_mermaid 为真时先插入 mermaid 渲染图，再输出图题。
    """
    lines = md_content.splitlines()
    stripped = lines[index].strip()

    # 图片占位符
    img_m = _orig.SCREENSHOT_PLACEHOLDER_RE.match(stripped)
    if img_m:
        label = img_m.group(1).strip()
        ip = image_map.get(label)
        if ip and ip.exists():
            add_auto_image(doc, ip)
        else:
            _orig.add_missing_asset_placeholder(doc, label, styles)
        return index + 1, pending_mermaid

    # 图题
    if re.match(r"^图\s*\d+[-\.]\d+", stripped):
        caption = _orig.normalize_text(stripped)
        if pending_mermaid:
            ip = image_map.get(caption)
            if ip and ip.exists():
                add_auto_image(doc, ip)
            else:
                _orig.add_missing_asset_placeholder(doc, caption, styles)
            pending_mermaid = False
        p = doc.add_paragraph()
        p.add_run(caption)
        _orig.apply_paragraph_style(p, styles["figure_caption"])
        return index + 1, pending_mermaid

    return index, pending_mermaid


def _set_word_heading_style(p, doc: Document, style_name: str) -> None:
    """设置 Word 内置 Heading 样式，保证大纲/导航结构可用。

    直接格式（字体/字号/对齐）由 apply_paragraph_style 先行设置，
    此处仅补充 pStyle 引用，视觉样式不受影响。
    """
    try:
        p.style = doc.styles[style_name]
    except KeyError:
        pass


def build_cumcm_doc(
    source: Path,
    image_map: dict[str, Path],
    profile: dict[str, Any],
) -> Document:
    styles = profile["styles"]
    doc = Document()
    apply_cumcm_page_setup(doc.sections[0])

    try:
        md_content = source.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] 读取 Markdown 源文件失败: {source} — {e}", file=sys.stderr)
        raise
    lines = md_content.splitlines()
    current_section = ""
    in_code = False
    code_lang = ""
    pending_mermaid = False
    seen_content = False
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        # blockquote 过滤
        if stripped.startswith(">"):
            index += 1
            continue

        if in_code:
            if stripped.startswith("```"):
                in_code = False
                if code_lang == "mermaid":
                    pending_mermaid = True
                code_lang = ""
            elif code_lang != "mermaid":
                p = doc.add_paragraph()
                p.add_run(line.rstrip())
                _orig.apply_paragraph_style(p, styles["code"])
            index += 1
            continue

        if not stripped or stripped == "---":
            index += 1
            continue

        if stripped.startswith("```"):
            in_code = True
            code_lang = stripped[3:].strip().lower()
            index += 1
            continue

        # # 标题
        if stripped.startswith("# "):
            p = doc.add_paragraph()
            p.add_run(_orig.normalize_text(stripped[2:].strip()))
            _orig.apply_paragraph_style(p, styles["title"])
            seen_content = True
            index += 1
            continue

        # ## 章节标题
        if stripped.startswith("## "):
            text = _orig.normalize_text(stripped[3:].strip())
            normalized = text.replace(" ", "").lower()
            style_key = _orig.SPECIAL_CENTERED_HEADINGS.get(normalized, "heading1")
            p = doc.add_paragraph()
            p.add_run(text)
            if seen_content and style_key == "heading1":
                style = _orig.deep_merge(styles["heading1"], {"page_break_before": True})
            else:
                style = styles[style_key]
            _orig.apply_paragraph_style(p, style)
            _set_word_heading_style(p, doc, "Heading 1")
            current_section = text
            seen_content = True
            index += 1
            continue

        if stripped.startswith("### "):
            p = doc.add_paragraph()
            p.add_run(_orig.normalize_text(stripped[4:].strip()))
            _orig.apply_paragraph_style(p, styles["heading2"])
            _set_word_heading_style(p, doc, "Heading 2")
            seen_content = True
            index += 1
            continue

        if stripped.startswith("#### "):
            p = doc.add_paragraph()
            p.add_run(_orig.normalize_text(stripped[5:].strip()))
            _orig.apply_paragraph_style(p, styles["heading3"])
            _set_word_heading_style(p, doc, "Heading 3")
            seen_content = True
            index += 1
            continue

        # 关键词
        kw = re.match(r"^(关键词[:：]|Keywords[:：])\s*(.*)$", stripped)
        if kw:
            p = doc.add_paragraph()
            _orig.apply_keyword_runs(p, kw.group(1), kw.group(2), styles)
            seen_content = True
            index += 1
            continue

        # 图片占位符 / 图题（委托给 build_images 处理）
        if _orig.SCREENSHOT_PLACEHOLDER_RE.match(stripped) or re.match(r"^图\s*\d+[-\.]\d+", stripped):
            index, pending_mermaid = build_images(doc, md_content, image_map, styles, index, pending_mermaid)
            seen_content = True
            continue

        # 表题
        if re.match(r"^表\s*\d+[-\.]\d+", stripped):
            p = doc.add_paragraph()
            p.add_run(_orig.normalize_text(stripped))
            _orig.apply_paragraph_style(p, styles["table_caption"])
            seen_content = True
            index += 1
            continue

        # 三线表（委托给 build_tables 处理）
        if stripped.startswith("|"):
            index = build_tables(doc, md_content, image_map, styles, index)
            seen_content = True
            continue

        # 普通段落
        p = doc.add_paragraph()
        p.add_run(_orig.normalize_text(stripped))
        if current_section.replace(" ", "") == "参考文献" and re.match(r"^\[\d+\]", stripped):
            _orig.apply_paragraph_style(p, styles["references_body"])
        elif current_section.lower() == "abstract":
            _orig.apply_paragraph_style(p, styles["body_en"])
        else:
            _orig.apply_paragraph_style(p, styles["body_cn"])
        seen_content = True
        index += 1

    build_section_page_numbers(doc, {"alignment": WD_ALIGN_PARAGRAPH.CENTER})
    return doc


# ============================================================
# 10. CLI
# ============================================================

def check_prerequisites(project_dir: Path) -> None:
    """论文生成前置检查：验证S4/S5产物齐全，防止绕过写作流程直接生成论文。"""
    required_s4 = [
        "S4_步骤产物/步骤0_正文写作规范.md",
        "S4_步骤产物/步骤1_问题分析.md",
        "S4_步骤产物/步骤2_模型假设.md",
        "S4_步骤产物/步骤3_模型建立与求解.md",
        "S4_步骤产物/步骤4_定义与符号说明.md",
        "S4_步骤产物/步骤5_模型检验.md",
        "S4_步骤产物/步骤6_模型的评价及优化.md",
        "S4_步骤产物/步骤7_支撑材料生成.md",
        "S4_步骤产物/步骤8_参考文献.md",
        "S4_步骤产物/步骤9_附录.md",
        "S4_步骤产物/步骤10_全文校对.md",
        "S4_步骤产物/步骤11_摘要撰写.md",
        "S4_步骤产物/步骤12_论文整篇整合.md",
    ]
    required_s5 = [
        "S5_步骤产物/步骤1_数据一致性校验.md",
        "S5_步骤产物/步骤2_编号一致性校验.md",
        "S5_步骤产物/步骤3_合规与格式预检.md",
    ]

    missing = []
    for f in required_s4 + required_s5:
        if not (project_dir / f).exists():
            missing.append(f)

    if missing:
        print("❌ 论文生成前置检查未通过！")
        print(f"   缺失产物 {len(missing)} 个：")
        for m in missing:
            print(f"   - {m}")
        print("   请先完成S4论文写作和S5综合校验后再生成论文。")
        print("   此门禁为代码级强制，无法通过提示词绕过。")
        raise SystemExit(1)

    print("✅ 论文生成前置检查通过（S4 13个产物 + S5 3个产物齐全）")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="CUMCM 论文生成包装脚本")
    parser.add_argument("source", type=Path, help="输入 Markdown 文件")
    parser.add_argument("target", type=Path, help="输出 DOCX 文件")
    parser.add_argument("--image-map", type=Path, default=None, help="图片映射 JSON")
    parser.add_argument(
        "--project-dir", type=Path, default=None,
        help="项目根目录（含S4/S5产物目录）。不指定则从source路径推断",
    )
    args = parser.parse_args()

    project_dir = args.project_dir or args.source.resolve().parent
    check_prerequisites(project_dir)

    image_map = _orig.load_image_map(args.image_map)
    profile = cumcm_style_profile()
    doc = build_cumcm_doc(args.source, image_map, profile)

    args.target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(args.target))
    print(f"[OK] 论文已生成: {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
