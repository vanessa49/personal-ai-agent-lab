# 论文 2（行为）⑤：合成人格语料 · 外部效度探针（设计）

> 状态：设计（task #22）。**非确认性**——它不替代 n=1 真实语料的单被试检验，只回答一个独立问题：
> "这套区分 trajectory vs QA 的方法，在**别的**（虚构、可公开）轨迹上也work吗？" 用来挡"只你一个人、只你的语料才有效"的质疑，且**不碰任何真人隐私**。

## 为什么需要它
- 隐私卡的是**真人语料**，不是**方法**。合成一个不对应任何真人的"人格"多会话语料，就能：
  1. 请**多个评审**判（多评审功率，真人语料做不到）；
  2. **完全公开复现**（语料本身就是造的，可随论文发布）；
  3. 证明差异来自**表示方法**而非某个人的特异风格。

## 构造（已备好可跑）

**已就绪的产物**：
- `eval_pipeline/synthetic/personas.json` — 4 个虚构人格卡（founder/researcher/clinician/designer），各有稳定领域/推理风格/修正倾向/语气/跨会话修订习惯，**明确标注无真人对应**。
- `eval_pipeline/synthetic/gen_synthetic_corpus.py` — 生成器：把人格卡展开成多会话、跨时间的 `.md` 对话，格式与 `cognitive_chunking.js` 的输入完全一致（`**创建时间**:` 头 + `## User`/`## Assistant`）；prompt 强制每会话含 refine/contrast/derive，部分会话是 revisit（修订早期立场→跨会话修订结构）；时间戳跨 start~end（早→训练期、晚→测试期）。

**步骤**：
1. 生成语料（需 LLM 密钥）：
```powershell
python eval_pipeline/synthetic/gen_synthetic_corpus.py `
  --personas eval_pipeline/synthetic/personas.json `
  --out-dir eval_pipeline/synthetic/conversations `
  --sessions-per-persona 12 --start 2024-01-01 --end 2026-03-01 --backend gemini
```
2. 过同一条 pipeline：`cognitive_chunking.js <conversations> <out> --strategy=smart_sentence_reverse` → 两种表示 → 同一 QLoRA 配方 → 各自模型（复用 MIXED_RETRAIN_RUNBOOK 的流程）。
3. 建 held-out（后期会话），生成三方续写。

## 评测（可多评审 + 可公开）
- **多评审盲评**：招若干评审（无隐私顾虑，语料是造的），judge"哪个续写最像这个 persona 的下一步"→ 计算评审间一致(IRR) + 胜率。
- **客观指标同真实语料**：多步连贯性、风格嵌入距离、可控性。
- **对照**：真实 n=1 语料上的效应方向，是否在合成 persona 上**重现**。重现 = 方法有外部效度；不重现 = 效应可能是该用户特异（也是有价值的边界发现）。

## 诚实边界
- 合成语料**没有真实认知演化**，只有被 prompt 出来的结构——所以它证的是"方法能区分被设计进去的结构"，**不是**"合成 persona 有真认知"。论文里要讲清：这是**方法可行性/外部效度**探针，真实认知主张仍只由 n=1 真实语料承担。
- 合成语料可随论文公开（含生成脚本 + persona 卡 + 种子），是**唯一能完全复现**的部分。

## 落地顺序
低优先，排在真实语料确认性检验（①③④⑥）之后；但因为它完全无隐私、可公开，是**审稿人最容易验证**的一块，值得作为附录复现包。依赖：pipeline 跑通（#4/#14）。
