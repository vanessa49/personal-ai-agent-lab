#!/usr/bin/env python3
"""
AB 测试脚本：微调前 vs 微调后模型对比（支持中英双语报告）

用法：
  python3 run_ab_test.py
  python3 run_ab_test.py --baseline qwen2.5:7b --finetuned qwen2.5:7b-lora-v1
  python3 run_ab_test.py --lang en          # 只生成英文报告
  python3 run_ab_test.py --lang zh          # 只生成中文报告
  python3 run_ab_test.py --lang both        # 中英双语（默认）
  python3 run_ab_test.py --test style
  python3 run_ab_test.py --test context
  python3 run_ab_test.py --test correction

多模型对比（同时跑 7B 和 9B）：
  python3 run_ab_test.py --baseline qwen2.5:7b --finetuned qwen2.5:7b-lora-v1
  python3 run_ab_test.py --baseline qwen2.5:9b --finetuned qwen2.5:9b-lora-v1
"""
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("缺少 requests 库，请运行：pip install requests")
    sys.exit(1)

OLLAMA_BASE = "http://192.168.0.198:11434"
OUTPUT_DIR  = Path("/ai-agent/training/eval")
TEMPERATURE = 0.7

# ── 双语文本 ──────────────────────────────────────────────────

I18N = {
    "zh": {
        "title": "AB 测试报告",
        "generated": "生成时间",
        "baseline_model": "Baseline 模型",
        "finetuned_model": "Fine-tuned 模型",
        "ollama": "Ollama 地址",
        "test1_title": "测试1：风格测试",
        "test2_title": "测试2：多轮上下文测试",
        "test3_title": "测试3：修正测试",
        "baseline_answer": "Baseline 回答",
        "finetuned_answer": "Fine-tuned 回答",
        "round3_note": "（仅记录第3轮，这是关键判断点）",
        "comparison": "对比观察",
        "summary": "总结",
        "table_test": "测试",
        "table_baseline": "Baseline",
        "table_finetuned": "Fine-tuned",
        "table_direction": "改善方向",
        "overall": "整体判断",
        "overall_note": "（请人工填写：pass / partial / fail）",
        "eval_notes": "评估维度说明",
        "style_note": "风格：是否有倾向性判断，结构是否接近「问题识别→权衡→建议」",
        "context_note": "上下文：第3轮是否正确引用「维护成本」而不是重新猜测",
        "correction_note": "修正：是否主动指出「样本质量比数量更重要」并给出具体理由",
        "test_names": {"style": "风格", "context": "上下文", "correction": "修正"},
        "comparison_prompt": """以下是同一个问题的两个模型回答。

Baseline 回答：
{baseline}

Fine-tuned 回答：
{finetuned}

请从以下角度简要对比（每点2-3句话）：
1. 回答结构是否有差异
2. 是否有主动分析或判断倾向
3. 哪个更像一个有自己立场的思考者

保持客观，不要偏袒任何一方。""",
    },
    "en": {
        "title": "AB Test Report",
        "generated": "Generated",
        "baseline_model": "Baseline Model",
        "finetuned_model": "Fine-tuned Model",
        "ollama": "Ollama Endpoint",
        "test1_title": "Test 1: Style Test",
        "test2_title": "Test 2: Multi-turn Context Test",
        "test3_title": "Test 3: Correction Test",
        "baseline_answer": "Baseline Response",
        "finetuned_answer": "Fine-tuned Response",
        "round3_note": "(Only Round 3 is recorded — this is the key evaluation point)",
        "comparison": "Comparative Observation",
        "summary": "Summary",
        "table_test": "Test",
        "table_baseline": "Baseline",
        "table_finetuned": "Fine-tuned",
        "table_direction": "Improvement Direction",
        "overall": "Overall Verdict",
        "overall_note": "(Fill in manually: pass / partial / fail)",
        "eval_notes": "Evaluation Criteria",
        "style_note": "Style: Does the response show a clear stance? Does it follow the pattern: problem identification → trade-off analysis → recommendation?",
        "context_note": "Context: Does Round 3 correctly reference 'maintenance cost' from Round 1 without re-prompting?",
        "correction_note": "Correction: Does the model proactively challenge the flawed assumption (quality > quantity) with specific reasoning?",
        "test_names": {"style": "Style", "context": "Context", "correction": "Correction"},
        "comparison_prompt": """Below are two model responses to the same question.

Baseline response:
{baseline}

Fine-tuned response:
{finetuned}

Please compare them briefly on the following dimensions (2-3 sentences each):
1. Structural differences in the responses
2. Presence of proactive analysis or opinionated stance
3. Which one reads more like a thinker with their own perspective

Be objective and do not favor either response.""",
    }
}

# 测试问题（中文，模型用中文回答）
TEST_QUESTIONS = {
    "style": "我在考虑把 Qdrant 从当前的 curl 调用方式改成直接集成进 OpenClaw 的 memory 层。你怎么看？",
    "context_r1": "我觉得 NAS 部署 AI 最大的挑战不是性能，而是长期维护成本。",
    "context_r2": "顺便问一下，bge-m3 和 bge-large 在中文语义检索上有什么区别？",
    "context_r3": "回到刚才的话题——基于你理解的那个挑战，有什么具体建议？",
    "correction": "我觉得训练数据越多越好，所以我打算把所有 1498 条样本全部用上，不做任何筛选，直接跑微调。",
}


# ── Ollama API ────────────────────────────────────────────────

def call_model(model_name, messages, base_url=OLLAMA_BASE):
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {"temperature": TEMPERATURE}
            },
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        print(f"  ✗ 无法连接 Ollama：{base_url}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 404:
            print(f"  ✗ 模型不存在：{model_name}")
            print(f"    请先运行：ollama pull {model_name}")
            sys.exit(1)
        raise


def check_model_exists(model_name, base_url=OLLAMA_BASE):
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=10)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(model_name in m or m.startswith(model_name) for m in models)
    except Exception:
        return False


# ── 三个测试用例 ──────────────────────────────────────────────

def test_style(model_name):
    messages = [{"role": "user", "content": TEST_QUESTIONS["style"]}]
    print(f"    调用 {model_name}...", end=" ", flush=True)
    answer = call_model(model_name, messages)
    print("完成")
    return {"messages": messages, "answer": answer}


def test_context(model_name):
    messages = []

    messages.append({"role": "user", "content": TEST_QUESTIONS["context_r1"]})
    print(f"    第1轮 {model_name}...", end=" ", flush=True)
    r1 = call_model(model_name, messages)
    print("完成")
    messages.append({"role": "assistant", "content": r1})

    messages.append({"role": "user", "content": TEST_QUESTIONS["context_r2"]})
    print(f"    第2轮 {model_name}...", end=" ", flush=True)
    r2 = call_model(model_name, messages)
    print("完成")
    messages.append({"role": "assistant", "content": r2})

    messages.append({"role": "user", "content": TEST_QUESTIONS["context_r3"]})
    print(f"    第3轮 {model_name}...", end=" ", flush=True)
    r3 = call_model(model_name, messages)
    print("完成")

    return {"messages": messages, "r1": r1, "r2": r2, "answer": r3}


def test_correction(model_name):
    messages = [{"role": "user", "content": TEST_QUESTIONS["correction"]}]
    print(f"    调用 {model_name}...", end=" ", flush=True)
    answer = call_model(model_name, messages)
    print("完成")
    return {"messages": messages, "answer": answer}


# ── 自动生成对比摘要 ──────────────────────────────────────────

def generate_comparison(baseline_answer, finetuned_answer, judge_model, lang="zh"):
    t = I18N[lang]
    prompt = t["comparison_prompt"].format(
        baseline=baseline_answer,
        finetuned=finetuned_answer
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        return call_model(judge_model, messages)
    except Exception as e:
        return f"(Auto-comparison failed: {e})"


# ── 报告生成 ──────────────────────────────────────────────────

def build_report(results, baseline_model, finetuned_model, timestamp, lang="zh"):
    t = I18N[lang]
    lines = []
    lines.append(f"# {t['title']}")
    lines.append("")
    lines.append(f"{t['generated']}: {timestamp}")
    lines.append(f"{t['baseline_model']}: {baseline_model}")
    lines.append(f"{t['finetuned_model']}: {finetuned_model}")
    lines.append(f"{t['ollama']}: {OLLAMA_BASE}")
    lines.append("")
    lines.append("---")

    test_titles = {
        "style":      t["test1_title"],
        "context":    t["test2_title"],
        "correction": t["test3_title"],
    }

    for test in results["tests"]:
        lines.append("")
        lines.append(f"## {test_titles.get(test['name'], test['name'])}")
        lines.append("")

        if test["name"] == "context":
            lines.append(f"### {t['baseline_answer']} {t['round3_note']}")
            lines.append("")
            lines.append(test["baseline"]["answer"])
            lines.append("")
            lines.append(f"### {t['finetuned_answer']} {t['round3_note']}")
            lines.append("")
            lines.append(test["finetuned"]["answer"])
        else:
            lines.append(f"### {t['baseline_answer']}")
            lines.append("")
            lines.append(test["baseline"]["answer"])
            lines.append("")
            lines.append(f"### {t['finetuned_answer']}")
            lines.append("")
            lines.append(test["finetuned"]["answer"])

        lines.append("")
        lines.append(f"### {t['comparison']}")
        lines.append("")
        # 对比摘要用对应语言生成
        comp_key = f"comparison_{lang}"
        lines.append(test.get(comp_key, test.get("comparison", "")))
        lines.append("")
        lines.append("---")

    # 总结表格
    lines.append("")
    lines.append(f"## {t['summary']}")
    lines.append("")
    lines.append(f"| {t['table_test']} | {t['table_baseline']} | {t['table_finetuned']} | {t['table_direction']} |")
    lines.append("|------|----------|------------|----------|")
    for test in results["tests"]:
        short = t["test_names"].get(test["name"], test["name"])
        lines.append(f"| {short} | - | - | - |")
    lines.append("")
    lines.append(f"**{t['overall']}**: {t['overall_note']}")
    lines.append("")
    lines.append(f"> {t['eval_notes']}:")
    lines.append(f"> - {t['style_note']}")
    lines.append(f"> - {t['context_note']}")
    lines.append(f"> - {t['correction_note']}")

    return "\n".join(lines)


# ── 主程序 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline",  default="qwen2.5:7b",
                        help="Baseline 模型名（未微调）")
    parser.add_argument("--finetuned", default="qwen2.5:7b-lora-v1",
                        help="微调后模型名")
    parser.add_argument("--ollama",    default=OLLAMA_BASE,
                        help="Ollama 地址")
    parser.add_argument("--test",      choices=["style", "context", "correction"],
                        help="只跑某一个测试")
    parser.add_argument("--lang",      choices=["zh", "en", "both"], default="both",
                        help="报告语言：zh/en/both（默认 both）")
    args = parser.parse_args()

    global OLLAMA_BASE
    OLLAMA_BASE = args.ollama

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str  = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 从模型名推断版本标签（用于文件名）
    model_tag = args.finetuned.replace(":", "_").replace("/", "_")

    print(f"\nAB 测试开始")
    print(f"  Baseline:   {args.baseline}")
    print(f"  Fine-tuned: {args.finetuned}")
    print(f"  Ollama:     {OLLAMA_BASE}")
    print(f"  语言:       {args.lang}")
    print()

    # 检查模型
    print("检查模型...")
    for model in [args.baseline, args.finetuned]:
        if check_model_exists(model, OLLAMA_BASE):
            print(f"  ✓ {model}")
        else:
            print(f"  ✗ {model} 不存在")
            print(f"    请先运行：ollama pull {model}")
            sys.exit(1)
    print()

    all_tests = [
        ("style",      test_style),
        ("context",    test_context),
        ("correction", test_correction),
    ]
    if args.test:
        all_tests = [t for t in all_tests if t[0] == args.test]

    results = {"tests": [], "meta": {
        "baseline": args.baseline,
        "finetuned": args.finetuned,
        "timestamp": timestamp,
        "ollama": OLLAMA_BASE,
    }}

    langs_to_gen = ["zh", "en"] if args.lang == "both" else [args.lang]

    for test_name, test_fn in all_tests:
        print(f"── {I18N['zh']['test_names'][test_name]} / {I18N['en']['test_names'][test_name]} ──")

        print(f"  Baseline:")
        baseline_result = test_fn(args.baseline)

        print(f"  Fine-tuned:")
        finetuned_result = test_fn(args.finetuned)

        test_entry = {
            "name": test_name,
            "baseline": baseline_result,
            "finetuned": finetuned_result,
        }

        # 为每种语言生成对比摘要
        for lang in langs_to_gen:
            print(f"  生成对比摘要（{lang}）...")
            comp = generate_comparison(
                baseline_result["answer"],
                finetuned_result["answer"],
                args.baseline,
                lang=lang
            )
            test_entry[f"comparison_{lang}"] = comp
        # 默认 comparison 字段用中文
        test_entry["comparison"] = test_entry.get("comparison_zh", test_entry.get("comparison_en", ""))

        results["tests"].append(test_entry)
        print()

    # 写原始数据
    raw_path = OUTPUT_DIR / "ab_test_raw.json"
    raw_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 原始数据: {raw_path}")

    # 写报告（按语言）
    for lang in langs_to_gen:
        report = build_report(results, args.baseline, args.finetuned, timestamp, lang)
        suffix = f"_{lang}" if args.lang == "both" else ""
        report_path  = OUTPUT_DIR / f"ab_test_results{suffix}.md"
        report_dated = OUTPUT_DIR / f"ab_test_{model_tag}_{date_str}{suffix}.md"
        report_path.write_text(report, encoding="utf-8")
        report_dated.write_text(report, encoding="utf-8")
        print(f"✓ 报告（{lang}）: {report_path}")
        print(f"✓ 历史版本: {report_dated}")

    print(f"\n查看中文报告：cat {OUTPUT_DIR}/ab_test_results_zh.md")
    print(f"查看英文报告：cat {OUTPUT_DIR}/ab_test_results_en.md")


if __name__ == "__main__":
    main()
