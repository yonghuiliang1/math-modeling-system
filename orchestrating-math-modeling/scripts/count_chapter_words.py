#!/usr/bin/env python3
"""
CUMCM 章节字数统计脚本
基于 chinese-thesis-workbench 的 count_chapter_words.py + markdown_utils.py，
叠加 CUMCM 国赛页数估算功能。

用法:
    python count_chapter_words.py <markdown-file>

输出:
    TOTAL    全文统计
    各章节   按 ## 标题分割统计
    末尾附 CUMCM 红线核查（摘要页数 / 正文页数）

CUMCM 页数估算说明:
    - 摘要页：约 800-1000 中文字符为一页
    - 正文页：约 1500-1800 中文字符为一页（含图表空间）
    - 附录页：不计入正文页数
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any


# ============================================================
# 1. 加载 chinese-thesis-workbench 的 markdown_utils
# ============================================================

def _find_markdown_utils_path() -> Path:
    """定位 chinese-thesis-workbench 的 markdown_utils.py：先项目内，再全局 skills"""
    candidates = [
        Path(__file__).resolve().parents[1]
        / "chinese-thesis-workbench" / "scripts" / "docx" / "markdown_utils.py",
        Path.home() / ".trae-cn" / "skills" / "chinese-thesis-workbench"
        / "scripts" / "docx" / "markdown_utils.py",
        Path.home() / ".trae" / "skills" / "chinese-thesis-workbench"
        / "scripts" / "docx" / "markdown_utils.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("; ".join(str(c) for c in candidates))


try:
    MARKDOWN_UTILS_PATH = _find_markdown_utils_path()
except FileNotFoundError as e:
    print(
        "错误: 未找到 chinese-thesis-workbench 的 markdown_utils.py。\n"
        f"  已搜索路径: {e}\n"
        "  请检查 chinese-thesis-workbench 是否已安装，以及其安装位置是否正确。\n"
        "  该脚本依赖 chinese-thesis-workbench 提供 markdown 文本统计工具。",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _load_markdown_utils():
    try:
        spec = importlib.util.spec_from_file_location("markdown_utils", MARKDOWN_UTILS_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load markdown utilities: {MARKDOWN_UTILS_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(
            f"错误: 加载 markdown_utils 模块失败: {e}\n"
            f"  已搜索路径: {MARKDOWN_UTILS_PATH}\n"
            "  请检查 chinese-thesis-workbench 是否已安装，以及其安装位置是否正确。",
            file=sys.stderr,
        )
        raise SystemExit(1)


_mu = _load_markdown_utils()
compute_text_metrics = _mu.compute_text_metrics


# ============================================================
# 2. 章节分割
# ============================================================

CHAPTER_RE = re.compile(r"^##\s+(.+)$", flags=re.M)


def chapter_spans(text: str) -> list[tuple[str, int, int]]:
    matches = list(CHAPTER_RE.finditer(text))
    spans: list[tuple[str, int, int]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        spans.append((match.group(1).strip(), start, end))

    return spans


# ============================================================
# 3. 格式化输出
# ============================================================

def format_metrics(label: str, metrics: dict[str, int]) -> str:
    return (
        f"{label}\t"
        f"APPROX_WORDS={metrics['approx_word_count']}\t"
        f"CHAR_NO_SPACES={metrics['char_no_spaces']}\t"
        f"CHAR_WITH_SPACES={metrics['char_with_spaces']}\t"
        f"CJK_CHARS={metrics['chinese_chars']}\t"
        f"NON_CJK_WORDS={metrics['non_chinese_words']}\t"
        f"EN_WORDS={metrics['english_words']}"
    )


# ============================================================
# 4. CUMCM 页数估算与红线核查
# ============================================================

# CUMCM 页数估算常量
CHARS_PER_PAGE = 1700             # 正文每页约 1700 中文字符（含图表空间）
CHARS_PER_PAGE_ABSTRACT = 900     # 摘要每页约 900 中文字符
BODY_PAGE_LIMIT = 30              # 正文不超过 30 页
ABSTRACT_PAGE_LIMIT = 1           # 摘要不超过 1 页

# 章节标题关键词识别
ABSTRACT_KEYWORDS = {"摘要", "abstract"}
APPENDIX_KEYWORDS = {"附录"}
REFERENCES_KEYWORDS = {"参考文献"}


def estimate_pages(cjk_chars: int, chars_per_page: int) -> float:
    """估算页数，向上取整到整数。"""
    if chars_per_page <= 0 or cjk_chars <= 0:
        return 0.0
    return (cjk_chars + chars_per_page - 1) // chars_per_page


def cumcm_red_line_check(chapters: list[tuple[str, dict[str, int]]]) -> list[str]:
    """CUMCM 红线核查，返回警告列表。"""
    warnings: list[str] = []

    abstract_chars = 0
    body_chars = 0
    appendix_chars = 0

    for title, metrics in chapters:
        normalized = title.replace(" ", "").lower()
        if normalized in ABSTRACT_KEYWORDS:
            abstract_chars += metrics["chinese_chars"]
        elif normalized in APPENDIX_KEYWORDS:
            appendix_chars += metrics["chinese_chars"]
        elif normalized in REFERENCES_KEYWORDS:
            # 参考文献不计入正文页数
            pass
        else:
            body_chars += metrics["chinese_chars"]

    # 摘要页数检查
    abstract_pages = estimate_pages(abstract_chars, CHARS_PER_PAGE_ABSTRACT)
    if abstract_pages > ABSTRACT_PAGE_LIMIT:
        warnings.append(
            f"  [!] 摘要约 {abstract_pages} 页，超过 {ABSTRACT_PAGE_LIMIT} 页红线 "
            f"(摘要约 {abstract_chars} 中文字符，每页按 {CHARS_PER_PAGE_ABSTRACT} 字估算)"
        )
    else:
        warnings.append(
            f"  [OK] 摘要约 {abstract_pages} 页，未超过 {ABSTRACT_PAGE_LIMIT} 页红线 "
            f"(摘要约 {abstract_chars} 中文字符)"
        )

    # 正文页数检查
    body_pages = estimate_pages(body_chars, CHARS_PER_PAGE)
    if body_pages > BODY_PAGE_LIMIT:
        warnings.append(
            f"  [!] 正文约 {body_pages} 页，超过 {BODY_PAGE_LIMIT} 页红线 "
            f"(正文约 {body_chars} 中文字符，每页按 {CHARS_PER_PAGE} 字估算，附录不计入)"
        )
    else:
        warnings.append(
            f"  [OK] 正文约 {body_pages} 页，未超过 {BODY_PAGE_LIMIT} 页红线 "
            f"(正文约 {body_chars} 中文字符，附录不计入)"
        )

    # 附录页数（仅供参考，无红线）
    appendix_pages = estimate_pages(appendix_chars, CHARS_PER_PAGE)
    warnings.append(
        f"  [--] 附录约 {appendix_pages} 页 (仅供参考，附录不计入正文页数限制)"
    )

    return warnings


# ============================================================
# 5. CLI
# ============================================================

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python count_chapter_words.py <markdown-file>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 1

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] 读取 Markdown 文件失败: {path} — {e}", file=sys.stderr)
        return 1

    # 全文统计
    print(format_metrics("TOTAL", compute_text_metrics(text)))
    print()

    # 章节统计
    chapters: list[tuple[str, dict[str, int]]] = []
    for title, start, end in chapter_spans(text):
        metrics = compute_text_metrics(text[start:end])
        print(format_metrics(title, metrics))
        chapters.append((title, metrics))

    # CUMCM 红线核查
    print()
    print("=" * 60)
    print("CUMCM 红线核查")
    print("=" * 60)
    warnings = cumcm_red_line_check(chapters)
    for w in warnings:
        print(w)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
