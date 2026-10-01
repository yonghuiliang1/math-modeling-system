#!/usr/bin/env python3
"""
CUMCM 图片映射构建脚本
基于 chinese-thesis-workbench 的 build_image_map.py，叠加 CUMCM 国赛图片标签自动扫描。

用法:
    # 方式1: 从 Markdown 文件自动扫描图片标签，匹配图片目录
    python build_image_map.py --source <论文.md> --image-dir <图片目录> --output <map.json>

    # 方式2: 从标签列表 JSON 构建（兼容原始脚本用法）
    python build_image_map.py --labels <labels.json> --image-dir <图片目录> --output <map.json>

    # 可选: 手动映射覆盖
    python build_image_map.py --source <论文.md> --image-dir <图片目录> --output <map.json> --manual <manual-map.json>

功能:
    1. 扫描 Markdown 中的图片占位符（[此处插入截图：XXX]）和图题（图X-Y 图题）
    2. 在指定图片目录中按标签名匹配 .png/.jpg/.jpeg 文件
    3. 支持手动映射覆盖
    4. 输出 JSON 格式的 image-map，供 generate_cumcm_docx.py --image-map 使用
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# ============================================================
# 1. Markdown 图片标签扫描
# ============================================================

# 图片占位符模式: [此处插入截图：标签] 或 [此处插入图片：标签]
PLACEHOLDER_RE = re.compile(r"^\[此处插入(?:截图|图片)：(.+?)\]$")

# 图题模式: 图X-Y 图题 或 图X.Y 图题
FIGURE_CAPTION_RE = re.compile(r"^图\s*(\d+)[-\.](\d+)\s+(.+)$")

# Mermaid 占位检测
MERMAID_PLACEHOLDER_RE = re.compile(r"^```mermaid$", re.M)


def scan_markdown_labels(md_path: Path) -> list[str]:
    """从 Markdown 文件中扫描所有图片标签。"""
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] 读取 Markdown 文件失败: {md_path} — {e}", file=sys.stderr)
        raise
    labels: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()

        # 图片占位符
        m = PLACEHOLDER_RE.match(stripped)
        if m:
            labels.append(m.group(1).strip())
            continue

        # 图题（作为图片标签）
        m = FIGURE_CAPTION_RE.match(stripped)
        if m:
            caption = stripped  # 完整图题作为标签
            labels.append(caption)

    return labels


def load_labels_json(labels_path: Path) -> list[str]:
    """从 labels.json 加载标签列表。"""
    try:
        data = json.loads(labels_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] 读取标签 JSON 文件失败: {labels_path} — {e}", file=sys.stderr)
        raise
    return data.get("labels", [])


# ============================================================
# 2. 图片文件匹配
# ============================================================

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]


def find_image(image_dir: Path, label: str) -> Path | None:
    """在图片目录中按标签名查找图片文件。"""
    # 清理标签中的特殊字符用于文件名匹配
    safe_label = re.sub(r'[<>:"/\\|?*]', "_", label)
    safe_label = safe_label.strip()

    for ext in IMAGE_EXTENSIONS:
        candidate = image_dir / f"{safe_label}{ext}"
        if candidate.exists():
            return candidate

    # 尝试模糊匹配：标签中包含的编号
    number_match = re.search(r"(\d+)[-\.](\d+)", label)
    if number_match:
        pattern = f"*{number_match.group(1)}-{number_match.group(2)}*"
        for ext in IMAGE_EXTENSIONS:
            for candidate in image_dir.glob(f"{pattern}{ext}"):
                return candidate
        # 也尝试 X.Y 格式
        pattern2 = f"*{number_match.group(1)}.{number_match.group(2)}*"
        for ext in IMAGE_EXTENSIONS:
            for candidate in image_dir.glob(f"{pattern2}{ext}"):
                return candidate

    return None


# ============================================================
# 3. 构建 image-map
# ============================================================

def build_image_map(
    labels: list[str],
    image_dir: Path,
    manual_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """构建图片映射字典。"""
    result: dict[str, str] = {}
    manual_map = manual_map or {}

    for label in labels:
        # 优先使用手动映射
        if label in manual_map:
            manual_target = Path(manual_map[label])
            if manual_target.exists():
                result[label] = str(manual_target)
                continue

        # 自动匹配
        found = find_image(image_dir, label)
        if found:
            result[label] = str(found)

    return result


# ============================================================
# 4. CLI
# ============================================================

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="CUMCM 图片映射构建脚本")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", type=Path, help="输入 Markdown 文件（自动扫描图片标签）")
    group.add_argument("--labels", type=Path, help="标签列表 JSON 文件")
    parser.add_argument("--image-dir", type=Path, required=True, help="图片目录")
    parser.add_argument("--output", type=Path, required=True, help="输出 image-map JSON")
    parser.add_argument("--manual", type=Path, default=None, help="手动映射 JSON（覆盖自动匹配）")

    args = parser.parse_args()

    # 加载标签
    if args.source:
        labels = scan_markdown_labels(args.source)
        print(f"[INFO] 从 {args.source} 扫描到 {len(labels)} 个图片标签")
    else:
        labels = load_labels_json(args.labels)
        print(f"[INFO] 从 {args.labels} 加载 {len(labels)} 个图片标签")

    # 加载手动映射
    manual_map = {}
    if args.manual and args.manual.exists():
        try:
            manual_map = json.loads(args.manual.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] 读取手动映射 JSON 失败: {args.manual} — {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[INFO] 加载 {len(manual_map)} 个手动映射")

    # 构建映射
    image_map = build_image_map(labels, args.image_dir, manual_map)

    # 统计
    matched = len(image_map)
    unmatched = len(labels) - matched
    print(f"[INFO] 匹配成功: {matched}, 未匹配: {unmatched}")

    if unmatched > 0:
        unmatched_labels = [l for l in labels if l not in image_map]
        print("[WARN] 未匹配的标签:")
        for label in unmatched_labels:
            print(f"  - {label}")

    # 输出
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(image_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] 图片映射已生成: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
