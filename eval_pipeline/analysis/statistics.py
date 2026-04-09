# analysis/statistics.py
import json
import numpy as np
from pathlib import Path
from datetime import datetime


DIMENSIONS = ["iterative_reasoning", "correction_willingness",
              "trajectory_sense", "coherence"]


def compute_scores(results: list) -> dict:
    """
    从原始结果列表中提取并汇总分数。
    
    Returns:
        {
          "style": {
            "base": {"iterative_reasoning": [scores], ...},
            "ft":   {"iterative_reasoning": [scores], ...}
          },
          ...
        }
    """
    aggregated = {}

    for r in results:
        if not r.get("judge_result"):
            continue

        cat = r["category"]
        scores_raw = r["judge_result"].get("scores", {})

        if cat not in aggregated:
            aggregated[cat] = {
                "base": {d: [] for d in DIMENSIONS},
                "ft":   {d: [] for d in DIMENSIONS}
            }

        # response_a = base, response_b = ft (由run_eval.py保证)
        for model_key, resp_key in [("base", "response_a"), ("ft", "response_b")]:
            resp_scores = scores_raw.get(resp_key, {})
            for dim in DIMENSIONS:
                val = resp_scores.get(dim)
                if isinstance(val, (int, float)):
                    aggregated[cat][model_key][dim].append(float(val))

    return aggregated


def summarize(aggregated: dict) -> dict:
    """计算均值和标准差"""
    summary = {}
    for cat, models in aggregated.items():
        summary[cat] = {}
        for model_name, dims in models.items():
            summary[cat][model_name] = {}
            for dim, vals in dims.items():
                if vals:
                    summary[cat][model_name][dim] = {
                        "mean": round(float(np.mean(vals)), 2),
                        "std":  round(float(np.std(vals)), 2),
                        "n":    len(vals)
                    }
    return summary


def compute_win_rate(results: list) -> dict:
    """计算ft相对于base的胜率"""
    wins = {}
    for r in results:
        if not r.get("judge_result"):
            continue
        cat = r["category"]
        winner = r["judge_result"].get("scores", {}).get("overall_winner", "")
        if cat not in wins:
            wins[cat] = {"ft_wins": 0, "base_wins": 0, "ties": 0, "total": 0}
        wins[cat]["total"] += 1
        if winner == "B":         # B = ft
            wins[cat]["ft_wins"] += 1
        elif winner == "A":       # A = base
            wins[cat]["base_wins"] += 1
        else:
            wins[cat]["ties"] += 1

    win_rates = {}
    for cat, w in wins.items():
        total = w["total"]
        if total > 0:
            win_rates[cat] = {
                "ft_win_rate": round(w["ft_wins"] / total, 3),
                "base_win_rate": round(w["base_wins"] / total, 3),
                "tie_rate": round(w["ties"] / total, 3),
                "total": total
            }
    return win_rates


def print_paper_table(summary: dict, win_rates: dict):
    """
    打印可直接放论文的结果表格
    """
    print("\n" + "="*65)
    print("EVALUATION RESULTS — LLM-as-Judge")
    print("="*65)

    # 主评分表
    print(f"\n{'Category':<14} {'Model':<8} ", end="")
    short = ["IterReas", "Correct", "Traj", "Coher"]
    for s in short:
        print(f"{s:>9}", end="")
    print()
    print("-"*65)

    dim_labels = list(zip(DIMENSIONS, short))

    for cat in ["style", "trajectory", "correction"]:
        if cat not in summary:
            continue
        for model_name in ["base", "ft"]:
            if model_name not in summary[cat]:
                continue
            label = f"{cat}/{model_name}"
            print(f"{label:<14} {model_name:<8} ", end="")
            for dim, _ in dim_labels:
                s = summary[cat][model_name].get(dim, {})
                if s:
                    print(f"{s['mean']:>7.2f}±{s['std']:.1f}", end="")
                else:
                    print(f"{'N/A':>9}", end="")
            print()
        print()

    # 胜率表
    print("\nWin Rates (FT vs Base, judged by LLM):")
    print(f"{'Category':<14} {'FT Wins':>10} {'Base Wins':>10} {'Ties':>8} {'Total':>7}")
    print("-"*50)
    for cat in ["style", "trajectory", "correction"]:
        if cat not in win_rates:
            continue
        w = win_rates[cat]
        print(f"{cat:<14} "
              f"{w['ft_win_rate']*100:>8.0f}%  "
              f"{w['base_win_rate']*100:>8.0f}%  "
              f"{w['tie_rate']*100:>6.0f}%  "
              f"{w['total']:>5}")

    print("\n" + "="*65)


def save_results(results: list, summary: dict, win_rates: dict,
                 output_dir: str = "results"):
    """保存所有结果到文件"""
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 原始结果
    raw_path = f"{output_dir}/raw_{timestamp}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 汇总统计
    summary_path = f"{output_dir}/summary_{timestamp}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "win_rates": win_rates,
            "timestamp": timestamp
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 原始结果: {raw_path}")
    print(f"✓ 汇总统计: {summary_path}")

    return raw_path, summary_path
