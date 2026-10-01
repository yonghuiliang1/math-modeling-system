#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补丁⑨（复检独立触发机制）单元实测。
覆盖：独立判决存在性（允许停止/缺行/无明确结论）、禁生产者代判（拦截/放行）、返工产物判定。
运行: D:\\phay\\python.exe _tests\\_test_independent_verdict.py
"""
import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mv", BASE / "微循环验证.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

passed = 0
failed = []

def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(f"{name} {detail}")

# --- 1. 独立判决：允许停止（✅）---
r = m.has_independent_verdict_marker("【独立判决】隔离复检者已冷读 v1.2，结论：✅ 无实质问题 → 允许停止", "x.md")
check("判决存在-允许停止通过", r == [], detail=str(r))

# --- 2. 独立判决：须返工（❌，判据字段存在即可，不判对错）---
r = m.has_independent_verdict_marker("【独立判决】隔离复检者已冷读 v1.2，结论：❌ 仍存在实质问题 → 须返工", "x.md")
check("判决存在-须返工通过", r == [], detail=str(r))

# --- 3. 缺【独立判决】→ 判独立复检未发生 ---
r = m.has_independent_verdict_marker("本轮产物版本：v1.2\n由隔离检查Agent直写", "x.md")
check("缺独立判决被拦截", len(r) == 1, detail=str(r))

# --- 4. 判决命令在但无明确结论 → 判决无效 ---
r = m.has_independent_verdict_marker("【独立判决】隔离复检者已冷读", "x.md")
check("判决无结论被拦截", len(r) == 1, detail=str(r))

# --- 5. 生产者自判终止（三连通过）→ 拦截 ---
r = m.check_producer_judgment("## 变更说明 v1.0→v1.1：修正口径，三连通过", "x.md")
check("生产者代判-三连通过被拦截", len(r) == 1, detail=str(r))

# --- 6. 生产者自判终止（复检通过）→ 拦截 ---
r = m.check_producer_judgment("## 变更说明 v1.0→v1.1：本轮复检通过", "x.md")
check("生产者代判-复检通过被拦截", len(r) == 1, detail=str(r))

# --- 7. 生产者无代判字样 → 放行 ---
r = m.check_producer_judgment("## 变更说明 v1.0→v1.1：修正口径标注，待隔离复检者冷读", "x.md")
check("生产者无代判放行", r == [], detail=str(r))

# --- 8. is_return_product 判定 ---
check("v1.0非返工产物", m.is_return_product("产物_v1.0.md") is False)
check("v1.1是返工产物", m.is_return_product("产物_v1.1.md") is True)
check("v1.2是返工产物", m.is_return_product("产物_v1.2.md") is True)

print(f"===== 补丁⑨ 单元实测：通过 {passed} / {passed + len(failed)} =====")
if failed:
    for f_ in failed:
        print("  FAIL:", f_)
    sys.exit(1)