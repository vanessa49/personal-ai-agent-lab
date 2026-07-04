# 论文 2（行为）操作 Runbook — 顺着做

> 目标：把行为证据的重心放到**客观可算指标(④)**，盲评(①)/judge(③)做人类锚点，⑤合成做外部效度，⑥预注册保确认性。
> 标注：**[现在]** 不依赖重训；**[待#4]** 需 #14 reverse 重生成 + #4 重训后的新 v_smart8；**[你的密钥]** 需 Gemini。
> 铁律（预注册逻辑）：**⑥ 在最前面**。看过确认性数据再定假设 = 不算确认性。现有 40 条盲评 = 探索性，别当证据。

---

## 阶段 0 [现在]：⑥ 锁预注册 + 冻结确认集选择

1. 定稿 `PAPER2_PREREGISTRATION.md`（假设/主次指标/分析），**存一份带日期的只读副本**。
2. **冻结确认性盲评的题目选择**（只冻结"哪些题 + 种子"，续写等 #4 后再生成）：
```powershell
# 题型分类（若还没有）：把 held-out 标 open/closed，盲评只用 open
python eval_pipeline/classify_question_type.py `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --output eval_pipeline/data/heldout_question_type.json
```
3. 在预注册里写死：确认集 = open 题、`--seed 20260704`（换成你定的）、`--sample 150`，且与探索用的 40 条不重叠。**此刻只锁参数，不看内容。**

---

## 阶段 A [现在·探索性]：④ 客观指标先看方向（当前 v_smart8）

> 只为看趋势，**结果算探索性**（你看了就不能再当确认性）。确认性版本在阶段 C 重训后跑。

风格嵌入距离（生成续写到"你的风格质心"的距离，越小越像你；需 Ollama bge-m3）：
```powershell
python eval_pipeline/style_distance.py `
  --result eval_pipeline/results/exp3_heldout_v_smart8.json `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --mode informat `
  --out eval_pipeline/results/style_distance_summary_EXPLORATORY.json
```
看点：`trajectory_minus_base.mean` 为负 = trajectory 更贴近你的风格；看 CI 是否含 0。
（`gold_self_reference_loo` 是参照下界——模型不可能比你自己更像你。）

---

## 阶段 B [现在·你的密钥]：③ LLM-judge 试跑 + 人机一致（当前 40）

先在已评的 40 条上试 judge，验证 judge 靠谱、并出人机一致（这步用现有数据，算方法学锚点）：
```powershell
# 1) judge 判全部（读 blind CSV 的三候选 + benchmark 的 gold）
python eval_pipeline/judge/llm_judge_pairwise.py `
  --blind-csv eval_pipeline/results/exp3_blind_open_full.csv `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --out-private eval_pipeline/results/llm_judge_picks.json `
  --out-summary eval_pipeline/results/llm_judge_summary.json

# 2) 与你人工 40 条算一致（Cohen's κ + %agreement）
python eval_pipeline/judge/llm_judge_pairwise.py --agreement `
  --judge-picks eval_pipeline/results/llm_judge_picks.json `
  --blind-csv eval_pipeline/results/exp3_blind_open_full.csv `
  --out-summary eval_pipeline/results/llm_judge_summary.json
```
看点：人机一致高于随机 = judge 可作规模化第二评审；judge 测"像gold"、你测"像我"，收敛才算数。

---

## 阶段 C [待#4]：确认性主线（重训后跑，这些才是论文证据）

> 前置：#14 reverse 重生成 → `check_finetune_data` 全 PASS → #4 训出新 v_smart8 → 用 MIXED runbook 步骤6 在 held-out 上重生成三方续写到 `exp3_heldout_v_smart8.json`。

**④ 客观指标（主轴，全 held-out，零评审）**
```powershell
# 风格距离（确认性）
python eval_pipeline/style_distance.py `
  --result eval_pipeline/results/exp3_heldout_v_smart8.json `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --mode informat --out eval_pipeline/results/style_distance_summary.json
# 多步轨迹连贯性：见 PAPER3_TRAINER_ABLATION_DESIGN.md §4（与论文3共用，脚本待写 = task #11/#21）
```

**③ LLM-judge 全量 549 + 人机一致**：同阶段 B 命令，但 judge 全 held-out（不只 40）→ 大 n 胜率。

**②→① 确认性盲评（≥150，锁定集）**
```powershell
# 1) 用阶段0锁定的 seed/sample 生成新盲评（新 v_smart8 的续写；--hide 模型身份）
python eval_pipeline/gen_blind_open.py `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --type-file eval_pipeline/data/heldout_question_type.json `
  --trajectory-model qwen2.5:7b-v_smart8 --trajectory-format smart3 `
  --sample 150 --seed 20260704 `
  --output eval_pipeline/results/exp3_blind_confirmatory.csv
# 2) 你盲填 your_pick=1（凭直觉选"最像我下一步"）
# 3) 解码 + SCED 随机化检验 → 确认性 p
python cognitive-trajectory/behavioral_eval/blind_randomization_test.py `
  --csv eval_pipeline/results/exp3_blind_confirmatory.csv `
  --out cognitive-trajectory/behavioral_eval/blind_randomization_confirmatory.json
```
看点：n≥150 时，若 trajectory≈40%，单侧 p 应进入显著区（现在 n=40 是 p=0.23）。

---

## 阶段 D [任何时候·独立]：⑤ 合成人格外部效度

不依赖真实重训、无隐私、可公开复现。见 `PAPER2_SYNTHETIC_EXTERNAL_VALIDITY.md`：造 K 个虚构人格多会话语料 → 同 pipeline → 多评审 + 客观指标 → 看真实 n=1 效应是否重现。脚本待写（task #22）。

---

## 一页流程图

```
⑥锁预注册+冻结题目选择(现在)
      │
      ├─[现在·探索] A:④风格距离(当前模型)  B:③judge+人机一致(40条)
      │
      └─[待#14→#4 重训]  C: ④确认性(风格+连贯性,全549)
                              ③judge全549
                              ②→① 确认性盲评≥150 → 随机化检验出确认p
   [任何时候] D:⑤合成外部效度(独立,可公开)
```
上传策略延续：只推**聚合数字 + 脚本**到 cognitive-trajectory 仓库；逐项/语料私有。
