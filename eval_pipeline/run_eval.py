#!/usr/bin/env python3
# run_eval.py
"""
Personal AI Fine-tuning Evaluation Pipeline
用法: python run_eval.py [--quick] [--backend pollinations|deepseek] [--no-judge]

--quick:    只跑每类前3个，用于测试pipeline是否正常
--backend:  覆盖config.py中的JUDGE_BACKEND设置
--no-judge: 只收集模型回答，不调judge（省积分，先确认模型能跑）
"""

import json
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# 确保可以import同级模块
sys.path.insert(0, str(Path(__file__).parent))

from config import JUDGE_BACKEND, SAVE_RAW_RESPONSES
from models.model_runner import OllamaRunner
from judge.llm_judge import judge as llm_judge
from analysis.statistics import (
    compute_scores, summarize, compute_win_rate,
    print_paper_table, save_results
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="每类只跑3个，快速验证pipeline")
    parser.add_argument("--backend", choices=["pollinations", "deepseek"],
                        default=None, help="覆盖judge backend设置")
    parser.add_argument("--no-judge", action="store_true",
                        help="跳过judge，只收集模型回答")
    parser.add_argument("--base-model", default=None,
                        help="覆盖baseline模型名")
    parser.add_argument("--ft-model", default=None,
                        help="覆盖fine-tuned模型名")
    return parser.parse_args()


def load_test_cases(quick: bool = False) -> dict:
    with open("data/test_cases.json", "r", encoding="utf-8") as f:
        cases = json.load(f)
    if quick:
        return {cat: items[:3] for cat, items in cases.items()}
    return cases


def run_evaluation(args):
    print("\n" + "="*60)
    print("Personal AI Fine-tuning Evaluation Pipeline")
    print("="*60)

    # 加载配置
    from config import BASE_MODEL_NAME, FT_MODEL_NAME
    base_model_name = args.base_model or BASE_MODEL_NAME
    ft_model_name   = args.ft_model   or FT_MODEL_NAME
    backend = args.backend or JUDGE_BACKEND

    print(f"\n📦 Baseline model : {base_model_name}")
    print(f"📦 Fine-tuned model: {ft_model_name}")
    print(f"🧑‍⚖️  Judge backend   : {'SKIPPED' if args.no_judge else backend}")
    print(f"⚡ Mode            : {'QUICK (3 per category)' if args.quick else 'FULL (all cases)'}")

    # 加载模型
    print("\n🔄 初始化模型...")
    try:
        base_runner = OllamaRunner(base_model_name)
        ft_runner   = OllamaRunner(ft_model_name)
    except Exception as e:
        print(f"❌ 模型初始化失败: {e}")
        sys.exit(1)

    # 加载测试题
    cases = load_test_cases(quick=args.quick)
    total = sum(len(v) for v in cases.values())
    print(f"\n📝 测试题总数: {total} ({', '.join(f'{k}:{len(v)}' for k,v in cases.items())})")

    results = []
    done = 0

    # 主评估循环
    for category, items in cases.items():
        print(f"\n{'─'*50}")
        print(f"  Category: {category.upper()}")
        print(f"{'─'*50}")

        for item in items:
            done += 1
            item_id = item.get("id", f"{category}_{done}")
            question = item["input"]
            context  = item.get("context", None)

            print(f"\n[{done}/{total}] {item_id}")
            print(f"  Q: {question[:80]}{'...' if len(question) > 80 else ''}")

            # 生成回答
            print(f"  ⏳ Base model...")
            resp_base = base_runner.generate(question, context)
            print(f"  ⏳ FT model...")
            resp_ft   = ft_runner.generate(question, context)

            result = {
                "id": item_id,
                "category": category,
                "question": question,
                "context": context,
                "response_base": resp_base,
                "response_ft": resp_ft,
                "judge_result": None,
                "timestamp": datetime.now().isoformat()
            }

            # 调用judge
            if not args.no_judge:
                print(f"  🧑‍⚖️  Judging... (backend: {backend})")
                judge_result = llm_judge(
                    question=question,
                    response_base=resp_base,
                    response_ft=resp_ft,
                    category=category,
                    context=context,
                    backend=backend
                )
                result["judge_result"] = judge_result

                if judge_result:
                    scores = judge_result.get("scores", {})
                    winner = scores.get("overall_winner", "?")
                    a_avg = _avg_scores(scores.get("response_a", {}))
                    b_avg = _avg_scores(scores.get("response_b", {}))
                    print(f"  ✓ Base avg={a_avg:.2f} | FT avg={b_avg:.2f} | Winner: {winner}")
                else:
                    print(f"  ⚠️  Judge失败，跳过此条")

            results.append(result)

    # 统计
    print(f"\n{'='*60}")
    print("COMPUTING STATISTICS...")

    if not args.no_judge:
        aggregated = compute_scores(results)
        summary    = summarize(aggregated)
        win_rates  = compute_win_rate(results)
        print_paper_table(summary, win_rates)
    else:
        summary, win_rates = {}, {}
        print("（已跳过judge，无统计结果）")

    # 保存
    raw_path, summary_path = save_results(results, summary, win_rates)

    print(f"\n✅ 评估完成！共处理 {len(results)} 条测试")
    if args.no_judge:
        print("   提示：回答已保存，可以之后单独跑judge：")
        print(f"   python run_judge_only.py --input {raw_path}")

    return results, summary, win_rates


def _avg_scores(scores_dict: dict) -> float:
    """计算单个回答的平均分"""
    from config import DIMENSIONS
    vals = [scores_dict.get(d, 0) for d in
            ["iterative_reasoning", "correction_willingness",
             "trajectory_sense", "coherence"]]
    vals = [v for v in vals if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else 0.0


if __name__ == "__main__":
    args = parse_args()
    run_evaluation(args)
