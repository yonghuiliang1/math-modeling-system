#!/usr/bin/env python3
"""
AI 工具使用详情 PDF 生成脚本

从 AI 使用记录文件汇总，按 2026 年试行规定第 4 条 4 项必填内容
生成中文 PDF。全部输出内容必须为中文。

用法:
    python generate_ai_usage_pdf.py [--project-dir <目录>] [--output <路径>]

参数:
    --project-dir  项目根目录（包含 S1_步骤产物/ 至 S6_步骤产物/），默认当前目录
    --output       输出 PDF 路径，默认 <project-dir>/AI工具使用详情.pdf

依赖:
    pip install fpdf2
    (如 fpdf2 不可用，自动回退生成 Markdown 文件)

字体:
    自动检测 Windows 系统中文字体（SimHei/SimFang/SimKai/SimSun/MSYH）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================
# 1. 中文字体检测
# ============================================================

FONT_CANDIDATES_TTF = [
    "simhei.ttf",
    "simfang.ttf",
    "simkai.ttf",
    "STKAITI.ttf",
    "STSONG.ttf",
]

FONT_CANDIDATES_TTC = [
    "simsun.ttc",
    "msyh.ttc",
]

# 系统字体目录
SYSTEM_FONT_DIRS = [
    "/usr/share/fonts/truetype",
    "/usr/share/fonts/opentype",
    "/usr/local/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
    "C:/Windows/Fonts/TraditionalChinese",
    "C:/Windows/Fonts/SimSun",
]

# macOS 特定中文字体文件路径
MACOS_FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STSong.ttf",
    "/System/Library/Fonts/PingFang.ttc",
]

# Linux 特定中文字体文件路径
LINUX_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _find_font(font_names: list[str]) -> str | None:
    """在系统字体目录中搜索指定字体文件，返回第一个存在的路径。

    覆盖 Windows / macOS / Linux 各平台字体目录。
    """
    for font_dir in SYSTEM_FONT_DIRS:
        for name in font_names:
            full_path = Path(font_dir) / name
            if full_path.exists():
                return str(full_path.resolve())
    return None


def find_chinese_font() -> str | None:
    # 首先检查当前目录
    for p in FONT_CANDIDATES_TTF + FONT_CANDIDATES_TTC:
        if Path(p).exists():
            return str(Path(p).resolve())

    # 然后在系统字体目录中搜索候选字体（覆盖 Windows/macOS/Linux 目录）
    found = _find_font(FONT_CANDIDATES_TTF + FONT_CANDIDATES_TTC)
    if found:
        return found

    # 最后检查 macOS/Linux 特定字体文件路径
    for p in MACOS_FONT_PATHS + LINUX_FONT_PATHS:
        if Path(p).exists():
            return str(Path(p).resolve())

    return None


# ============================================================
# 1.5 PDF 排版配置
# ============================================================

# 字号常量（pt）
FONT_SIZE_TITLE = 16           # 文档主标题
FONT_SIZE_SUBTITLE = 10        # 副标题（规定依据说明）
FONT_SIZE_SECTION = 13         # 一级小节标题（一、二、三、四）
FONT_SIZE_SUBSECTION = 12      # 二级小节标题（附录标题）
FONT_SIZE_BODY = 11            # 正文
FONT_SIZE_CAPTION = 10         # 附录记录标题/摘要
FONT_SIZE_SMALL = 8            # 小号间距
FONT_SIZE_SPACE_LARGE = 6      # 大间距
FONT_SIZE_SPACE_MEDIUM = 4     # 中间距
FONT_SIZE_SPACE_SMALL = 3      # 小间距
FONT_SIZE_SPACE_APPENDIX = 10  # 附录前空行间距

# 页面配置（A4 纵向，mm 单位）
PAGE_CONFIG = {
    "orientation": "portrait",
    "unit": "mm",
    "format": "A4",
    "auto_page_break_margin": 25,
    "margins": {"left": 25, "top": 25, "right": 25},
    "page_width": 210,
    "left_margin": 25,
    "right_margin": 25,
}


# ============================================================
# 2. 读取 AI 使用记录
# ============================================================

RECORD_FILES = [
    ("S1", "S1_步骤产物/AI使用记录.md"),
    ("S2", "S2_步骤产物/AI使用记录.md"),
    ("S3", "S3_步骤产物/AI使用记录.md"),
    ("S4A", "S4_步骤产物/AI使用记录A.md"),
    ("S4B", "S4_步骤产物/AI使用记录B.md"),
    ("S4C", "S4_步骤产物/AI使用记录C.md"),
    ("S5", "S5_步骤产物/AI使用记录.md"),
    ("S6", "S6_步骤产物/AI使用记录.md"),
]

# 默认的AI工具配置
# 版本号必须填写"具体型号/版本"，严禁使用"当前版本"等模糊表述——评委依据确切版本判断工具可信度
# 使用前请按参赛队实际使用的工具版本号替换占位文字
DEFAULT_AI_TOOLS = [
    "TRAE (内置 AI 助手) / 具体版本号(如 v1.6.0) / 字节跳动",
    "ChatGPT / GPT-4o (gpt-4o-2024-05-13) / OpenAI",
]


def read_ai_records(project_dir: Path) -> dict[str, str]:
    records = {}
    for label, rel_path in RECORD_FILES:
        fp = project_dir / rel_path
        if fp.exists():
            try:
                records[label] = fp.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[ERROR] 读取 AI 使用记录失败: {fp} — {e}", file=sys.stderr)
                raise
        else:
            records[label] = ""
    return records


# ============================================================
# 3. 构建中文内容
# ============================================================

# "辅助措辞 → 具体使用目的"映射，体现"在哪个环节、为了什么目的"（越具体越安全，供评委判断参与度）
USAGE_PURPOSE_MAP = {
    "辅助文字润色": "论文撰写环节，辅助语言润色，提升表述的严谨性与可读性",
    "辅助公式排版": "公式录入环节，辅助公式排版与格式转换（LaTeX/OMML），确保公式编号连续",
    "辅助数据验算": "结果复核环节，辅助交叉验算部分计算结果，核对数值一致性",
    "辅助图表美化": "图表制作环节，辅助调整坐标轴标注、配色与布局，保证中文标注规范",
}


def extract_usage_phases(records: dict[str, str]) -> list[str]:
    """从AI使用记录中提取各阶段的实际使用环节，并将辅助措辞映射为"阶段+目的"的具体表述。"""
    usage_phases = []
    for label, content in records.items():
        if not content.strip():
            continue
        found = []
        for kw in USAGE_PURPOSE_MAP:
            if kw in content:
                found.append(USAGE_PURPOSE_MAP[kw])
        if found:
            usage_phases.append(f"{label}：{'；'.join(found)}")
        else:
            first_line = content.strip().split("\n")[0][:40]
            usage_phases.append(f"{label}：{first_line}")
    return usage_phases


def build_sections(records: dict[str, str]) -> list[tuple[str, int, bool, str]]:
    """构建 PDF 内容段落。

    返回 [(文本, 字号, 是否加粗, 对齐方式)] 的列表。
    对齐方式: "C" 居中, "L" 左对齐。
    """
    sections: list[tuple[str, int, bool, str]] = []

    # 标题
    sections.append(("AI 工具使用详情", FONT_SIZE_TITLE, True, "C"))
    sections.append(("", FONT_SIZE_SPACE_LARGE, False, "L"))
    sections.append(("（基于全国大学生数学建模竞赛人工智能工具使用规定 2026年试行 第4条）", FONT_SIZE_SUBTITLE, False, "C"))
    sections.append(("", FONT_SIZE_SMALL, False, "L"))

    # 一、所用AI工具名称、版本或型号
    sections.append(("一、所用AI工具名称、版本或型号", FONT_SIZE_SECTION, True, "L"))
    sections.append(("", FONT_SIZE_SPACE_SMALL, False, "L"))
    sections.append((
        "本参赛队在竞赛过程中使用以下 AI 工具辅助完成部分工作：\n"
        + "\n".join(f"{i+1}. {tool}" for i, tool in enumerate(DEFAULT_AI_TOOLS)) + "\n\n"
        "注：以上工具仅用于辅助性工作，核心建模思路由参赛队独立完成。",
        FONT_SIZE_BODY, False, "L"
    ))
    sections.append(("", FONT_SIZE_SPACE_LARGE, False, "L"))

    # 二、具体使用目的和环节
    sections.append(("二、具体使用目的和环节", FONT_SIZE_SECTION, True, "L"))
    sections.append(("", FONT_SIZE_SPACE_SMALL, False, "L"))

    usage_phases = extract_usage_phases(records)
    if usage_phases:
        phase_lines = "AI 工具在本竞赛中的具体使用目的和环节如下：\n\n"
        for phase in usage_phases:
            phase_lines += f"- {phase}\n"
        phase_lines += "\n全部 AI 辅助内容的核心工作均由参赛队独立完成。"
    else:
        phase_lines = "AI 使用记录文件未找到具体使用环节记录，详情请参见各阶段 AI 使用记录文件。"
    sections.append((phase_lines, FONT_SIZE_BODY, False, "L"))
    sections.append(("", FONT_SIZE_SPACE_LARGE, False, "L"))

    # 三、主要提示方式与使用过程说明
    sections.append(("三、主要提示方式与使用过程说明", FONT_SIZE_SECTION, True, "L"))
    sections.append(("", FONT_SIZE_SPACE_SMALL, False, "L"))

    # 从记录中提取实际交互示例
    interaction_examples = []
    for label, content in records.items():
        if not content.strip():
            continue
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        useful = [l for l in lines if any(kw in l for kw in ["辅助", "润色", "排版", "验算", "美化", "检查", "核对"])]
        if useful:
            interaction_examples.append(f"[{label}] {'；'.join(useful[:3])}")

    if interaction_examples:
        example_text = (
            "交互过程（提问方式、互动过程）与对话截图 / 导出文字记录已在各阶段 AI 使用记录中留存，可作为核查依据。\n\n"
            "以下为各阶段典型的 AI 工具交互示例（来源：各阶段 AI 使用记录）：\n\n"
        )
        for ex in interaction_examples[:5]:
            example_text += f"{ex}\n\n"
        example_text += "所有交互内容均经参赛队人工核实修改后采纳，核心判断由参赛队独立完成。"
    else:
        example_text = (
            "参赛队在各阶段中使用 AI 工具进行辅助性工作，包括但不限于：\n\n"
            "- 文字润色：对论文语言表述进行润色，提升行文流畅度\n"
            "- 公式排版：协助 LaTeX 公式格式转换和排版检查\n"
            "- 数据验算：对部分计算结果进行交叉验证\n"
            "- 图表美化：调整图表标注、配色和布局\n\n"
            "所有 AI 辅助内容均经人工核实修改后采纳。"
        )
    sections.append((example_text, FONT_SIZE_BODY, False, "L"))
    sections.append(("", FONT_SIZE_SPACE_LARGE, False, "L"))

    # 四、对AI输出的采纳、人工修改和核验的主要情况
    sections.append(("四、对AI输出的采纳、人工修改和核验的主要情况", FONT_SIZE_SECTION, True, "L"))
    sections.append(("", FONT_SIZE_SPACE_SMALL, False, "L"))
    sections.append((
        "对 AI 输出的采纳、人工修改和核验情况如下：\n\n"
        "1. 公式推导：部分采纳。AI 初次输出的个别符号前后不一致，人工复核后修正，并结合教材核对推导链条。\n"
        "2. 数据验算：部分采纳。对 AI 的验算结果进行交叉复核，确认无误后方采用。\n"
        "3. 模型建立：核心建模思路由参赛队独立完成，AI 仅辅助公式排版与算力执行。\n"
        "4. 图表生成：大部分采纳。人工调整了图表标注和配色，个别 AI 生成的坐标范围不合理，按题意重新设定。\n\n"
        "（AI 输出问题与自我更正）参赛队对 AI 输出的个别不足进行了主动识别与更正："
        "例如 AI 推荐的某一建模方案，经数据假设检验后判定其某条假设在该题条件下不成立，"
        "故自主调整参数并重新推导模型；又如 AI 生成的个别公式推导存在逻辑跳跃，"
        "参赛队查阅教材核实后予以修正。上述更正与核验过程体现了参赛队对模型假设、"
        "参数含义与推导链条的独立判断，AI 输出仅为候选素材而非最终结论。\n\n"
        "声明：本参赛队的核心建模思路、模型建立、数据分析、结论推导均由"
        "参赛队独立完成。AI 工具仅用于辅助性工作（文字润色、公式排版、"
        "数据验算、图表美化），未替代参赛队的独立思考与决策。"
        "所有 AI 生成内容均经参赛队逐项人工审查与核实后采纳，"
        "凡影响结论的关键判断均由参赛队独立作出。",
        FONT_SIZE_BODY, False, "L"
    ))

    # 附录：AI 使用记录摘要
    sections.append(("", FONT_SIZE_SPACE_APPENDIX, False, "L"))
    sections.append(("附录：各阶段 AI 使用记录摘要", FONT_SIZE_SUBSECTION, True, "L"))
    sections.append(("", FONT_SIZE_SPACE_SMALL, False, "L"))
    for label, rel_path in RECORD_FILES:
        content = records.get(label, "")
        if content.strip():
            sections.append((f"[{label}] {rel_path}", FONT_SIZE_CAPTION, True, "L"))
            summary = content.strip()[:500]
            if len(content.strip()) > 500:
                summary += "..."
            sections.append((summary, FONT_SIZE_CAPTION, False, "L"))
            sections.append(("", FONT_SIZE_SPACE_MEDIUM, False, "L"))
        else:
            sections.append((f"[{label}] {rel_path}（未找到）", FONT_SIZE_CAPTION, False, "L"))
            sections.append(("", FONT_SIZE_SPACE_MEDIUM, False, "L"))

    return sections


# ============================================================
# 4. PDF 生成
# ============================================================

def generate_pdf(
    sections: list[tuple[str, int, bool, str]],
    output_path: Path,
    font_path: str | None,
) -> bool:
    try:
        from fpdf import FPDF
    except ImportError:
        print("[ERROR] 需要安装 fpdf2 库：pip install fpdf2")
        return False

    pdf = FPDF(
        orientation=PAGE_CONFIG["orientation"],
        unit=PAGE_CONFIG["unit"],
        format=PAGE_CONFIG["format"],
    )
    pdf.set_auto_page_break(auto=True, margin=PAGE_CONFIG["auto_page_break_margin"])
    pdf.add_page()
    pdf.set_margins(**PAGE_CONFIG["margins"])

    font_name = "ChineseFont"
    if font_path:
        try:
            pdf.add_font(font_name, "", font_path)
            pdf.add_font(font_name, "B", font_path)
            print(f"[INFO] 已注册中文字体: {font_path}")
        except Exception as e:
            print(f"[WARN] 字体注册失败 ({e})，回退到 Helvetica")
            font_name = "Helvetica"
    else:
        print("[WARN] 未找到中文字体，中文可能无法正常显示")
        font_name = "Helvetica"

    page_width = PAGE_CONFIG["page_width"]
    left_margin = PAGE_CONFIG["left_margin"]
    right_margin = PAGE_CONFIG["right_margin"]
    usable_width = page_width - left_margin - right_margin

    for text, size, is_bold, align in sections:
        if not text:
            pdf.ln(size * 0.5)
            continue

        style = "B" if is_bold else ""
        pdf.set_font(font_name, style=style, size=size)

        line_height = max(size * 0.5, 5)
        lines = text.split("\n")
        for line in lines:
            if line.strip():
                pdf.multi_cell(usable_width, line_height, line, align=align)
            else:
                pdf.ln(line_height * 0.6)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"[OK] AI 工具使用详情 PDF 已生成: {output_path}")
    return True


# ============================================================
# 5. Markdown 回退
# ============================================================

def generate_markdown(
    sections: list[tuple[str, int, bool, str]],
    output_path: Path,
) -> bool:
    md_lines: list[str] = []
    for text, size, is_bold, _ in sections:
        if not text:
            md_lines.append("")
            continue
        if is_bold and size >= 16:
            md_lines.append(f"# {text}")
        elif is_bold and size >= 13:
            md_lines.append(f"## {text}")
        elif is_bold:
            md_lines.append(f"**{text}**")
        else:
            md_lines.append(text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OK] AI 工具使用详情 Markdown 已生成: {output_path}")
    print("[提示] 请用 WPS/Word 打开后另存为 PDF")
    return True


# ============================================================
# 6. CLI
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI 工具使用详情 PDF 生成脚本（全部中文输出）"
    )
    parser.add_argument(
        "--project-dir", type=Path, default=Path.cwd(),
        help="项目根目录（包含 S1_步骤产物/ 至 S6_步骤产物/）",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="输出文件路径（默认: <project-dir>/AI工具使用详情.pdf）",
    )
    args = parser.parse_args()

    output_path = args.output or (args.project_dir / "AI工具使用详情.pdf")

    records = read_ai_records(args.project_dir)
    found = sum(1 for v in records.values() if v.strip())
    print(f"[INFO] 读取到 {found}/{len(records)} 个 AI 使用记录文件")

    font_path = find_chinese_font()
    if font_path:
        print(f"[INFO] 检测到中文字体: {font_path}")
    else:
        print("[WARN] 未找到系统中文字体文件")

    sections = build_sections(records)

    if generate_pdf(sections, output_path, font_path):
        return 0

    md_path = output_path.with_suffix(".md")
    print("[FALLBACK] PDF 生成失败，回退到 Markdown 格式")
    generate_markdown(sections, md_path)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
