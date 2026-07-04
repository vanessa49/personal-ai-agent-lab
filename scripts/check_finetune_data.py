#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重训前自检（pre-flight）：在烧 GPU 之前，验证 reverse 重生成 + prepare_finetune
产出的训练数据没有踩过我们踩过的坑。任一 hard 检查失败 → 退出码 1，别开训。

检查项：
  1. [schema]      每条 alpaca 记录 instruction/input/output/system 非空，output 够长
  2. [reverse]     原始 cognitive_samples.jsonl 的截断样本呈 reverse 特征
                   （截断样本不再是 ~100% 以 role tag 开头 = 不是 forward/hard）
  3. [leakage]     temporal 切分零泄漏：train 侧对话时间戳全部 < cutoff 年
  4. [format]      mixed 模式下 v3/v5/free 各约 1/3
  5. [weight]      加权重采样确实生效（refines/contrasts/iteration_final 相对原始被放大）
  6. [scaffold]    v3/v5 记录 input 含 <required_relation>；free 记录不含
  7. [config]      lora_train.yaml 关键项 sane（train_on_prompt=false、量化、rank）

用法（regen + prepare_finetune 之后、训练之前）:
  python scripts/check_finetune_data.py \
    --dataset C:/ai-training/finetune/personal_cognitive_v_smart8.json \
    --raw-samples Y:/ai-agent/training/cognitive_smart/cognitive_samples.jsonl \
    --split-manifest eval_pipeline/data/split_manifest.json --split-type temporal \
    --expect-format mixed --expect-resample \
    --config config/lora_train.yaml --cutoff-year 2025
"""
import argparse, itertools, json, re, sys, io, collections
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

HI_W_RELATIONS = {"refines", "contrasts", "iteration_final"}
ROLE_RE = re.compile(r"^\[(user|assistant)\]")


class Checks:
    def __init__(self):
        self.fail = 0
        self.warn = 0

    def ok(self, name, msg=""):
        print(f"  [PASS] {name}{(' — ' + msg) if msg else ''}")

    def bad(self, name, msg):
        print(f"  [FAIL] {name} — {msg}")
        self.fail += 1

    def caution(self, name, msg):
        print(f"  [WARN] {name} — {msg}")
        self.warn += 1


def load_records(path):
    txt = Path(path).read_text(encoding="utf-8")
    try:
        d = json.loads(txt)
        return d if isinstance(d, list) else d.get("data", d.get("samples", []))
    except json.JSONDecodeError:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]


def check_schema(c, recs):
    empties = sum(1 for r in recs if not (r.get("output") or "").strip())
    short = sum(1 for r in recs if len((r.get("output") or "").strip()) < 20)
    nosys = sum(1 for r in recs if not (r.get("system") or "").strip())
    if empties:
        c.bad("schema", f"{empties} 条 output 为空")
    elif short > len(recs) * 0.05:
        c.caution("schema", f"{short} 条 output<20 字（{short/len(recs):.0%}）")
    else:
        c.ok("schema", f"{len(recs)} 条，output 均非空")
    if nosys:
        c.caution("schema", f"{nosys} 条缺 system（公平协议需要中文 system）")


def check_reverse(c, raw_path, n=8000):
    trunc = 0; role_start = 0
    with open(raw_path, encoding="utf-8") as fh:
        for line in itertools.islice(fh, 0, n):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ctx = (r.get("input", "") or "").split("<cognitive_state>")[0].strip()
            if len(ctx) < 950:
                continue
            trunc += 1
            if ROLE_RE.match(ctx):
                role_start += 1
    if trunc < 50:
        c.caution("reverse", f"截断样本太少({trunc})，无法判断策略——上下文大多没到上限")
        return
    mid = 1 - role_start / trunc
    if mid < 0.05:
        c.bad("reverse", f"截断样本 {role_start}/{trunc}({role_start/trunc:.0%}) 以 role tag 开头 "
                         f"= forward/hard，不是 reverse！漏了 --strategy=smart_sentence_reverse？")
    else:
        c.ok("reverse", f"截断样本 {mid:.0%} 以句子中部开头 = reverse 生效（{trunc} 条命中上限）")


def check_leakage(c, raw_path, manifest_path, split_type, cutoff_year, n=200000):
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    graphs = man.get("graphs", man)
    train_ids = {g for g, m in graphs.items() if m.get(split_type) == "train"}
    if not train_ids:
        c.caution("leakage", f"manifest 里没有 {split_type}/train 对话")
        return
    matched = crossed = 0
    with open(raw_path, encoding="utf-8") as fh:
        for line in itertools.islice(fh, 0, n):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("source") in train_ids:
                matched += 1
                yr = (r.get("timestamp", "") or "")[:4]
                if yr and yr.isdigit() and int(yr) >= cutoff_year:
                    crossed += 1
    if matched == 0:
        c.bad("leakage", "manifest 的 train 对话ID 与样本 source 对不上——manifest 没跟着 regen 重建？")
    elif crossed:
        c.bad("leakage", f"train 切分里有 {crossed} 条时间戳 >= {cutoff_year}（泄漏！）")
    else:
        c.ok("leakage", f"train 侧 {matched} 条样本时间戳全部 < {cutoff_year}（零泄漏）")


def check_format(c, recs, expect):
    fmts = collections.Counter(r.get("format", "?") for r in recs)
    if expect == "mixed":
        got = {k: fmts.get(k, 0) for k in ("v3", "v5", "free")}
        tot = sum(got.values())
        if tot == 0:
            c.bad("format", f"记录没有 format 字段或全非 v3/v5/free：{dict(fmts)}")
            return
        fracs = {k: v / tot for k, v in got.items()}
        if all(0.25 <= f <= 0.42 for f in fracs.values()):
            c.ok("format", f"mixed 均衡 {({k: round(v,2) for k,v in fracs.items()})}")
        else:
            c.caution("format", f"mixed 不均衡 {({k: round(v,2) for k,v in fracs.items()})}")
    else:
        c.ok("format", f"format 分布 {dict(fmts)}")


def check_weight(c, recs, expect_resample):
    """自足检查：重采样(有放回)会产生重复记录，且高 weight 记录应有更高的重复倍数。
    不依赖原始样本的 relation 字段。"""
    if not expect_resample:
        c.caution("weight", "未要求 resample——注意 LLaMA-Factory 会丢弃 weight 列，权重将无效")
        return
    key_cnt = collections.Counter()
    key_w = {}
    have_w = 0
    for r in recs:
        k = (r.get("instruction", ""), r.get("input", ""), r.get("output", ""))
        key_cnt[k] += 1
        if "weight" in r:
            have_w += 1
            key_w[k] = r.get("weight")
    uniq = len(key_cnt)
    dup_rate = 1 - uniq / len(recs) if recs else 0
    if dup_rate < 0.02:
        c.bad("weight", f"几乎无重复记录（唯一率 {uniq/len(recs):.0%}）——"
                        f"--weighted-resample 没生效？（LLaMA-Factory 会丢 weight 列，必须靠重采样）")
        return
    # 权重与重复倍数是否正相关（按 weight 放大的直接证据）
    if have_w >= len(recs) * 0.5 and len(key_w) > 10:
        xs = [key_w[k] for k in key_cnt if k in key_w]
        ys = [key_cnt[k] for k in key_cnt if k in key_w]
        try:
            import statistics as st
            mx, my = st.mean(xs), st.mean(ys)
            cov = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / len(xs)
            corr = cov / (st.pstdev(xs)*st.pstdev(ys)) if st.pstdev(xs) and st.pstdev(ys) else 0
        except Exception:
            corr = None
        if corr is not None and corr > 0.1:
            c.ok("weight", f"重复率 {dup_rate:.0%}，weight×重复倍数 corr={corr:+.2f}（按权重放大生效）")
        else:
            c.caution("weight", f"重复率 {dup_rate:.0%} 但 weight 与倍数相关弱(corr={corr})——"
                                f"确认是按 weight 重采样而非均匀")
    else:
        c.ok("weight", f"重复率 {dup_rate:.0%}（重采样已生效；无 weight 字段无法验相关性）")


def check_scaffold(c, recs):
    bad_struct = sum(1 for r in recs if r.get("format") in ("v3", "v5")
                     and "<required_relation>" not in (r.get("input") or ""))
    bad_free = sum(1 for r in recs if r.get("format") == "free"
                   and "<cognitive_state>" in (r.get("input") or ""))
    if bad_struct:
        c.bad("scaffold", f"{bad_struct} 条 v3/v5 记录 input 缺 <required_relation>")
    elif bad_free:
        c.bad("scaffold", f"{bad_free} 条 free 记录仍含 <cognitive_state>（应剥离）")
    else:
        c.ok("scaffold", "v3/v5 含 required_relation，free 已剥离")


def check_config(c, cfg_path):
    txt = Path(cfg_path).read_text(encoding="utf-8")
    def val(k):
        m = re.search(rf"^{k}\s*:\s*(\S+)", txt, re.M)
        return m.group(1) if m else None
    if val("train_on_prompt") not in ("false", "False"):
        c.bad("config", "train_on_prompt 应为 false（只训 output）")
    if val("quantization_bit") != "4":
        c.caution("config", f"quantization_bit={val('quantization_bit')}（8GB 卡建议 4）")
    if "weighted-resample" not in txt and "weighted_resample" not in txt and "resample" not in txt:
        c.caution("config", "配置没提 weighted-resample——确认数据 prep 时开了（weight 列会被丢弃）")
    c.ok("config", f"train_on_prompt={val('train_on_prompt')} rank={val('lora_rank')} "
                   f"quant={val('quantization_bit')} cutoff_len={val('cutoff_len')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="prepare_finetune 产出的 alpaca json")
    ap.add_argument("--raw-samples", help="cognitive_samples.jsonl（reverse/leakage/weight 检查）")
    ap.add_argument("--split-manifest")
    ap.add_argument("--split-type", choices=["temporal", "random"], default="temporal")
    ap.add_argument("--cutoff-year", type=int, default=2025, help="temporal 测试期起始年")
    ap.add_argument("--expect-format", default="mixed")
    ap.add_argument("--expect-resample", action="store_true")
    ap.add_argument("--config", help="lora_train.yaml")
    args = ap.parse_args()

    print("=" * 64)
    print("重训前自检 (pre-flight)")
    print("=" * 64)
    c = Checks()

    recs = load_records(args.dataset)
    print(f"数据集: {args.dataset}  ({len(recs)} 条)\n")
    check_schema(c, recs)
    check_format(c, recs, args.expect_format)
    check_scaffold(c, recs)
    check_weight(c, recs, args.expect_resample)
    if args.raw_samples:
        check_reverse(c, args.raw_samples)
        if args.split_manifest:
            check_leakage(c, args.raw_samples, args.split_manifest,
                          args.split_type, args.cutoff_year)
    else:
        c.caution("raw", "未传 --raw-samples：跳过 reverse/leakage 检查")
    if args.config:
        check_config(c, args.config)

    print("\n" + "=" * 64)
    print(f"结果: {c.fail} 个 FAIL, {c.warn} 个 WARN")
    if c.fail:
        print("❌ 有硬性问题，别开训——先修数据/命令。")
        sys.exit(1)
    print("✅ 通过（留意 WARN）。可以开训。")


if __name__ == "__main__":
    main()
