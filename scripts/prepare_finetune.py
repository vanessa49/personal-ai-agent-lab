#!/usr/bin/env python3
"""
微调数据准备脚本

输入：
  /ai-agent/training/cognitive/cognitive_samples.jsonl  (认知切分样本)
  /ai-agent/training/dataset/samples.jsonl              (传统对话样本，可选)

输出：
  /ai-agent/training/finetune/dataset.json              (LLaMA-Factory alpaca 格式)
  /ai-agent/training/finetune/dataset_info.json         (数据集注册文件)
  /ai-agent/training/finetune/stats.json                (统计信息)

用法：
  python3 prepare_finetune.py [--min 150] [--max 600] [--cognitive-only]
"""
import json
import sys
import math
import argparse
from pathlib import Path
from datetime import datetime, timezone

COGNITIVE_SAMPLES = Path('/ai-agent/training/cognitive/cognitive_samples.jsonl')
DIALOG_SAMPLES    = Path('/ai-agent/training/dataset/samples.jsonl')
OUTPUT_DIR        = Path('/ai-agent/training/finetune')

SYSTEM_PROMPT = (
    "你是一个持续成长的个人 AI 助手。"
    "你的目标不是给出标准答案，而是跟随用户的思维方式，"
    "在已有思考的基础上继续推进、完善或修正。"
    "保持思考的连贯性，尊重用户的认知风格。"
)


def read_jsonl(path):
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8').strip().split('\n')
    result = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result


RECENCY_TAU_DAYS = 1460  # 时间衰减半衰期：4年（可通过 --tau 参数调整）
                         # tau=730(2年)：1年前→0.61，2年前→0.37
                         # tau=1460(4年)：1年前→0.78，2年前→0.61，3年前→0.47
                         # tau=9999：基本关闭衰减（等同于 --no-recency）


def get_recency_factor(timestamp_str, reference_date=None, tau_days=RECENCY_TAU_DAYS):
    if not timestamp_str:
        return 0.7
    try:
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ref = reference_date or datetime.now(timezone.utc)
        age_days = (ref - ts).days
        return math.exp(-max(age_days, 0) / tau_days)
    except Exception:
        return 0.7


def get_cognitive_epoch(timestamp_str):
    if not timestamp_str:
        return 'unknown'
    try:
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return f"epoch_{ts.year}"
    except Exception:
        return 'unknown'


def get_sample_weight(sample, use_recency=True, tau_days=RECENCY_TAU_DAYS):
    reasoning = sample.get('reasoning', '')
    depth = sample.get('iteration_depth', 0)

    if 'iteration_final' in reasoning:
        base = 2.5
    elif 'refines' in reasoning or 'contrasts' in reasoning:
        base = 2.0
    elif 'derives' in reasoning or 'clarifies' in reasoning:
        base = 1.5
    elif 'hypothesizes' in reasoning or 'speculates' in reasoning:
        base = 1.3
    elif 'restarts' in reasoning:
        base = 1.2
    else:
        base = 1.0

    if depth > 0:
        base *= (1 + math.log(depth + 1))

    if use_recency:
        recency = get_recency_factor(sample.get('timestamp'), tau_days=tau_days)
        base *= recency

    return round(min(base, 5.0), 3)


def cognitive_to_alpaca(sample, use_recency=True, tau_days=RECENCY_TAU_DAYS):
    relation = sample.get('reasoning', '').replace('认知推进 (', '').rstrip(')')
    relation_desc = {
        'follows':        '自然延续这个思路',
        'derives':        '从前提推导出下一步结论',
        'refines':        '对上文观点进行修正或完善',
        'contrasts':      '从不同角度重新审视上文判断',
        'responds':       '针对上文问题给出回应',
        'iteration_final':'综合讨论过程，给出最终修正后的判断',
        'hypothesizes':   '基于上文，提出假设性推理',
        'restarts':       '重新审视上文，从新的角度出发',
        'clarifies':      '对上文表述进行更精确的说明',
        'speculates':     '基于上文，给出推测性判断',
    }.get(relation, '继续推进思考')

    ts = sample.get('timestamp', '')
    return {
        'instruction': f"{relation_desc}：",
        'input': sample.get('input', ''),
        'output': sample.get('output', ''),
        'system': SYSTEM_PROMPT,
        'weight': get_sample_weight(sample, use_recency, tau_days),
        'timestamp': ts,
        'cognitive_epoch': get_cognitive_epoch(ts),
    }


def dialog_to_alpaca(sample):
    """传统对话样本 → alpaca 格式"""
    return {
        'instruction': sample.get('instruction', ''),
        'input': sample.get('input', ''),
        'output': sample.get('output', ''),
        'system': SYSTEM_PROMPT,
    }


def filter_quality(samples, min_output_len=30, max_output_len=4000):
    """过滤明显低质量样本"""
    filtered = []
    for s in samples:
        out = s.get('output', '')
        inp = s.get('input', '') + s.get('instruction', '')
        if len(out) < min_output_len:
            continue
        if len(out) > max_output_len:
            # 截断而不是丢弃
            s = dict(s)
            s['output'] = out[:max_output_len]
        if len(inp) < 5:
            continue
        filtered.append(s)
    return filtered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--min', type=int, default=150)
    parser.add_argument('--max', type=int, default=600)
    parser.add_argument('--cognitive-only', action='store_true')
    parser.add_argument('--dialog-only', action='store_true')
    parser.add_argument('--no-recency', action='store_true', help='关闭时间衰减权重')
    parser.add_argument('--tau', type=int, default=RECENCY_TAU_DAYS,
                        help=f'时间衰减半衰期（天），默认 {RECENCY_TAU_DAYS}（{RECENCY_TAU_DAYS//365}年）')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 读取样本
    cognitive_raw = read_jsonl(COGNITIVE_SAMPLES)
    dialog_raw    = read_jsonl(DIALOG_SAMPLES) if not args.cognitive_only else []

    print(f"认知切分样本: {len(cognitive_raw)} 条")
    print(f"传统对话样本: {len(dialog_raw)} 条")

    # 转换格式
    alpaca_samples = []
    cognitive_converted = []
    dialog_converted = []

    if not args.dialog_only:
        cognitive_converted = [cognitive_to_alpaca(s, use_recency=not args.no_recency, tau_days=args.tau) for s in cognitive_raw]
        cognitive_converted = filter_quality(cognitive_converted)
        alpaca_samples.extend(cognitive_converted)
        print(f"认知样本过滤后: {len(cognitive_converted)} 条")

    if not args.cognitive_only:
        dialog_converted = [dialog_to_alpaca(s) for s in dialog_raw]
        dialog_converted = filter_quality(dialog_converted)
        # 传统样本补充，不超过认知样本的 50%
        max_dialog = max(50, len(cognitive_converted) // 2) if not args.dialog_only else args.max
        dialog_converted = dialog_converted[:max_dialog]
        alpaca_samples.extend(dialog_converted)
        print(f"对话样本过滤后: {len(dialog_converted)} 条（上限 {max_dialog}）")

    total = len(alpaca_samples)
    print(f"\n合并后总计: {total} 条")

    if total < args.min:
        print(f"\n⚠️  样本数 {total} < 最低要求 {args.min}")
        print(f"   认知切分数据不足时，建议先跑更多对话导入：")
        print(f"   node scripts/cognitive_chunking.js /ai-agent/memory/conversations /ai-agent/training/cognitive")
        if total < 50:
            print(f"   样本太少，退出。")
            sys.exit(1)

    # 限制最大数量
    if total > args.max:
        # 优先保留认知样本
        alpaca_samples = alpaca_samples[:args.max]
        print(f"截取前 {args.max} 条")

    # 写出 dataset.json（LLaMA-Factory 格式）
    dataset_path = OUTPUT_DIR / 'dataset.json'
    dataset_path.write_text(
        json.dumps(alpaca_samples, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\n✓ 数据集: {dataset_path}  ({len(alpaca_samples)} 条)")

    # 写出 dataset_info.json（LLaMA-Factory 数据集注册）
    dataset_info = {
        "personal_cognitive": {
            "file_name": "dataset.json",
            "formatting": "alpaca",
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output",
                "system": "system",
                "weight": "weight"
            }
        }
    }
    info_path = OUTPUT_DIR / 'dataset_info.json'
    info_path.write_text(json.dumps(dataset_info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✓ 数据集注册: {info_path}")

    # 统计
    stats = {
        'total': len(alpaca_samples),
        'cognitive_count': len(cognitive_converted) if not args.dialog_only else 0,
        'dialog_count': len(dialog_converted) if not args.cognitive_only else 0,
        'avg_input_len': int(sum(len(s['input']) for s in alpaca_samples) / max(len(alpaca_samples), 1)),
        'avg_output_len': int(sum(len(s['output']) for s in alpaca_samples) / max(len(alpaca_samples), 1)),
        'weight_gt1_count': sum(1 for s in alpaca_samples if s.get('weight', 1.0) > 1.0),
        'weight_2_count': sum(1 for s in alpaca_samples if s.get('weight', 1.0) >= 2.0),
        'recency_enabled': not args.no_recency,
        'recency_tau_days': args.tau,
        'cognitive_epoch_dist': {},
        'created_at': datetime.now().isoformat(),
    }
    # epoch 分布
    for s in alpaca_samples:
        ep = s.get('cognitive_epoch', 'unknown')
        stats['cognitive_epoch_dist'][ep] = stats['cognitive_epoch_dist'].get(ep, 0) + 1

    stats_path = OUTPUT_DIR / 'stats.json'
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✓ 统计信息: {stats_path}")
    print(f"  weight > 1.0 的样本: {stats['weight_gt1_count']} 条")
    print(f"  weight ≥ 2.0 的样本: {stats['weight_2_count']} 条")
    print(f"  时间衰减: {'开启' if not args.no_recency else '关闭'}")
    print(f"  认知阶段分布: {stats['cognitive_epoch_dist']}")

    print(f"""
{'='*60}
数据准备完成，下一步在笔记本上执行：

  python scripts/run_finetune.py

或手动用 LLaMA-Factory：
  cd LLaMA-Factory
  # 把 {OUTPUT_DIR}/dataset.json 复制到 LLaMA-Factory/data/
  # 把 {OUTPUT_DIR}/dataset_info.json 内容合并到 LLaMA-Factory/data/dataset_info.json
  python src/train.py --config ../personal-ai-agent-lab/config/lora_train.yaml
{'='*60}
""")


if __name__ == '__main__':
    main()
