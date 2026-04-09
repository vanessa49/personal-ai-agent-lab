#!/usr/bin/env python3
# run_judge_only.py
"""
对已收集的模型回答单独跑judge。
用法: python run_judge_only.py --input results/raw_YYYYMMDD_HHMMSS.json
              [--backend pollinations|deepseek]

用途：
  1. 先用 --no-judge 收集所有回答（不花积分）
  2. 人工检查回答质量
  3. 再跑这个脚本只花judge的积分
"""

import json
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from judge.llm_judge import judge as llm_judge
from analysis.statistics import (
    compute_scores, summarize, compute_win_rate,
    print_paper_table, save_results
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="raw结果JSON文件路径")
    parser.add_argument("--backend", choices=["pollinations", "deepseek"],
                        default=None)
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"📂 加载 {len(results)} 条记录: {args.input}")

    # 只处理还没有judge结果的
    to_judge = [r for r in results if not r.get("judge_result")]
    already_done = len(results) - len(to_judge)
    print(f"  已有judge: {already_done} | 需要judge: {len(to_judge)}")

    for i, r in enumerate(to_judge, 1):
        print(f"\n[{i}/{len(to_judge)}] {r['id']} ({r['category']})")
        result = llm_judge(
            question=r["question"],
            response_base=r["response_base"],
            response_ft=r["response_ft"],
            category=r["category"],
            context=r.get("context"),
            backend=args.backend
        )
        r["judge_result"] = result
        if result:
            scores = result.get("scores", {})
            winner = scores.get("overall_winner", "?")
            print(f"  ✓ Winner: {winner}")

    # 统计并输出
    aggregated = compute_scores(results)
    summary    = summarize(aggregated)
    win_rates  = compute_win_rate(results)
    print_paper_table(summary, win_rates)
    save_results(results, summary, win_rates)


if __name__ == "__main__":
    main()
