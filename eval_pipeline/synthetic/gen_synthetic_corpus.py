#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成合成人格语料（⑤ 外部效度探针，task #22）：把 personas.json 里的虚构人格展开成
多会话、跨时间的对话，写成 cognitive_chunking.js 能直接吃的 .md 格式。

产物**不对应任何真人**、可完全公开复现。用途：跑同一条 pipeline（chunking→两种表示→
QLoRA→评测），看"QA vs trajectory 的区分"是否在**别的**轨迹上也重现 = 方法外部效度。

关键设计（让 trajectory vs QA 真的有差异可测）：
  - 每个会话内要有真实的认知推进：refine（走回/修正）、contrast（换角度）、derive（推导下一步）；
  - 部分会话是"revisit"：重开某个早期话题、并给出**修订后的立场**（制造跨会话修订结构，
    对上 trajectory / evolution-aware 的论点）；
  - 时间戳跨 start~end：早期会话落训练期、后期落测试期（temporal 切分可用）。

需要 LLM（默认 Gemini，复用 eval_pipeline/judge/llm_judge._call_api；需 config 密钥）。

用法:
  python eval_pipeline/synthetic/gen_synthetic_corpus.py \
     --personas eval_pipeline/synthetic/personas.json \
     --out-dir eval_pipeline/synthetic/conversations \
     --sessions-per-persona 12 --start 2024-01-01 --end 2026-03-01 --backend gemini
"""
import argparse, json, random, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

GEN_PROMPT = """你在生成一段**虚构人物**与 AI 助手的真实感对话，用于研究数据（不对应任何真人）。

人物设定（用户方要体现这个思维风格）：
- 领域：{domains}
- 推理风格：{reasoning_style}
- 修正倾向：{correction_tendency}
- 语气：{tone}

本次话题：{topic}
{revisit_note}

要求：
1. 写 6–12 轮，严格用行首标记 `## User` 和 `## Assistant` 交替（不要别的标题格式）。
2. **用户方**要真实体现该人物的思维推进——过程中要出现：至少一次**修正/走回**（"其实，重新想…"）、
   至少一次**换角度/对比**（"不过换个角度…"）、至少一次**推导下一步**（"那么接下来…"）。
3. 助手方正常协助，但不要长篇大论到盖过用户的思路推进。
4. 自然、有具体细节，不要写成条目化模板，不要 meta 说明。
5. 只输出对话本身（从 `## User` 开始）。"""

REVISIT_TMPL = "这是一个 **revisit**：用户在更早的会话里对「{prior}」持某立场，现在**改变了主意**，本次要体现修订后的新立场与理由。"


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--personas", default="eval_pipeline/synthetic/personas.json")
    ap.add_argument("--out-dir", default="eval_pipeline/synthetic/conversations")
    ap.add_argument("--sessions-per-persona", type=int, default=12)
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2026-03-01")
    ap.add_argument("--backend", default="gemini")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from judge.llm_judge import _call_api  # noqa
    personas = json.loads(Path(args.personas).read_text(encoding="utf-8"))["personas"]
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    d0 = datetime.date.fromisoformat(args.start)
    d1 = datetime.date.fromisoformat(args.end)
    span = (d1 - d0).days

    n_ok = 0
    for p in personas:
        topics = list(p["domains"])
        prior_topics = []
        for s in range(args.sessions_per_persona):
            # 时间戳按会话顺序线性铺开（早→训练期，晚→测试期）
            day = int(span * s / max(1, args.sessions_per_persona - 1))
            ts = datetime.datetime.combine(d0 + datetime.timedelta(days=day),
                                           datetime.time(rng.randint(8, 20), rng.randint(0, 59)))
            is_revisit = s >= 3 and prior_topics and rng.random() < 0.35
            if is_revisit:
                topic = rng.choice(prior_topics)
                revisit = REVISIT_TMPL.format(prior=topic)
            else:
                topic = rng.choice(topics)
                prior_topics.append(topic)
                revisit = ""
            prompt = GEN_PROMPT.format(domains="；".join(p["domains"]),
                                       reasoning_style=p["reasoning_style"],
                                       correction_tendency=p["correction_tendency"],
                                       tone=p["tone"], topic=topic, revisit_note=revisit)
            try:
                body = _call_api(prompt, args.backend).strip()
            except Exception as e:
                print(f"  [skip {p['id']} s{s}] {e}")
                continue
            if "## User" not in body:
                print(f"  [skip {p['id']} s{s}] 输出没有 ## User 标记")
                continue
            md = f"**创建时间**: {iso(ts)}\n\n{body}\n"
            fp = out / f"{p['id']}_s{s:02d}{'_revisit' if is_revisit else ''}.md"
            fp.write_text(md, encoding="utf-8")
            n_ok += 1
            print(f"  wrote {fp.name}  ({iso(ts)}{' revisit' if is_revisit else ''})")
    print(f"\n[OK] {n_ok} 个合成对话 -> {out}")
    print("下一步：把 out-dir 当 conversations 输入喂给 cognitive_chunking.js "
          "(--strategy=smart_sentence_reverse)，再走同一条 pipeline。")


if __name__ == "__main__":
    main()
