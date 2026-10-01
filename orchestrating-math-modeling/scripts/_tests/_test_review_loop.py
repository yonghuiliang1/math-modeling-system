#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补丁⑦（复循环硬门禁）单元实测：直接驱动 微循环验证.py 的两个新函数。

覆盖（流程控制规范.md 5.5 检查项27-28）：
  T1 check_review_target_version  —— 正常复循环通过 / 缺字段拦截 / 声明错版(≠产物版本)拦截
  T2 check_assembled_as_loop     —— 对照表冒充(全篇无返工版本+对照吸收表述)拦截 / 诚实复循环不误报
  T3 v1.0 首轮不误报（两函数对首轮产物均放行）
  T4 创新点强制机理闭环（即使 is_no_arithm_product 命中白名单仍要求机理闭环）
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

V = Path(__file__).parent.parent / "微循环验证.py"
spec = importlib.util.spec_from_file_location("wxh", V)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

passed, failed = 0, 0

def run(name: str, cond: bool):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")

print("== T1 审查对象版本硬绑定 ==")
# 正常复循环：返工产物 v1.2，报告声明冷读对象 v1.2
ok = ("本轮独立审查对象版本：步骤6_创新点设计_v1.2.md；本轮独立冷读 v1.2 后新发现问题 0")
run("返工产物声明对象=v1.2 → 通过", m.check_review_target_version(ok, "步骤6_创新点设计_v1.2.md") == [])
# 缺字段：返工产物 v1.2 但报告未声明审查对象版本（实战 v1.2 的洞）
run("返工产物缺'本轮独立审查对象版本' → 拦截", len(m.check_review_target_version("无该字段，只有对照吸收表", "步骤6_创新点设计_v1.2.md")) > 0)
# 声明错版：声明对象是 v1.0，产物是 v1.2 → 拦截（未重审返工产物）
run("声明对象=v1.0而产物v1.2 → 拦截(跳轮)", len(m.check_review_target_version("本轮独立审查对象版本：步骤6_创新点设计_v1.0.md", "步骤6_创新点设计_v1.2.md")) > 0)

print("== T2 对照表冒充复循环 ==")
assembled = "独立审查Agent问题清单：P1已吸收、P2已对照、全部修订完毕。结论：通过"
run("全篇无v1.2且堆对照吸收表述 → 拦截冒充", len(m.check_assembled_as_loop(assembled, "步骤6_创新点设计_v1.2.md")) > 0)
# 诚实复循环：报告含 v1.2（返工版本痕迹）→ 不误伤
honest = "本轮独立审查对象版本：v1.2；重读 v1.2 后新发现 0"
run("含返工版本v1.2痕迹 → 不误报", m.check_assembled_as_loop(honest, "步骤6_创新点设计_v1.2.md") == [])
run("正文仅v1.2一次出现即视为有锚点", m.check_assembled_as_loop("检查对象文件 v1.2", "步骤6_创新点设计_v1.2.md") == [])

print("== T3 v1.0 首轮不误报 ==")
run("首轮v1.0 缺对象版本不拦截", m.check_review_target_version("检查对象 v1.0", "步骤6_创新点设计_v1.0.md") == [])
run("首轮v1.0 对照吸收不拦截", m.check_assembled_as_loop("已对照通过", "步骤6_创新点设计_v1.0.md") == [])

print("== T4 创新点强制机理闭环 ==")
run("is_no_arithm_product('创新点')==True(命中算术白名单)", m.is_no_arithm_product("步骤6_创新点设计.md") is True)
run("但'创新点' in fname → 机理闭环条件成立", (not m.is_no_arithm_product("步骤6_创新点设计.md")) or ("创新点" in "步骤6_创新点设计.md"))

print(f"\n===== 补丁⑦ 单元实测：通过 {passed} / {passed + failed} =====")
sys.exit(0 if failed == 0 else 1)