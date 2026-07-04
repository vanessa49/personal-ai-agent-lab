#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-as-judge，第二评审（③）：对每条 held-out 项，给 judge 看 context + 用户真实续写(gold)
+ 三个匿名候选(base/qa/trajectory 打乱)，判"哪个候选最贴近真实续写"。→ 可规模化到全部项，
补足人工盲评 n 小的问题。再算 judge 与人工 40 条的一致性(收敛证据)。

隐私：judge 需读语料 → 用你的 config 密钥本地跑。**只上传聚合胜率 + 一致性**，逐项 judge
结果落私有文件。诚实边界：judge 测"像 gold"，人工测"像我"，二者是不同构念，收敛才算证据。

用法（需 config.py 里的 GEMINI 密钥）:
  python eval_pipeline/judge/llm_judge_pairwise.py \
     --blind-csv eval_pipeline/results/exp3_blind_open_full.csv \
     --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json \
     --out-private eval_pipeline/results/llm_judge_picks.json \
     --out-summary eval_pipeline/results/llm_judge_summary.json
  # 已有 judge 逐项结果后，算与人工一致：
  python eval_pipeline/judge/llm_judge_pairwise.py --agreement \
     --judge-picks eval_pipeline/results/llm_judge_picks.json \
     --blind-csv eval_pipeline/results/exp3_blind_open_full.csv \
     --out-summary eval_pipeline/results/llm_judge_summary.json
"""
import argparse, csv, json, random, sys, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1]))

JUDGE_PROMPT = """你在做一个匿名评审。下面是一段对话上下文，接着是这位作者**真实写下的下一条**（reference），以及三个候选续写（已匿名、随机排序）。

请判断：哪个候选在**思路走向、风格、对上下文的延续方式**上，最接近 reference（作者的真实下一步）？只看"最像同一个人接着写的那一条"，不是看谁写得更好或更长。

[上下文]
{context}

[作者真实的下一步 reference]
{gold}

[候选 1]
{c1}

[候选 2]
{c2}

[候选 3]
{c3}

只输出 JSON：{{"pick": 1|2|3, "reason": "一句话"}}"""


def read_csv(path):
    for enc in ("utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return list(csv.reader(open(path, encoding=enc, newline="")))
        except UnicodeError:
            continue
    raise SystemExit("cannot decode csv")


def col(hdr, name):
    return next((i for i, h in enumerate(hdr) if name in h), -1)


def load_blind(csv_path, key):
    """→ {sid: {context, cands:{model:text}, human_pick}}"""
    rows = read_csv(csv_path)
    hdr = rows[0]
    c_sid, c_ctx, c_opt, c_pick = (col(hdr, "sample_id"), col(hdr, "context"),
                                   col(hdr, "option"), col(hdr, "your_pick"))
    c_out = next((i for i, h in enumerate(hdr) if "候选" in h or "output" in h.lower()), 3)
    items, cur = {}, None
    for r in rows[1:]:
        if not r or all(not x.strip() for x in r):
            continue
        if r[c_sid].strip():
            cur = r[c_sid].strip()
            items[cur] = {"context": r[c_ctx].strip() if c_ctx >= 0 else "",
                          "cands": {}, "human_pick": None}
        lab = r[c_opt].strip() if c_opt < len(r) else ""
        if lab and cur:
            m = key.get(cur, {}).get(lab)
            if m:
                items[cur]["cands"][m] = r[c_out].strip() if c_out < len(r) else ""
                if r[c_pick].strip() in ("1", "1.0"):
                    items[cur]["human_pick"] = m
    return items


def load_gold(bench_path):
    b = json.load(open(bench_path, encoding="utf-8"))
    bs = b["samples"] if isinstance(b, dict) else b
    gold = {}
    for s in bs:
        g = (s.get("ground_truth") or s.get("gold") or s.get("answer")
             or s.get("target") or s.get("continuation") or "")
        gold[s["id"]] = g
    return gold


def kappa(a, b):
    """Cohen's kappa on paired categorical labels."""
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c)/n) * (b.count(c)/n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe != 1 else 1.0, round(po, 3)


def run_judge(args):
    from judge.llm_judge import _call_api, _parse_json_response  # noqa
    key = json.loads(Path(args.blind_csv + ".key.json").read_text(encoding="utf-8"))
    items = load_blind(args.blind_csv, key)
    gold = load_gold(args.benchmark)
    rng = random.Random(args.seed)
    picks = {}
    counts = collections.Counter()
    done = 0
    for sid, it in items.items():
        if sid not in gold or len(it["cands"]) < 3:
            continue
        models = ["base", "qa", "trajectory"]
        order = models[:]
        rng.shuffle(order)                       # anonymize position
        texts = [it["cands"].get(m, "") for m in order]
        prompt = JUDGE_PROMPT.format(context=it["context"][:2000], gold=gold[sid][:1200],
                                     c1=texts[0][:1200], c2=texts[1][:1200], c3=texts[2][:1200])
        try:
            raw = _call_api(prompt, args.backend)
            parsed = _parse_json_response(raw) or {}
            pick_idx = int(parsed.get("pick", 0)) - 1
        except Exception as e:
            print(f"  [skip {sid}] {e}")
            continue
        if 0 <= pick_idx < 3:
            picked_model = order[pick_idx]
            picks[sid] = picked_model
            counts[picked_model] += 1
            done += 1
        if done % 20 == 0:
            print(f"  judged {done} ...")
    Path(args.out_private).write_text(json.dumps(picks, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(counts.values())
    summary = {"note": "LLM-judge 'closest to gold' win counts, aggregate only.",
               "backend": args.backend, "n_judged": n,
               "counts": dict(counts),
               "rates": {m: round(counts[m]/n, 3) for m in counts} if n else {}}
    write_summary(args.out_summary, judge=summary)
    print(f"\njudged {n}: {dict(counts)}  -> {args.out_summary}")


def run_agreement(args):
    judge_picks = json.loads(Path(args.judge_picks).read_text(encoding="utf-8"))
    key = json.loads(Path(args.blind_csv + ".key.json").read_text(encoding="utf-8"))
    items = load_blind(args.blind_csv, key)
    a, b = [], []
    for sid, it in items.items():
        if it["human_pick"] and sid in judge_picks:
            a.append(it["human_pick"]); b.append(judge_picks[sid])
    if not a:
        print("no overlap between human picks and judge picks"); return
    k, po = kappa(a, b)
    agr = {"n_overlap": len(a), "percent_agreement": po, "cohens_kappa": k,
           "human_traj_rate": round(a.count("trajectory")/len(a), 3),
           "judge_traj_rate": round(b.count("trajectory")/len(b), 3)}
    write_summary(args.out_summary, agreement=agr)
    print(f"human vs judge on {len(a)} items: agreement={po}, kappa={k}")
    print(f"  human traj rate={agr['human_traj_rate']}  judge traj rate={agr['judge_traj_rate']}")


def write_summary(path, **kw):
    p = Path(path)
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    cur.update(kw)
    p.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blind-csv", required=True)
    ap.add_argument("--benchmark")
    ap.add_argument("--backend", default="gemini")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-private", default="eval_pipeline/results/llm_judge_picks.json")
    ap.add_argument("--out-summary", default="eval_pipeline/results/llm_judge_summary.json")
    ap.add_argument("--agreement", action="store_true", help="只算与人工一致（需 --judge-picks）")
    ap.add_argument("--judge-picks")
    args = ap.parse_args()
    if args.agreement:
        run_agreement(args)
    else:
        if not args.benchmark:
            raise SystemExit("--benchmark required for judging")
        run_judge(args)


if __name__ == "__main__":
    main()
