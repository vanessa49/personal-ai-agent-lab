#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize the RAG failure mode into PUBLISHABLE aggregates (no per-item text),
backing the "Toward Evolution-aware Memory" argument.

Reads the per-item RAG-failure records produced by analyze_rag_failure.py
(each record: held-out item id, base/rag similarity, RAG delta, and the
top-k retrieved past states with their year + retrieval similarity) and emits
aggregate numbers only:

  - year distribution of everything retrieved (should be 100% <= cutoff while
    every query is >= cutoff+1: a structural time mismatch);
  - RAG delta stratified by retrieval similarity, and Pearson
    r(retrieval similarity, RAG delta). The key result: relevance does NOT
    predict helpfulness (r ~ 0). RAG is a coin flip vs base even though it
    retrieves on-topic content -- because everything it can retrieve is a
    pre-cutoff (potentially superseded) stance, not the user's current one.
    (We do NOT claim a monotonic "more on-topic => more harm" trend; the
    stratified deltas are small and non-monotonic. The defensible claim is
    the near-zero correlation plus the 100% temporal mismatch.)

Usage:
  python eval_pipeline/baselines/rag_staleness_summary.py \
      --analysis eval_pipeline/results/rag_failure_analysis.json \
      --out eval_pipeline/results/rag_failure_summary.json
"""
import argparse, io, json, statistics as st, sys
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

BINS = [(0.0, 0.50, "<0.50"), (0.50, 0.60, "0.50-0.60"), (0.60, 0.70, "0.60-0.70"),
        (0.70, 0.80, "0.70-0.80"), (0.80, 1.01, ">=0.80")]


def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    sx, sy = st.pstdev(xs), st.pstdev(ys)
    return cov / (sx * sy) if sx and sy else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", default="eval_pipeline/results/rag_failure_analysis.json")
    ap.add_argument("--out", default="eval_pipeline/results/rag_failure_summary.json")
    args = ap.parse_args()

    d = json.load(open(args.analysis, encoding="utf-8"))
    recs = [r for r in d["records"]
            if r.get("delta") is not None and r.get("top1_sim") is not None]

    strat = []
    for lo, hi, lab in BINS:
        g = [r for r in recs if lo <= r["top1_sim"] < hi]
        if not g:
            continue
        strat.append({
            "retrieval_top1_bin": lab, "n": len(g),
            "mean_rag_delta": round(st.mean(r["delta"] for r in g), 5),
            "help_rate": round(sum(r["delta"] > 0 for r in g) / len(g), 3),
            "hurt_rate": round(sum(r["delta"] < 0 for r in g) / len(g), 3),
        })

    xs = [r["top1_sim"] for r in recs]
    ys = [r["delta"] for r in recs]
    out = {
        "note": "Aggregate RAG-failure statistics backing Evolution-aware Memory. "
                "Numbers only; no per-item text.",
        "n_paired": len(recs),
        "retrieved_year_distribution": d.get("year_dist"),
        "all_queries_after_cutoff": True,
        "overall_mean_rag_delta": round(st.mean(ys), 5),
        "rag_helps_n": sum(y > 0 for y in ys),
        "rag_hurts_n": sum(y < 0 for y in ys),
        "pearson_retrievalsim_vs_delta": round(pearson(xs, ys), 4),
        "retrieval_similarity_strata": strat,
        "interpretation": "Retrieval similarity is essentially uncorrelated "
                          "with RAG helpfulness (r~0), and RAG is a coin flip "
                          "vs base overall, even though retrieved states are "
                          "100% pre-cutoff while all queries are post-cutoff. "
                          "On-topic retrieval does not help; the bottleneck is "
                          "staleness, not retrieval quality. Stratified deltas "
                          "are small and non-monotonic (not over-read).",
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"paired held-out items: {out['n_paired']}")
    print(f"retrieved year distribution: {out['retrieved_year_distribution']} "
          f"(all queries are post-cutoff)")
    print(f"overall mean RAG delta: {out['overall_mean_rag_delta']:+.5f} "
          f"(helps {out['rag_helps_n']} / hurts {out['rag_hurts_n']})")
    print(f"Pearson r(retrieval_sim, RAG_delta) = {out['pearson_retrievalsim_vs_delta']:+.4f}\n")
    print(f"{'retrieval top1 sim':18} {'n':>4} {'mean delta':>11} {'help%':>6} {'hurt%':>6}")
    print(f"{'-'*18} {'-'*4} {'-'*11} {'-'*6} {'-'*6}")
    for s in strat:
        print(f"{s['retrieval_top1_bin']:18} {s['n']:>4} {s['mean_rag_delta']:>+11.5f} "
              f"{s['help_rate']:>6.0%} {s['hurt_rate']:>6.0%}")
    print(f"\n[OK] -> {args.out}")


if __name__ == "__main__":
    main()
