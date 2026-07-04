#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract the trajectory-win cases from the first-person blind-preference CSV
for qualitative coding: for every item where the (blind) user picked the
trajectory continuation, surface the shared context plus all three model
continuations (base / qa / trajectory) side by side, so an analyst can code
*why* the trajectory output was preferred.

Reads the PRIVATE blind CSV + decode key (personal text) and writes a local
working file. The per-item text never leaves the machine; only the resulting
code labels (sample_id -> reason, no text) and the aggregate frequency table
are publishable.

Usage:
  python eval_pipeline/qualitative_blind.py \
      --csv eval_pipeline/results/exp3_blind_open_full.csv \
      --out eval_pipeline/results/blind_traj_wins.json
"""
import csv, json, argparse
from pathlib import Path


def read_csv(path):
    for enc in ("utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return list(csv.reader(open(path, encoding=enc, newline="")))
        except UnicodeError:
            continue
    raise SystemExit("could not decode CSV")


def col(hdr, name):
    return next((i for i, h in enumerate(hdr) if name in h), -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--key", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    key = json.loads(Path(args.key or args.csv + ".key.json").read_text(encoding="utf-8"))
    rows = read_csv(args.csv)
    hdr = rows[0]
    c_sid = col(hdr, "sample_id")
    c_ctx = col(hdr, "context")
    c_opt = col(hdr, "option")
    c_out = next((i for i, h in enumerate(hdr) if "候选" in h or "output" in h.lower()), 3)
    c_pick = col(hdr, "your_pick")

    items, cur = {}, None
    for r in rows[1:]:
        if not r or all(not x.strip() for x in r):
            continue
        if r[c_sid].strip():
            cur = r[c_sid].strip()
            items[cur] = {"context": r[c_ctx].strip() if c_ctx >= 0 else "", "opts": {}, "pick": None}
        lab = r[c_opt].strip() if c_opt < len(r) else ""
        if lab and cur:
            model = key.get(cur, {}).get(lab)
            items[cur]["opts"][model] = r[c_out].strip() if c_out < len(r) else ""
            if r[c_pick].strip() in ("1", "1.0"):
                items[cur]["pick"] = model

    wins = {sid: it for sid, it in items.items() if it["pick"] == "trajectory"}
    Path(args.out).write_text(
        json.dumps({"n_total": len(items), "n_traj_wins": len(wins), "wins": wins},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total judged items: {len(items)}; trajectory wins: {len(wins)}")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
