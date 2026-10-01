#!/usr/bin/env python3
"""
暂停点验证脚本

扫描指定阶段的产物目录，验证暂停标记和暂停确认的完整性。
作为阶段门禁检查的可选组成部分。

用法:
    python 暂停点验证.py --phase S1 --dir <项目根目录>

参数:
    --phase   阶段名称 (S1/S2/S3/S4/S5/S6)
    --dir     项目根目录路径

退出码:
    0 = 全部通过
    1 = 存在不通过项
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PHASE_DIR_MAP = {
    "S1": "S1_步骤产物",
    "S2": "S2_步骤产物",
    "S3": "S3_步骤产物",
    "S4": "S4_步骤产物",
    "S5": "S5_步骤产物",
    "S6": "S6_步骤产物",
}

AI_RECORD_KEYWORDS = ["AI使用记录", "ai_record"]


def is_ai_record(filename: str) -> bool:
    return any(kw in filename for kw in AI_RECORD_KEYWORDS)


def is_first_step(filename: str, phase: str) -> bool:
    """判断是否为该阶段的第一步产物。

    统一规则：从文件名提取步骤编号，步骤编号为 1 视为第一步；
    对以 0 起步的阶段（S3/S4），步骤编号 0 也视为第一步。
    S2 无编号命名，按首个产物命名特征（题意锚定）匹配。
    """
    # S2 无编号命名，首个产物为题意锚定卡
    if phase == "S2":
        return "题意锚定" in filename
    step_match = re.search(r"步骤(?:\d+[-_])?(\d+)", filename)
    if step_match:
        step_num = int(step_match.group(1))
        # 以 0 起步的阶段（S3/S4）第一步编号为 0，其余阶段为 1
        return step_num == (0 if phase in ("S3", "S4") else 1)
    return False


def has_pause_confirm(content: str) -> bool:
    return "【暂停确认】" in content


def has_pause_marker(content: str) -> bool:
    return "【步骤暂停" in content or "步骤暂停 ⏸" in content


def check_pause_confirm_format(content: str) -> bool:
    idx = content.find("【暂停确认】")
    if idx == -1:
        return False
    block = content[idx:idx + 500]
    has_step = "上一步骤" in block or "上一步" in block
    has_reply = "用户是否已回复" in block or "已回复" in block
    has_conclusion = "确认结论" in block or "可进入" in block or "等待" in block
    return has_step and has_reply and has_conclusion


def verify_phase(phase: str, project_dir: Path) -> tuple[bool, list[str]]:
    dir_name = PHASE_DIR_MAP.get(phase)
    if not dir_name:
        return False, [f"未知阶段: {phase}"]
    phase_dir = project_dir / dir_name
    if not phase_dir.exists():
        return False, [f"产物目录不存在: {phase_dir}"]

    md_files = sorted(phase_dir.glob("*.md"))
    if not md_files:
        return False, [f"产物目录为空: {phase_dir}"]

    issues: list[str] = []

    for f in md_files:
        fname = f.name
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] 读取产物文件失败: {f} — {e}", file=sys.stderr)
            raise

        if is_ai_record(fname):
            continue

        if is_first_step(fname, phase):
            continue

        if not has_pause_confirm(content):
            issues.append(f"{fname}: 缺少【暂停确认】段落")

        if not has_pause_marker(content):
            issues.append(f"{fname}: 缺少【步骤暂停 ⏸】标记")

        if has_pause_confirm(content) and not check_pause_confirm_format(content):
            issues.append(f"{fname}: 【暂停确认】格式不完整（缺上一步骤/用户回复/确认结论）")

    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description="暂停点验证脚本")
    parser.add_argument("--phase", required=True, choices=list(PHASE_DIR_MAP.keys()))
    parser.add_argument("--dir", required=True, help="项目根目录路径")
    args = parser.parse_args()

    project_dir = Path(args.dir)
    if not project_dir.exists():
        print(f"❌ 项目目录不存在: {project_dir}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"暂停点验证 — 阶段: {args.phase}")
    print(f"{'='*60}")

    passed, issues = verify_phase(args.phase, project_dir)

    if not issues:
        print("✅ 全部暂停标记和暂停确认完整")
    else:
        for i in issues:
            print(f"  ❌ {i}")

    print(f"{'='*60}")
    if passed:
        print("✅ 暂停点验证通过")
        sys.exit(0)
    else:
        print(f"❌ 暂停点验证未通过（{len(issues)}个问题）")
        sys.exit(1)


if __name__ == "__main__":
    main()
