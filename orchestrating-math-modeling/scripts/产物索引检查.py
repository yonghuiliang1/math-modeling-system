# -*- coding: utf-8 -*-
r"""
数学建模论文全流程 — 产物索引自动检查工具（适配 orchestrating-math-modeling 新结构）
====================================================================================
功能：扫描 S1_步骤产物 ~ S6_步骤产物 文件夹，对照应有文件清单，
      输出"齐全/缺失"状态表，统计文件数量、非空状态、最后修改时间，
      并自动定位断点（缺失项 → 最后完成步骤）。

用法：
    python 产物索引检查.py                 # 检查项目根目录下所有产物
    python 产物索引检查.py --path C:\xxx  # 指定项目根目录
    python 产物索引检查.py --verbose       # 显示详细信息（含每个文件内容摘要）
    python 产物索引检查.py --fix           # 自动创建缺失的文件夹

依赖：无（仅使用 Python 标准库）
Python 版本：3.6+
"""

import os
import sys
import argparse
from datetime import datetime

# ============================================================
# 配置区：各部分应有的文件清单（与 references/产物规范.md 5.2 保持一致）
# static: 固定文件名（精确匹配）
# dynamic_prefix: 动态文件前缀（前缀匹配，如 S3 的"问题"、S2 的版本化建模计划）
# ============================================================

YINGYOU_WENJIAN = {
    "S1_步骤产物": {
        "static": [
            "步骤1_题目理解.md",
            "步骤2_附件理解.md",
            "步骤3_文献检索.md",
            "步骤4_资料文档.md",
            "步骤5_初稿方案.md",
            "步骤6_创新点设计.md",
            "步骤7_最终创新点初稿.md",
            "AI使用记录.md",
        ],
        "dynamic_prefix": [],
    },
    "S2_步骤产物": {
        "static": [
            "步骤2-1_可行性与风险应对.md",
            "步骤2-3_最终建模计划.md",
            "AI使用记录.md",
        ],
        "dynamic_prefix": ["步骤2-2_建模计划_v"],
    },
    "S3_步骤产物": {
        "static": [
            "结果摘要.md",
            "变量符号约定.md",
            "模型验证结论.md",
            "AI使用记录.md",
        ],
        "dynamic_prefix": [],
        "dirs_required": [
            "代码",
            "图片",
            "表格",
            "中间数据",
        ],
    },
    "S4_步骤产物": {
        "static": [
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
            "aigc-style-report.md",
            "步骤11_摘要撰写.md",
            "步骤12_论文整篇整合.md",
            "AI使用记录A.md",
            "AI使用记录B.md",
            "AI使用记录C.md",
        ],
        "dynamic_prefix": [],
    },
    "S5_步骤产物": {
        "static": [
            "步骤0_红队攻击报告.md",
            "步骤1_数据一致性校验.md",
            "步骤2_编号一致性校验.md",
            "步骤3_合规与格式预检.md",
            "AI使用记录.md",
        ],
        "dynamic_prefix": [],
    },
    "S6_步骤产物": {
        "static": [
            "步骤1_全量产物索引.md",
            "步骤2_格式排版与论文生成.md",
            "步骤3_最终定稿.md",
            "AI使用记录.md",
        ],
        "dynamic_prefix": [],
    },
}

# 颜色定义（终端彩色输出）
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def huoqu_wenjian_info(file_path):
    """获取文件信息：大小、修改时间、是否非空"""
    if not os.path.exists(file_path):
        return {"exists": False, "size": 0, "mtime": None, "non_empty": False}

    stat = os.stat(file_path)
    return {
        "exists": True,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "non_empty": stat.st_size > 0,
    }


def jiancha_bufen(bufen_name, bufen_dir, bufen_config, verbose=False):
    """检查某个部分的产物完整性"""
    static_files = bufen_config["static"]
    dynamic_prefixes = bufen_config.get("dynamic_prefix", [])
    dirs_required = bufen_config.get("dirs_required", [])

    # 获取实际存在的文件列表（md + json + py等）
    actual_files = []
    actual_dirs = []
    if os.path.isdir(bufen_dir):
        for item in os.listdir(bufen_dir):
            item_path = os.path.join(bufen_dir, item)
            if os.path.isdir(item_path):
                actual_dirs.append(item)
            else:
                actual_files.append(item)

    # 检查静态文件
    static_found = []
    static_missing = []
    for f in static_files:
        fpath = os.path.join(bufen_dir, f)
        info = huoqu_wenjian_info(fpath)
        if info["exists"]:
            static_found.append((f, info))
        else:
            static_missing.append(f)

    # 检查动态文件（前缀匹配）
    dynamic_found = []
    dynamic_missing = []
    for prefix in dynamic_prefixes:
        matched = [f for f in actual_files if f.startswith(prefix) and f not in static_files]
        if matched:
            for f in matched:
                fpath = os.path.join(bufen_dir, f)
                info = huoqu_wenjian_info(fpath)
                dynamic_found.append((f, info))
        else:
            dynamic_missing.append(prefix + "*")

    # 检查必需目录
    dirs_found = []
    dirs_missing = []
    for d in dirs_required:
        if d in actual_dirs:
            dirs_found.append(d)
        else:
            dirs_missing.append(d + "/")

    total_found = len(static_found) + len(dynamic_found) + len(dirs_found)
    total_missing = len(static_missing) + len(dynamic_missing) + len(dirs_missing)

    # 输出结果
    status = (
        f"{GREEN}齐全{RESET}"
        if total_missing == 0
        else f"{RED}缺失{RESET}"
    )

    print(f"\n{'='*60}")
    print(f"{BOLD}{CYAN}{bufen_name}{RESET}")
    print(f"{'='*60}")
    print(f"  应有文件数: {len(static_files) + len(dynamic_prefixes) + len(dirs_required)}")
    print(f"  实际文件数: {total_found}")
    print(f"  状态: {status}")

    if static_missing or dynamic_missing or dirs_missing:
        print(f"\n  {RED}缺失文件:{RESET}")
        for f in static_missing:
            print(f"    {RED}✗ {f}{RESET}")
        for p in dynamic_missing:
            print(f"    {RED}✗ {p}（动态匹配，未找到）{RESET}")
        for d in dirs_missing:
            print(f"    {RED}✗ {d}（必需目录，不存在）{RESET}")

    if verbose or static_found or dynamic_found or dirs_found:
        print(f"\n  {GREEN}已有文件:{RESET}")
        for f, info in static_found + dynamic_found:
            empty_mark = f"{YELLOW}(空文件){RESET}" if not info["non_empty"] else ""
            size_str = f"{info['size']} bytes" if info["size"] < 1024 else f"{info['size']/1024:.1f} KB"
            print(f"    {GREEN}✓{RESET} {f}  [{size_str}] {info['mtime']} {empty_mark}")
        for d in dirs_found:
            print(f"    {GREEN}✓{RESET} {d}/  [目录]")

    return {
        "part": bufen_name,
        "expected": len(static_files) + len(dynamic_prefixes),
        "found": total_found,
        "missing": static_missing + dynamic_missing,
        "complete": total_missing == 0,
    }


def dingwei_duandian(all_results):
    """根据缺失项自动定位断点（最后一个完整阶段的下一步）"""
    for i, r in enumerate(all_results):
        if not r["complete"]:
            # 找到第一个缺失的阶段
            if i == 0:
                return "S1 起始阶段产物缺失，需从 S1 步骤1 开始"
            # 前一个阶段完整，当前阶段缺失
            prev_part = all_results[i - 1]["part"]
            missing_hint = r["missing"][0] if r["missing"] else "未知文件"
            return f"断点定位：{prev_part} 已完成，{r['part']} 缺失文件「{missing_hint}」，从该缺失步骤恢复"
    return "全部产物齐全，无断点"


def jiancha_xiangmu(root_dir, verbose=False, fix=False):
    """检查整个项目的产物完整性"""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}数学建模论文全流程产物索引检查{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"项目根目录: {root_dir}")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_results = []
    total_expected = 0
    total_found = 0
    total_missing = 0

    for bufen_name, bufen_config in YINGYOU_WENJIAN.items():
        bufen_dir = os.path.join(root_dir, bufen_name)

        # 如果--fix模式，创建缺失的文件夹
        if fix and not os.path.isdir(bufen_dir):
            os.makedirs(bufen_dir, exist_ok=True)
            print(f"\n{YELLOW}已创建文件夹: {bufen_dir}{RESET}")

        result = jiancha_bufen(bufen_name, bufen_dir, bufen_config, verbose)
        all_results.append(result)

        total_expected += result["expected"]
        total_found += result["found"]
        total_missing += len(result["missing"])

    # 汇总
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}汇总{RESET}")
    print(f"{'='*60}")
    print(f"{'部分':<25} {'应有':>6} {'已有':>6} {'缺失':>6} {'状态':>6}")
    print(f"{'-'*55}")

    for r in all_results:
        status = f"{GREEN}✓{RESET}" if r["complete"] else f"{RED}✗{RESET}"
        miss = len(r["missing"])
        print(f"{r['part']:<25} {r['expected']:>6} {r['found']:>6} {miss:>6}   {status}")

    print(f"{'-'*55}")
    print(f"{'总计':<25} {total_found}/{total_expected:>12}")

    # 总体完成度
    if total_missing == 0:
        print(f"\n{GREEN}{BOLD}✓ 全部产物文件齐全！{RESET}")
    else:
        print(f"\n{RED}{BOLD}✗ 共有 {total_missing} 个文件缺失，请补充。{RESET}")

    # 断点定位
    print(f"\n{BOLD}断点定位:{RESET}")
    print(f"  {dingwei_duandian(all_results)}")

    # 检查额外文件（非步骤产物的关键文件）
    print(f"\n{BOLD}关键文件检查:{RESET}")
    guanjian_wenjian = ["论文.docx", "图片", "表格", "代码", "支撑材料"]
    for f in guanjian_wenjian:
        fpath = os.path.join(root_dir, f)
        if os.path.exists(fpath):
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                if size > 20 * 1024 * 1024:
                    print(f"  {RED}✗ {f} ({size_str}) - 超过20MB限制！{RESET}")
                else:
                    print(f"  {GREEN}✓ {f} ({size_str}){RESET}")
            else:
                file_count = len(os.listdir(fpath))
                print(f"  {GREEN}✓ {f}/ (文件夹, {file_count}个文件){RESET}")
        else:
            if f in ["论文.docx"]:
                print(f"  {YELLOW}○ {f} - 尚未生成（S6 步骤2完成后生成）{RESET}")
            else:
                print(f"  {YELLOW}○ {f} - 尚未创建{RESET}")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="数学建模论文全流程产物索引检查工具")
    parser.add_argument("--path", "-p", type=str, default=None, help="项目根目录路径（默认为脚本所在目录的上级）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息（含每个文件大小和修改时间）")
    parser.add_argument("--fix", "-f", action="store_true", help="自动创建缺失的文件夹")
    args = parser.parse_args()

    # 确定项目根目录
    if args.path:
        root_dir = os.path.abspath(args.path)
    else:
        # 默认为脚本所在目录的上级（scripts/../）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)

    if not os.path.isdir(root_dir):
        print(f"{RED}错误: 项目根目录不存在: {root_dir}{RESET}")
        sys.exit(1)

    jiancha_xiangmu(root_dir, verbose=args.verbose, fix=args.fix)


if __name__ == "__main__":
    main()
