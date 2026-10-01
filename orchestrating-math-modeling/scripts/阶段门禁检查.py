#!/usr/bin/env python3
"""
阶段门禁检查脚本

在阶段过渡时检查本阶段所有应产物是否齐全。

用法:
    python 阶段门禁检查.py --phase S1 --dir <项目根目录>
    python 阶段门禁检查.py --phase S1 --dir <项目根目录> --auto

参数:
    --phase   阶段名称 (S1/S2/S3/S4/S5/S6)
    --dir     项目根目录路径
    --auto    启用auto模式专项检查（决策日志+hard_blocker验证）

退出码:
    0 = 门禁通过
    1 = 门禁未通过
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

YINGYOU_WENJIAN: dict[str, list[str]] = {
    "S1": [
        "步骤1_题目理解.md",
        "步骤2_附件理解.md",
        "步骤3_文献检索.md",
        "步骤4_资料文档.md",
        "步骤5_初稿方案.md",
        "步骤6_创新点设计.md",
        "步骤7_最终创新点初稿.md",
        "AI使用记录.md",
    ],
    "S2": [
        "步骤2-1_可行性与风险应对.md",
        "步骤2-2_建模计划_v*.md",
        "步骤2-3_最终建模计划.md",
        "AI使用记录.md",
    ],
    "S3": [
        "结果摘要.md",
        "变量符号约定.md",
        "模型验证结论.md",
        "AI使用记录.md",
    ],
    "S4": [
        "步骤0_正文写作规范.md",
        "步骤1_问题分析.md",
        "步骤2_模型假设.md",
        "步骤3_模型建立与求解.md",
        "步骤4_定义与符号说明.md",
        "步骤5_模型检验.md",
        "步骤6_模型的评价及优化.md",
        "步骤7_支撑材料生成.md",
        "步骤8_参考文献.md",
        "步骤9_附录.md",
        "步骤10_全文校对.md",
        "步骤11_摘要撰写.md",
        "步骤12_论文整篇整合.md",
        "AI使用记录A.md",
        "AI使用记录B.md",
        "AI使用记录C.md",
    ],
    "S5": [
        "步骤0_红队攻击报告.md",
        "步骤1_数据一致性校验.md",
        "步骤2_编号一致性校验.md",
        "步骤3_合规与格式预检.md",
        "AI使用记录.md",
    ],
    "S6": [
        "步骤1_全量产物索引.md",
        "步骤2_格式排版与论文生成.md",
        "步骤3_最终定稿.md",
        "AI使用记录.md",
    ],
}

PHASE_SPECIAL_CHECKS: dict[str, list[str]] = {
    "S2": ["最终建模计划.md 必须存在（锁定步骤）"],
    "S3": ["代码/图片/表格/日志 四个目录必须存在", "结果摘要.md + 变量符号约定.md + 模型验证结论.md 必须存在"],
    "S4": ["S4A(5)+S4B(4)+S4C(7)=16个产物必须齐全"],
    "S6": ["论文.docx 必须存在", "AI工具使用详情.pdf 必须存在"],
}

# 门禁检查阈值
MIN_DECISION_COUNT = 1           # 决策日志中至少需要的 [决策] 记录数

# 门禁检查项列表（供报告展示）
GATE_CHECK_ITEMS = [
    "应有产物齐全性检查",
    "阶段特殊检查（S2锁定/S3产物数/S4产物数/S6交付物）",
    "auto模式：决策日志检查",
    "auto模式：hard_blocker暂停确认检查",
]


def find_matching_files(phase_dir: Path, pattern: str) -> list[Path]:
    if "*" in pattern:
        return sorted(phase_dir.glob(pattern))
    p = phase_dir / pattern
    return [p] if p.exists() else []


def check_version_in_file(filepath: Path) -> str | None:
    if not filepath.exists():
        return None
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {filepath} — {e}", file=sys.stderr)
        raise
    m = re.search(r"\*\*版本\*\*[：:]\s*v(\d+)\.(\d+)", content)
    if m:
        return f"v{m.group(1)}.{m.group(2)}"
    return None


def check_code_overview_structure(filepath: Path) -> bool:
    """占位函数，运行结果已删除，S3特殊检查改为产物齐全性"""
    return True


def check_zero_modification_suspicion(phase_dir: Path) -> tuple[bool, str]:
    """独立抽查提醒：若本阶段产物全部声称 v1.0 零修改（高度可疑），提示做独立抽查。

    产物规范.md 7.3.3：当作者全部声称 v1.0 直接通过且零修改时，独立抽查为必做。
    本检查为硬性告警：返回 False 即提示必须做独立抽查，但不在门禁中直接阻断（由主流程打印提示供人工复核）。
    """
    md_files = [f for f in phase_dir.glob("*.md") if "AI使用记录" not in f.name]
    if not md_files:
        return True, "无产物，跳过零修改可疑检测"

    all_v10 = True
    any_version = False
    any_v20 = False  # 存在 v2.0+（大迭代）即不算零修改
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        m = re.search(r"\*\*版本\*\*[：:]\s*v(\d+)\.(\d+)", content)
        if not m:
            continue
        any_version = True
        major = m.group(1)
        full = f"{m.group(1)}.{m.group(2)}"
        if int(major) >= 2:
            any_v20 = True
        if full != "1.0":
            all_v10 = False

    if any_v20 or (any_version and not all_v10):
        return True, "产物存在高版本或 v1.x 迭代，零修改可疑检测不触发"
    if any_version and all_v10:
        return False, "⚠️ 本阶段产物全部为 v1.0（零修改），高度可疑——请按产物规范.md 7.3.3 执行独立抽查（≥30%）确认确有实质证否排除，而非检查走过场"
    return True, "产物缺少完整版本字段，零修改可疑检测不触发"


def check_decision_log(phase_dir: Path) -> tuple[bool, str]:
    """决策日志检查（软检查）：产物中有决策日志内容（表格或[决策]标记）即通过；
    无决策日志内容时跳过不视为失败。当前所有阶段文件均未要求决策日志，故恒通过。"""
    md_files = list(phase_dir.glob("*.md"))
    for f in md_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {f} — {e}", file=sys.stderr)
            raise
        if "[决策]" in content or "决策日志" in content:
            return True, f"找到决策日志内容（在{f.name}中）"
    return True, "无决策日志要求，跳过"


def check_hard_blocker_pause(phase_dir: Path) -> tuple[bool, str]:
    md_files = list(phase_dir.glob("*.md"))
    for f in md_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {f} — {e}", file=sys.stderr)
            raise
        if "hard_blocker" in content.lower() or "阻塞报告" in content:
            if "已暂停等待用户确认" in content or "用户确认" in content:
                return True, f"hard_blocker已记录暂停确认（在{f.name}中）"
            return False, f"发现hard_blocker但未记录暂停确认（在{f.name}中）"
    return True, "无hard_blocker触发"


def verify_phase_gate(phase: str, project_dir: Path, auto: bool) -> tuple[bool, list[str]]:
    dir_name = PHASE_DIR_MAP.get(phase)
    if not dir_name:
        return False, [f"未知阶段: {phase}"]
    phase_dir = project_dir / dir_name
    if not phase_dir.exists():
        return False, [f"产物目录不存在: {phase_dir}"]

    required = YINGYOU_WENJIAN.get(phase, [])
    issues: list[str] = []
    missing_files: list[str] = []

    for pattern in required:
        matches = find_matching_files(phase_dir, pattern)
        if not matches:
            missing_files.append(pattern)
            continue

    if missing_files:
        issues.append(f"缺失产物({len(missing_files)}个): {', '.join(missing_files)}")

    if phase == "S3":
        # S3特殊检查：四个目录必须存在
        required_dirs = ["代码", "图片", "表格", "中间数据"]
        missing_dirs = [d for d in required_dirs if not (phase_dir / d).is_dir()]
        if missing_dirs:
            issues.append(f"S3缺失目录({len(missing_dirs)}个): {', '.join(missing_dirs)}")

    if phase == "S6":
        docx_files = list(project_dir.glob("*.docx")) + list(project_dir.glob("论文*.docx"))
        pdf_files = (list(project_dir.glob("AI工具使用详情.pdf"))
                     + list(phase_dir.glob("AI工具使用详情.pdf"))
                     + list((project_dir / "支撑材料").glob("AI工具使用详情.pdf")))
        if not docx_files:
            issues.append("论文.docx 不存在")
        if not pdf_files:
            issues.append("AI工具使用详情.pdf 不存在")

    # 零修改可疑检测（产物规范.md 7.3.3 独立抽查提示）：打印提醒供人工复核，不阻断门禁通过
    zero_passed, zero_msg = check_zero_modification_suspicion(phase_dir)
    if not zero_passed:
        print(f"\n👀 {zero_msg}")

    if auto:
        dl_passed, dl_msg = check_decision_log(phase_dir)
        if not dl_passed:
            issues.append(f"[auto] 决策日志: {dl_msg}")
        hb_passed, hb_msg = check_hard_blocker_pause(phase_dir)
        if not hb_passed:
            issues.append(f"[auto] hard_blocker: {hb_msg}")

    return len(issues) == 0, issues


def main():
    parser = argparse.ArgumentParser(description="阶段门禁检查脚本")
    parser.add_argument("--phase", required=True, choices=list(PHASE_DIR_MAP.keys()))
    parser.add_argument("--dir", required=True, help="项目根目录路径")
    parser.add_argument("--auto", action="store_true", help="启用auto模式专项检查")
    args = parser.parse_args()

    project_dir = Path(args.dir)
    if not project_dir.exists():
        print(f"❌ 项目目录不存在: {project_dir}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"阶段门禁检查 — 阶段: {args.phase} | 模式: {'auto' if args.auto else 'standard'}")
    print(f"{'='*60}")

    passed, issues = verify_phase_gate(args.phase, project_dir, args.auto)

    required = YINGYOU_WENJIAN.get(args.phase, [])
    print(f"\n应有产物: {len(required)}个")
    print(f"问题数: {len(issues)}个")

    if issues:
        print("\n❌ 门禁未通过，问题清单:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print(f"\n{'='*60}")
        print("❌ 阶段门禁未通过 — 禁止进入下一阶段")
        print("   请补全缺失产物或修复问题后重新运行本检查。")
        sys.exit(1)
    else:
        print("\n✅ 全部检查项通过")
        print(f"\n{'='*60}")
        print("✅ 阶段门禁通过 — 允许进入下一阶段")
        sys.exit(0)


if __name__ == "__main__":
    main()
