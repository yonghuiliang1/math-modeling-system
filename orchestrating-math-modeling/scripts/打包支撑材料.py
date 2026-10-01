#!/usr/bin/env python3
"""支撑材料真打包：原样复制 S3_步骤产物 压缩为 zip，并冒烟运行求解脚本验证可复现。

用法:
    python 打包支撑材料.py --dir <项目根目录> [--out <输出zip路径>]

流程:
    1. 校验支撑材料根目录结构（代码/ 图片/ 表格/ + 代码/config.py）
    2. 原样复制到临时目录（不重组、不改名、不移动）
    3. 冒烟运行 问题X_求解.py，产出 冒烟运行.log（随包 + 留在源目录）
    4. 压缩为 zip
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


REQUIRED_SUBDIRS = ["代码", "图片", "表格"]


def build_structure_report(src_root: Path) -> tuple[list[str], bool]:
    report = []
    ok = True
    for sub in REQUIRED_SUBDIRS:
        p = src_root / sub
        if p.is_dir():
            report.append(f"[结构] {sub}/ 存在")
        else:
            report.append(f"[结构] 缺失 {sub}/")
            ok = False
    config = src_root / "代码" / "config.py"
    if config.exists():
        report.append("[结构] 代码/config.py 存在")
    else:
        report.append("[结构] 缺失 代码/config.py（路径基准唯一真相源）")
        ok = False
    return report, ok


def find_solve_scripts(code_dir: Path) -> list[Path]:
    return sorted(code_dir.glob("问题*_求解.py"))


def smoke_run(work_root: Path, code_dir: Path) -> tuple[str, bool]:
    scripts = find_solve_scripts(code_dir)
    lines = []
    if not scripts:
        lines.append("[冒烟] 未找到 问题*_求解.py，跳过，仅做结构校验")
        return "\n".join(lines), False
    target = scripts[0]
    cmd = f"{sys.executable} \"{target.name}\""
    lines.append(f"[冒烟] 工作目录: {code_dir}")
    lines.append(f"[冒烟] 执行: {cmd}")
    try:
        proc = subprocess.run(
            [sys.executable, str(target)],
            cwd=str(code_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        lines.append(f"[冒烟] 退出码: {proc.returncode}")
        if proc.stdout:
            lines.append("[冒烟] stdout:")
            lines.append(proc.stdout.rstrip())
        if proc.stderr:
            lines.append("[冒烟] stderr:")
            lines.append(proc.stderr.rstrip())
        return "\n".join(lines), proc.returncode == 0
    except subprocess.TimeoutExpired:
        lines.append("[冒烟] 超时（600s）")
        return "\n".join(lines), False


def main() -> int:
    parser = argparse.ArgumentParser(description="打包支撑材料并冒烟运行")
    parser.add_argument("--dir", required=True, help="项目根目录")
    parser.add_argument("--out", default=None, help="输出 zip 路径（默认 <项目根目录>/支撑材料.zip）")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    src_root = root / "S3_步骤产物"
    if not src_root.is_dir():
        print(f"[错误] 找不到支撑材料根目录: {src_root}")
        return 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [f"冒烟运行日志（生成时间 {now}）", "=" * 50]

    struct_report, struct_ok = build_structure_report(src_root)
    report_lines.extend(struct_report)
    if not struct_ok:
        report_lines.append("[结论] 结构校验未通过，禁止打包；请先按 产物规范.md 一.5 补齐目录")
        log_text = "\n".join(report_lines)
        (src_root / "冒烟运行.log").write_text(log_text, encoding="utf-8")
        print(log_text)
        return 1

    out_path = Path(args.out) if args.out else root / "支撑材料.zip"
    out_path = out_path.resolve()

    work_root = Path(tempfile.mkdtemp(prefix="zhichi_"))
    try:
        package_dir = work_root / "支撑材料"
        shutil.copytree(src_root, package_dir)

        code_dir = package_dir / "代码"
        smoke_text, smoke_ok = smoke_run(package_dir, code_dir)
        report_lines.append(smoke_text)
        report_lines.append("[结论] 冒烟运行通过" if smoke_ok else "[结论] 冒烟运行未通过")
        log_text = "\n".join(report_lines)

        (package_dir / "冒烟运行.log").write_text(log_text, encoding="utf-8")
        (src_root / "冒烟运行.log").write_text(log_text, encoding="utf-8")

        base = str(out_path)
        if base.lower().endswith(".zip"):
            base = base[:-4]
        shutil.make_archive(base, "zip", root_dir=str(package_dir))
        print(f"[打包] 已生成: {base}.zip")
        for line in report_lines:
            print(line)
        return 0 if (struct_ok and smoke_ok) else 1
    finally:
        shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())