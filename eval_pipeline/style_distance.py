#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风格嵌入距离（④，客观、零评审）：不看单条对不对，而看**一个模型的续写整体上像不像
这位用户自己的续写**。

做法：把该用户 held-out 真实续写(gold)嵌入取质心 = "用户风格分布中心"；再把每个模型
(base/qa/trajectory)在同一批 held-out 上生成的续写嵌入，算到该质心的平均距离。距离越小
= 输出分布越贴近用户本人的风格。与"下一步相似度(对不对)"正交——测的是风格保真度。

诚实控制：gold 也参与算质心会偏乐观，故用 **留一法**（算某条 gold 到质心时排除它自己），
并同时报"gold 自身到质心的平均距离"作为参照下界（模型不可能比用户自己更像用户）。

需要 Ollama(bge-m3)。逐项嵌入落私有缓存；只上传聚合(均值/CI/差)。

用法:
  python eval_pipeline/style_distance.py \
     --result eval_pipeline/results/exp3_heldout_v_smart8.json \
     --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json \
     --mode informat --out eval_pipeline/results/style_distance_summary.json
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, "eval_pipeline")
from fair_eval_common import embed, cosine, bootstrap_ci  # noqa: E402


def mean_vec(vs):
    n = len(vs); d = len(vs[0])
    return [sum(v[i] for v in vs) / n for i in range(d)]


def load_gold(bench):
    b = json.load(open(bench, encoding="utf-8"))
    bs = b["samples"] if isinstance(b, dict) else b
    g = {}
    for s in bs:
        g[s["id"]] = (s.get("ground_truth") or s.get("gold") or s.get("answer")
                      or s.get("target") or s.get("continuation") or "")
    return g


def get_text(rec, model, mode):
    d = rec.get(f"{model}__{mode}", {})
    return d.get("text", "") if isinstance(d, dict) else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--mode", default="informat")
    ap.add_argument("--cache", default="eval_pipeline/.style_embed_cache.json")
    ap.add_argument("--out", default="eval_pipeline/results/style_distance_summary.json")
    args = ap.parse_args()

    cache_path = Path(args.cache)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    def emb(t):
        t = (t or "").strip()
        if not t:
            return None
        if t in cache:
            return cache[t]
        e = embed(t)
        if e is not None:
            cache[t] = e
        return e

    d = json.load(open(args.result, encoding="utf-8"))
    recs = d["results"] if isinstance(d, dict) else d
    gold = load_gold(args.benchmark)

    ids = [r["id"] for r in recs if gold.get(r["id"], "").strip()]
    gold_emb = {i: emb(gold[i]) for i in ids}
    ids = [i for i in ids if gold_emb.get(i)]
    centroid = mean_vec([gold_emb[i] for i in ids])
    cache_path.write_text(json.dumps(cache), encoding="utf-8")

    # gold 参照下界：留一法（排除自身）到质心的距离
    n = len(ids)
    def loo_centroid_dist(i):
        v = gold_emb[i]
        c = [(centroid[k] * n - v[k]) / (n - 1) for k in range(len(v))]
        return 1 - cosine(v, c)
    gold_ref = [loo_centroid_dist(i) for i in ids]

    rec_by_id = {r["id"]: r for r in recs}
    out = {"note": "Style-embedding distance to the user's own continuation centroid. "
                   "Lower = closer to the user's style. Aggregate only.",
           "mode": args.mode, "n": n}
    out["gold_self_reference_loo"] = _stat(gold_ref)
    dist = {}
    for model in ["base", "qa", "trajectory"]:
        ds = {}
        for i in ids:
            e = emb(get_text(rec_by_id[i], model, args.mode))
            if e:
                ds[i] = 1 - cosine(e, centroid)
        dist[model] = ds
        out[model] = _stat(list(ds.values()))
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    # trajectory vs base 配对差（负 = trajectory 更贴近用户风格）
    paired = [dist["trajectory"][i] - dist["base"][i]
              for i in ids if i in dist["trajectory"] and i in dist["base"]]
    if paired:
        mu, lo, hi = bootstrap_ci(paired)
        out["trajectory_minus_base"] = {"mean": round(mu, 4),
                                        "ci95": [round(lo, 4), round(hi, 4)], "n": len(paired)}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[OK] -> {args.out}")


def _stat(v):
    if not v:
        return {"mean": None, "n": 0}
    mu, lo, hi = bootstrap_ci(v)
    return {"mean": round(mu, 4), "ci95": [round(lo, 4), round(hi, 4)], "n": len(v)}


if __name__ == "__main__":
    main()
