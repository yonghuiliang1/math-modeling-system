#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题意对齐检查脚本 (topic_alignment_check.py)
方案C核心组件：对比当前步骤产物与题意契约，检查题意对齐度

用法:
  python topic_alignment_check.py --product <产物MD路径> --contract <题意契约路径> [--output <报告路径>] [--threshold 0.6]

题意契约支持两种格式:
  1. JSON格式 (problem_analysis.json) — P1步骤1产出
  2. MD格式 (题意锚定卡.md) — P2步骤0产出

检查维度:
  D1: 核心问题关键词覆盖率 (权重0.2)
  D2: 子问题逐问覆盖 (权重0.4)
  D3: 约束红线违背检测 (权重0.2)
  D4: 评价指标回应检测 (权重0.2)
"""

import argparse
import json
import re
import os
import sys
from datetime import datetime

try:
    import jieba
    jieba.setLogLevel(60)  # 静默 jieba 初始化日志
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# ============================================================
# 配置
# ============================================================
DEFAULT_THRESHOLD = 0.6
WEIGHTS = {"D1": 0.2, "D2": 0.4, "D3": 0.2, "D4": 0.2}

# D2 子问题描述关键词覆盖比例阈值
D2_DESC_COVERAGE_RATIO = 0.5

# D3 否定检测上下文窗口（字符数）
NEGATION_CONTEXT_WINDOW = 5

# D3 否定检测白名单：这些词中的"不"并非否定语义（如"不限于"表示包含、允许），
# 检测到否定词时若其属于白名单复合词，则不视为约束违背，避免误报。
NEGATION_WHITELIST = [
    "不限于", "不仅", "不足", "不一致", "不通过", "不满足",
    "不高于", "不低于", "不超过", "不大于", "不小于",
]

STOP_WORDS = {
    "的", "了", "和", "与", "或", "等", "中", "上", "下", "为", "在", "有",
    "本文", "本步", "该步", "当前", "步骤", "分析", "方法", "模型", "数据",
    "结果", "进行", "采用", "使用", "基于", "通过", "根据", "对于", "关于",
    "问题", "需要", "可以", "可能", "应该", "必须", "一个", "这种", "这样",
    "以及", "并且", "或者", "如果", "虽然", "但是", "因此", "所以", "然而",
    "说明", "给出", "得到", "完成", "确定", "选择", "考虑", "如下",
}

NEGATION_WORDS = ["不", "否", "放弃", "忽略", "跳过", "不使用", "不考虑",
                  "不采用", "剔除", "排除", "违反", "违背", "突破", "超出"]


def _is_whitelisted_negation(neg: str, context_before: str, context_after: str) -> bool:
    """判断否定词是否属于白名单复合词（如"不限于"、"不仅"等）。

    白名单词中的"不"并非否定语义（如"不限于"表示包含、允许），
    若否定词与相邻字符组成白名单词，则不视为约束违背，避免误报。
    """
    if neg != "不":
        return False
    window = context_before + context_after
    return any(wl in window for wl in NEGATION_WHITELIST)


# ============================================================
# 关键词提取
# ============================================================

def extract_keywords(text):
    """从文本中提取关键词（优先jieba分词，回退n-gram提取）"""
    keywords = set()

    if HAS_JIEBA:
        # 1. jieba 分词：过滤停用词、单字词、纯标点/空白
        for word in jieba.cut(text):
            word = word.strip()
            if not word:
                continue
            if word in STOP_WORDS:
                continue
            if len(word) < 2:
                continue
            if re.fullmatch(r'[\W_]+', word):
                continue
            keywords.add(word)
    else:
        # 降级方案：n-gram 提取（jieba 不可用时）
        for seg in re.findall(r'[\u4e00-\u9fa5]+', text):
            if len(seg) <= 4:
                if seg not in STOP_WORDS:
                    keywords.add(seg)
            else:
                for length in range(2, min(5, len(seg) + 1)):
                    for i in range(len(seg) - length + 1):
                        word = seg[i:i + length]
                        if word not in STOP_WORDS:
                            keywords.add(word)

    # 2. 英文词组（2字母以上）
    for en in re.findall(r'[A-Za-z]{2,}', text):
        keywords.add(en)

    # 3. 数字+中文组合
    for m in re.finditer(r'\d+[\u4e00-\u9fa5]{1,2}', text):
        keywords.add(m.group(0))

    # 4. 数字+英文组合
    for m in re.finditer(r'\d+[A-Za-z]+', text):
        keywords.add(m.group(0))

    return list(keywords)


# ============================================================
# 题意契约加载
# ============================================================

def load_contract_json(path):
    """加载JSON格式题意契约 (problem_analysis.json)"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] 读取题意契约 JSON 失败: {path} — {e}", file=sys.stderr)
        raise

    contract = {
        "core_problem": "",
        "sub_problems": [],
        "constraints": [],
        "metrics": [],
        "source_format": "json"
    }

    contract["core_problem"] = data.get("core_problem", "")

    for q in data.get("questions", []):
        contract["sub_problems"].append({
            "id": q.get("id", ""),
            "description": q.get("description", ""),
            "constraints": q.get("constraints", []),
            "metrics": q.get("metrics", [])
        })

    contract["constraints"] = data.get("constraints", [])
    contract["metrics"] = data.get("metrics", [])

    if not contract["core_problem"] and data.get("questions"):
        contract["core_problem"] = " ".join(
            q.get("description", "") for q in data["questions"])

    return contract


def load_contract_md(path):
    """加载MD格式题意锚定卡"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"[ERROR] 读取题意锚定卡失败: {path} — {e}", file=sys.stderr)
        raise

    contract = {
        "core_problem": "",
        "sub_problems": [],
        "constraints": [],
        "metrics": [],
        "source_format": "md"
    }

    sections = re.split(r'^##\s+', text, flags=re.MULTILINE)

    for section in sections:
        lines = section.strip().split('\n')
        header = lines[0].strip() if lines else ""
        body = '\n'.join(lines[1:]).strip()

        if "核心问题" in header:
            contract["core_problem"] = body.split('\n')[0].strip()
        elif "子问题" in header:
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    content = re.sub(r'^[-*]\s*', '', line)
                    id_match = re.match(
                        r'(问题\d+|Q\d+|[（(]\d+[)）])', content)
                    sub_id = id_match.group(1) if id_match else ""
                    contract["sub_problems"].append({
                        "id": sub_id,
                        "description": content,
                        "constraints": [],
                        "metrics": []
                    })
        elif "约束" in header:
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    contract["constraints"].append(
                        re.sub(r'^[-*]\s*', '', line))
        elif "指标" in header or "评价" in header:
            for line in body.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    contract["metrics"].append(
                        re.sub(r'^[-*]\s*', '', line))

    return contract


def load_contract(path):
    """加载题意契约（自动判断格式）"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        return load_contract_json(path)
    return load_contract_md(path)


def load_product(path):
    """加载步骤产物MD"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[ERROR] 读取步骤产物失败: {path} — {e}", file=sys.stderr)
        raise


# ============================================================
# 检查维度
# ============================================================

def check_d1_core_problem(contract, product_text):
    """D1: 核心问题关键词覆盖率"""
    core = contract["core_problem"]
    if not core:
        return {"score": 0.0, "details": {"error": "题意契约中无核心问题描述"}}

    keywords = extract_keywords(core)
    if not keywords:
        return {"score": 0.0, "details": {"error": "无法从核心问题中提取关键词"}}

    matched = [kw for kw in keywords if kw in product_text]
    unmatched = [kw for kw in keywords if kw not in product_text]
    score = len(matched) / len(keywords) if keywords else 0.0

    return {
        "score": round(score, 3),
        "details": {
            "core_problem": core,
            "total_keywords": len(keywords),
            "matched_count": len(matched),
            "matched": matched,
            "unmatched": unmatched
        }
    }


def check_d2_subproblem_coverage(contract, product_text):
    """D2: 子问题逐问覆盖"""
    subs = contract["sub_problems"]
    if not subs:
        return {"score": 0.0, "details": {"error": "题意契约中无子问题列表"}}

    covered = []
    uncovered = []

    for sub in subs:
        sub_id = sub.get("id", "")
        sub_desc = sub.get("description", "")

        id_found = bool(sub_id) and sub_id in product_text

        desc_found = False
        if not id_found and sub_desc:
            keywords = extract_keywords(sub_desc)
            if keywords:
                found_count = sum(1 for kw in keywords if kw in product_text)
                desc_found = found_count >= len(keywords) * D2_DESC_COVERAGE_RATIO

        label = sub_id or sub_desc[:20]
        if id_found or desc_found:
            covered.append(label)
        else:
            uncovered.append(label)

    score = len(covered) / len(subs) if subs else 0.0

    return {
        "score": round(score, 3),
        "details": {
            "total_subproblems": len(subs),
            "covered_count": len(covered),
            "covered": covered,
            "uncovered": uncovered
        }
    }


def check_d3_constraint_violation(contract, product_text):
    """D3: 约束红线违背检测"""
    all_constraints = list(contract["constraints"])
    for sub in contract["sub_problems"]:
        all_constraints.extend(sub.get("constraints", []))

    if not all_constraints:
        return {"score": 1.0, "details": {"info": "题意契约中无约束条件，D3默认通过"}}

    violated = []
    clean = []

    for constraint in all_constraints:
        constraint_text = constraint if isinstance(constraint, str) else (
            constraint.get("description", str(constraint))
            if isinstance(constraint, dict) else str(constraint)
        )

        keywords = extract_keywords(constraint_text)
        if not keywords:
            clean.append(constraint_text[:30])
            continue

        is_violated = False
        for kw in keywords:
            idx = product_text.find(kw)
            if idx < 0:
                continue
            context_before = product_text[max(0, idx - NEGATION_CONTEXT_WINDOW):idx]
            context_after = product_text[idx + len(kw):idx + len(kw) + NEGATION_CONTEXT_WINDOW]
            for neg in NEGATION_WORDS:
                if neg in context_before or neg in context_after:
                    # 否定词若属于白名单复合词（如"不限于""不仅"），不视为违背
                    if _is_whitelisted_negation(neg, context_before, context_after):
                        continue
                    is_violated = True
                    break
            if is_violated:
                break

        if is_violated:
            violated.append(constraint_text[:30])
        else:
            clean.append(constraint_text[:30])

    violation_rate = len(violated) / len(all_constraints) if all_constraints else 0.0
    score = round(1.0 - violation_rate, 3)

    return {
        "score": score,
        "details": {
            "total_constraints": len(all_constraints),
            "violated_count": len(violated),
            "violated": violated,
            "clean": clean
        }
    }


def check_d4_metric_response(contract, product_text):
    """D4: 评价指标回应检测"""
    all_metrics = list(contract["metrics"])
    for sub in contract["sub_problems"]:
        all_metrics.extend(sub.get("metrics", []))

    if not all_metrics:
        return {"score": 1.0, "details": {"info": "题意契约中无评价指标，D4默认通过"}}

    responded = []
    unresponded = []

    for metric in all_metrics:
        metric_text = metric if isinstance(metric, str) else (
            metric.get("name", metric.get("description", str(metric)))
            if isinstance(metric, dict) else str(metric)
        )

        if metric_text in product_text:
            responded.append(metric_text)
        else:
            keywords = extract_keywords(metric_text)
            found = any(kw in product_text for kw in keywords) if keywords else False
            if found:
                responded.append(metric_text)
            else:
                unresponded.append(metric_text)

    score = len(responded) / len(all_metrics) if all_metrics else 0.0

    return {
        "score": round(score, 3),
        "details": {
            "total_metrics": len(all_metrics),
            "responded_count": len(responded),
            "responded": responded,
            "unresponded": unresponded
        }
    }


# ============================================================
# 报告生成
# ============================================================

def generate_report(product_file, contract_file, threshold, checks):
    """生成对齐报告"""
    d1, d2, d3, d4 = checks["D1"], checks["D2"], checks["D3"], checks["D4"]

    overall = round(
        d1["score"] * WEIGHTS["D1"] +
        d2["score"] * WEIGHTS["D2"] +
        d3["score"] * WEIGHTS["D3"] +
        d4["score"] * WEIGHTS["D4"], 3
    )

    status = "PASS" if overall >= threshold else "FAIL"

    recommendations = []
    if d1["score"] < threshold and "unmatched" in d1.get("details", {}):
        rec = ", ".join(d1["details"]["unmatched"][:5])
        recommendations.append(f"D1核心问题覆盖不足，未覆盖关键词: {rec}")
    if d2["score"] < threshold and "uncovered" in d2.get("details", {}):
        rec = ", ".join(d2["details"]["uncovered"][:5])
        recommendations.append(f"D2子问题覆盖不足，未提及: {rec}")
    if d3["score"] < 1.0 and "violated" in d3.get("details", {}):
        rec = ", ".join(d3["details"]["violated"][:5])
        recommendations.append(f"D3约束违背风险: {rec}")
    if d4["score"] < threshold and "unresponded" in d4.get("details", {}):
        rec = ", ".join(d4["details"]["unresponded"][:5])
        recommendations.append(f"D4指标回应不足，未回应: {rec}")

    if not recommendations:
        recommendations.append(
            f"对齐分数 {overall} >= 阈值 {threshold}，门禁通过。")

    return {
        "check_time": datetime.now().isoformat(),
        "product_file": os.path.basename(product_file),
        "contract_file": os.path.basename(contract_file),
        "threshold": threshold,
        "overall_score": overall,
        "status": status,
        "weights": WEIGHTS,
        "dimensions": {
            "D1_core_problem": d1,
            "D2_subproblem_coverage": d2,
            "D3_constraint_violation": d3,
            "D4_metric_response": d4
        },
        "recommendation": " ".join(recommendations)
    }


def format_md_report(report):
    """格式化为人类可读的MD报告"""
    lines = [
        "# 题意对齐检查报告",
        "",
        f"**检查时间**: {report['check_time']}",
        f"**产物文件**: {report['product_file']}",
        f"**题意契约**: {report['contract_file']}",
        f"**对齐阈值**: {report['threshold']}",
        f"**总体对齐分数**: {report['overall_score']}",
        f"**门禁状态**: {'✅ PASS' if report['status'] == 'PASS' else '❌ FAIL'}",
        "",
        "## 各维度详情",
        ""
    ]

    dim_names = [
        ("D1_core_problem", "D1 核心问题覆盖"),
        ("D2_subproblem_coverage", "D2 子问题覆盖"),
        ("D3_constraint_violation", "D3 约束违背检测"),
        ("D4_metric_response", "D4 指标回应检测")
    ]

    for dim_key, dim_name in dim_names:
        dim = report["dimensions"][dim_key]
        lines.append(f"### {dim_name} (分数: {dim['score']})")
        for k, v in dim["details"].items():
            if isinstance(v, list):
                lines.append(f"- {k}: {', '.join(str(i) for i in v) if v else '无'}")
            else:
                lines.append(f"- {k}: {v}")
        lines.append("")

    lines.append("## 建议")
    lines.append(report["recommendation"])

    return '\n'.join(lines)


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='题意对齐检查脚本 — 对比步骤产物与题意契约，检查题意对齐度',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python topic_alignment_check.py \\
    --product 第二部分_步骤产物/步骤4_细化建模计划.md \\
    --contract S1_步骤产物/step1_problem_analysis.json \\
    --output paper_output/qa/topic_alignment_report.json \\
    --threshold 0.6

题意契约支持 JSON (problem_analysis.json) 和 MD (题意锚定卡.md) 两种格式。
        """
    )
    parser.add_argument('--product', required=True, help='当前步骤产物MD路径')
    parser.add_argument('--contract', required=True, help='题意契约路径（JSON或MD）')
    parser.add_argument('--output', default=None,
                        help='报告输出路径（JSON格式，默认输出到stdout）')
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help=f'对齐阈值（默认{DEFAULT_THRESHOLD}）')
    parser.add_argument('--md-report', default=None,
                        help='MD格式报告输出路径（可选）')

    args = parser.parse_args()

    # 加载题意契约
    try:
        contract = load_contract(args.contract)
    except Exception as e:
        print(f"[ERROR] 加载题意契约失败: {e}", file=sys.stderr)
        sys.exit(2)

    # 加载产物
    try:
        product_text = load_product(args.product)
    except Exception as e:
        print(f"[ERROR] 加载步骤产物失败: {e}", file=sys.stderr)
        sys.exit(2)

    # 执行检查
    checks = {
        "D1": check_d1_core_problem(contract, product_text),
        "D2": check_d2_subproblem_coverage(contract, product_text),
        "D3": check_d3_constraint_violation(contract, product_text),
        "D4": check_d4_metric_response(contract, product_text)
    }

    # 生成报告
    report = generate_report(args.product, args.contract, args.threshold, checks)

    # 输出 JSON
    report_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report_json)
        print(f"[INFO] JSON报告已写入: {args.output}")
    else:
        print(report_json)

    # 输出 MD 报告
    if args.md_report:
        md_dir = os.path.dirname(args.md_report)
        if md_dir:
            os.makedirs(md_dir, exist_ok=True)
        with open(args.md_report, 'w', encoding='utf-8') as f:
            f.write(format_md_report(report))
        print(f"[INFO] MD报告已写入: {args.md_report}")

    # 控制台摘要
    icon = "✅" if report["status"] == "PASS" else "❌"
    print(f"\n{icon} 题意对齐检查: {report['status']} "
          f"(分数: {report['overall_score']}, 阈值: {args.threshold})")
    print(f"   D1={checks['D1']['score']} D2={checks['D2']['score']} "
          f"D3={checks['D3']['score']} D4={checks['D4']['score']}")
    print(f"   {report['recommendation']}")

    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == '__main__':
    main()
