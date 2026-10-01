#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公式库.py — 确定性复算硬钩子（微循环复算闭环改造 v3）

定位：把"复算"从碰运气变成强制动作。微循环每轮调用本模块，对隔离子Agent返回的核查结论中的
"复算记录"做算术核验，抓出"对账查不出、复算才查出"的计算错（如 989 vs 589.6）。

依据：微循环复算闭环改造方案.md（分层 + 全量复算 + 三连判据）

用法:
    公式库复算工具：
        import importlib.util  # 或直接 import 公式库
        errors = 公式库.verify_recalculation_records(check_report_text)
        pass  # errors 为空 = 所有复算记录算术正确

    独立自检:
        python 公式库.py --self_check

核验规则:
    1) 主核验「复算记录」：扫描文本，提取形如
           `充满时刻 = 12 × 1474 ÷ 30 = 589.6`
       （名 = 算式 = 结果）的记录，用白名单表达式安全求值，比对"结果 = 算式值"。
       支持中文运算符 × ÷ 以及 + - * / () 与小数、幂 ^。
    2) 求和自洽：形如 `类型求和 = 223 + 372 + 382 = 977` 同样被覆盖核验。
    3) 无法数值判定的确定性断言（如"到达时刻 ≤ 充满时刻"单调不变式），
       由本模块以"说明性断言"返回提醒字段，不强行数值判定。

安全: 用 ast 白名单求值，仅允许数字与 + - * / ( ) **，杜绝任意代码执行。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 一、安全表达式求值（ast 白名单，禁止任意代码执行）
# ---------------------------------------------------------------------------

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
    ast.UnaryOp, ast.USub, ast.UAdd, ast.Mod,
)

_OPERATOR_ALIASES = {
    "×": "*",
    "x": "*",
    "X": "*",
    "·": "*",
    "÷": "/",
    "／": "/",
    "−": "-",
    "﹣": "-",  # 全角减号
    "^": "**",
    "**": "**",
}


def _translate_expr(expr: str) -> str:
    """把表达式中人类书写的中文符号/空格规整为 Python 可求值形式。"""
    out = expr
    # 全角空格→半角
    out = out.replace("　", " ")
    for src, dst in _OPERATOR_ALIASES.items():
        if src != "**":
            out = out.replace(src, dst)
    out = out.replace("---", "-")  # 去除可能的重复负号
    out = out.strip()
    # 把分隔多个空格的整理为单空格，但保留"**"不被破坏
    out = re.sub(r"\s+", "", out)
    return out


def safe_eval_expr(expr: str) -> float:
    """在 ast 白名单下求值一个算术表达式，返回 float。非法则抛 ValueError。"""
    translated = _translate_expr(expr)
    if not translated:
        raise ValueError(f"空表达式: {expr!r}")
    # 阻断明显危险模式
    if any(k in translated for k in ("__", "import", "exec", "eval", "lambda", "open", "[")):
        raise ValueError(f"包含非算术内容: {expr!r}")
    try:
        tree = ast.parse(translated, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"表达式语法错误: {expr!r} ({e})")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"表达式含非法节点 {type(node).__name__}: {expr!r}")
    return float(eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {}))


def _extract_number(text: str) -> float | None:
    """从一段文本中提取第一个数字（含小数、负号）。"""
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


# ---------------------------------------------------------------------------
# 二、复算记录核验
# ---------------------------------------------------------------------------

# 复算记录行：形如「名 = 算式 = 结果[单位]」，「算式」只含数字与运算符
# 例：充满时刻 = 12 × 1474 ÷ 30 = 589.6 min
_RECHECK_LINE_RE = re.compile(
    r"^\s*([^=\n]{1,40}?)\s*=\s*"
    r"([0-9\s\+\-\*/×÷·xX()^\.]{3,})\s*=\s*"
    r"(-?\d+(?:\.\d+)?)\s*[A-Za-z%]*\s*$"
)


def _is_likely_expr(piece: str) -> bool:
    """判断一段是否为'算式'（至少含一个运算符号）。"""
    return bool(re.search(r"[\+\-\*/×÷·^]", piece))


def _parse_recalc_pieces(line: str) -> list[tuple[str, str, float]]:
    """从一行中提取所有 (name, expr, expected) 复算候选。

    兼容 markdown 表格行：按 '|' 拆单元格分别解析（三必查板块的复算记录就在表格里，
    整行以 '|' 开头，不能整行跳过）；普通行整行解析。表达式中不含 '|'，故拆 cell 安全。
    """
    if "|" in line:
        cells = [c.strip() for c in line.split("|")]
        # 去除空 cell 与表头/分隔行（纯 - : 字符）
        cells = [c for c in cells if c and not set(c) <= set("-:")]
        pieces = cells
    else:
        pieces = [line.strip()]
    out: list[tuple[str, str, float]] = []
    for piece in pieces:
        if "=" not in piece:
            continue
        parts = [p.strip() for p in piece.split("=")]
        # 需至少「名 = 算式 = 结果」三段
        if len(parts) < 3:
            continue
        name = parts[0]
        if not name:
            continue
        expr = parts[1]
        result_part = "=".join(parts[2:])
        expected = _extract_number(result_part)
        if expected is None:
            continue
        if not _is_likely_expr(expr):
            continue
        out.append((name, expr, expected))
    return out


def verify_recalculation_records(text: str) -> list[str]:
    """核验调用方传入的核查结论中所有'复算记录'的算术正确性。

    返回错误清单（空列表 = 全部复算记录算术正确或没有可核验记录）。
    """
    errors: list[str] = []
    if not text:
        return errors
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or "=" not in line:
            continue
        for name, expr, expected in _parse_recalc_pieces(line):
            try:
                actual = safe_eval_expr(expr)
            except ValueError:
                # 无法求值（可能含业务说明文字）→ 不强行数值判定
                continue
            if abs(actual - expected) > 1e-6:
                errors.append(f"第{lineno}行「{name}」: 算式 {expr} 重算 = {actual:g}，"
                              f"记录结果 = {expected:g}，不符（疑似 989 型计算错）")
    return errors


# ---------------------------------------------------------------------------
# 三、说明性确定性断言（无法数值判定的单调不变式等，供提示，不阻断）
# ---------------------------------------------------------------------------

_INVARIANT_PATTERNS = [
    (re.compile(r"充满时刻\s*[≤>=]\s*到达时刻"), "充满时刻应 ≥ 到达时刻（水先达后充满）"),
    (re.compile(r"到达时刻\s*[≤<]\s*充满时刻"), "到达时刻应 ≤ 充满时刻（水先达后充满）"),
    (re.compile(r"合计\s*=\s*\d+\s*\+\s*\d+\s*\+\s*\d+\s*=\s*\d+"), "求和自洽"),
]


def scan_invariants(text: str) -> list[str]:
    """扫描确定性单调不变式，返回命中提示（用于人工复核，不阻断）。"""
    hints: list[str] = []
    for pat, desc in _INVARIANT_PATTERNS:
        if pat.search(text):
            hints.append(f"命中确定性不变式: {desc}")
    return hints


# ---------------------------------------------------------------------------
# 四、自检入口
# ---------------------------------------------------------------------------

def _self_check() -> None:
    # 正确样例
    good = "充满时刻 = 12 × 1474 ÷ 30 = 589.6 min"
    # 错误样例（989 型）
    bad = "充满时刻 = 12 × 1474 ÷ 30 = 989 min"
    # 求和自洽正确
    sum_ok = "类型求和 = 223 + 372 + 382 = 977"
    # 求和自洽错误
    sum_bad = "类型求和 = 223 + 372 + 382 = 900"
    for text in (good, sum_ok):
        errs = verify_recalculation_records(text)
        print(f"[自检-应通过] {text} -> 错误={len(errs)} {'✅' if not errs else errs}")
    for text in (bad, sum_bad):
        errs = verify_recalculation_records(text)
        print(f"[自检-应拦截] {text} -> 错误={len(errs)} {'❌未拦!!' if not errs else '✅已拦截'}")


if __name__ == "__main__":
    if "--self_check" in sys.argv:
        _self_check()
    else:
        print("公式库.py — 公式复算工具。运行 --self_check 做自检。")