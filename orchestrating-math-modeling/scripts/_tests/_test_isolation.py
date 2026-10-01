#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B 方案隔离校验单元实测：直接驱动 微循环验证.py 的三个隔离函数。

覆盖（补丁⑥ / 流程控制规范.md 5.5 检查项24-26）：
  C1  has_isolation_sign()        —— 直写签名识别
  C2  has_self_review_residue()   —— 产者自审残留（冷读不净）拦截
  C3  check_version_bind()        —— 检查报告版本号与本轮产物版本绑定
  C4  block_has_prefix_field()    —— 老字段名(独立审查Agent)与新闻段名(隔离*)兼容
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

print("== C1 直写签名识别 ==")
run("合规签名命中", m.has_isolation_sign("...含 `<!-- 由隔离检查Agent直写，未经生产转述 -->` 签名...") is True)
run("别名'由隔离检查者直写'命中", m.has_isolation_sign("由隔离检查者直写，未经生产转述") is True)
run("缺签名不命中", m.has_isolation_sign("这是普通检查报告，无签名") is False)
run("空内容不命中", m.has_isolation_sign("") is False)

print("== C2 自审残留（冷读不净）拦截 ==")
run("识别'我认为'", m.has_self_review_residue("检查者认为待商榷，但我认为没问题") is True)
run("识别'我方建模'", m.has_self_review_residue("我方建模思路如此") is True)
run("识别'根据我的思路'", m.has_self_review_residue("根据我的思路应当闭环") is True)
run("干净报告不误报", m.has_self_review_residue("隔离检查者冷读产物后，判定机理闭环0处未闭环") is False)

print("== C3 版本绑定 ==")
ok_fname = "步骤1_题目理解_v2.0.md"
run("版本一致→无问题", m.check_version_bind("本轮产物版本：步骤1_题目理解_v2.0.md", ok_fname) == [])
run("缺版本字段→报缺失", len(m.check_version_bind("无版本声明", ok_fname)) > 0)
run("版本漂移→报错", len(m.check_version_bind("本轮产物版本：步骤1_题目理解_v1.0.md", ok_fname)) > 0)

print("== C4 字段名兼容（老/新闻段） ==")
run("新闻段'隔离检查者复核'", m.block_has_prefix_field("隔离检查者复核：...", "复核") is True)
run("新闻段'隔离检查Agent问题清单'", m.block_has_prefix_field("隔离检查Agent问题清单：...", "问题清单") is True)
run("老字段'独立审查Agent优化建议'", m.block_has_prefix_field("独立审查Agent优化建议：...", "优化建议") is True)
run("非同段不误命中", m.block_has_prefix_field("自审优化建议：...", "优化建议") is False)

print(f"\n===== 隔离校验单元实测：通过 {passed} / {passed + failed} =====")
sys.exit(0 if failed == 0 else 1)