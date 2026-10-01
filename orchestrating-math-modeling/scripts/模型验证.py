#!/usr/bin/env python3
"""模型验证脚手架：生成 模型验证结论.md 模板 + 参数稳定性扰动测试辅助。

对应 S3 步骤3-5.5（模型验证），标准见《检验》文档：
第一部分四检（量纲边界/结果量级/参数稳定性/敏感性）
第二部分核心数字可回溯
第三部分误差/对比/情景三项检验

用法:
    python 模型验证.py --init --out <模型验证结论.md 路径>
    （稳定性测试函数供 S3 求解脚本调用：from 模型验证 import perturb_params, stability_test）
"""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """# 模型验证结论

> 步骤3-5.5 产出。标准：《检验》文档四检 + 可回溯 + 三项检验。

## 变更说明

- **版本**：v1.0
- **与上一版本差异**：首次产出
- **变更时间**：待补充

## 第一部分 · 四检（四项基础校验）

| 检验 | 结论 | 记录 |
|------|------|------|
| 1 量纲和边界 | 待补充 | 量纲是否统一、变量是否在合理区间、超界截断/异常说明 |
| 2 结果数量级 | 待补充 | 核心结果字段数量级核验、趋势增减是否符合题意 |
| 3 参数稳定性 | 待补充 | 关键参数 ±5%/±10% 扰动，结论是否稳定带内不剧烈跳变 |
| 4 敏感性 | 待补充 | 保留/删去关键假设两组对照，敏感程度定性量化 |

## 第二部分 · 核心数字可回溯

| 论文核心数字 | 支撑材料来源（代码/数据/脚本） | 可由 solve() 复现 |
|--------------|-------------------------------|-------------------|
| 待补充 | 待补充 | 待补充 |

## 第三部分 · 误差·对比·情景 三项检验

| 检验 | 结论 | 记录 |
|------|------|------|
| 1 误差分析 | 待补充 | 绝对/相对/均方误差 + 误差变化曲线 + 误差来源 + 对结论影响 |
| 2 对比实验 | 待补充 | 经典/简化模型同数据对照，横向证明优劣 |
| 3 情景分析 | 待补充 | 乐观/基准/保守多情景求解，验证结论稳健 |

## 验证总判定

待补充（全部通过 / 不通过项清单及返工计划）
"""


def perturb_params(params: dict, key: str, ratio: float) -> dict:
    """返回 key 乘以 (1 + ratio) 后的参数副本。"""
    out = dict(params)
    out[key] = params[key] * (1.0 + ratio)
    return out


def stability_test(
    solve_fn,
    base_params: dict,
    keys: list[str],
    ratios: tuple[float, ...] = (0.05, 0.10),
):
    """参数稳定性测试：对每个关键参数做 ±ratio 扰动，返回对比表（list of dict）。

    solve_fn(params) -> 标量 或 dict（结果指标）。
    每行: {"参数": key, "扰动": "+5%", "结果": 指标}
    """
    rows = []
    base = solve_fn(dict(base_params))
    for key in keys:
        for ratio in ratios:
            up = solve_fn(perturb_params(base_params, key, ratio))
            down = solve_fn(perturb_params(base_params, key, -ratio))
            rows.append({"参数": key, "扰动": f"+{ratio:.0%}", "结果": up})
            rows.append({"参数": key, "扰动": f"-{ratio:.0%}", "结果": down})
    return base, rows


def write_template(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(TEMPLATE, encoding="utf-8")
    print(f"[模型验证] 已生成模板: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="模型验证结论模板生成")
    parser.add_argument("--init", action="store_true", help="生成 模型验证结论.md 模板")
    parser.add_argument("--out", required=True, help="模板输出路径")
    args = parser.parse_args()
    if args.init:
        write_template(Path(args.out))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())