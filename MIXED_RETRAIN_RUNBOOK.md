# #14 + #13 Runbook（贴合真实 NAS-docker ↔ 笔记本流程）

> 目标：用权威版 chunking(B) 重生成「打标+切分」数据 → mixed(v3/v5/free)+加权 训 v_smart8 → held-out + deploy 评测。
> 标注：**[NAS]** = ssh 进 NAS、在 openclaw 容器里跑（CPU）；**[笔记本]** = 本地跑（GPU/Ollama/读 Y: 盘）。
> 铁律：① 微调模型入 Ollama 必用 `scripts/make_ollama_modelfile.py`；② llamafactory/训练命令必在 venv `C:\ai-training\env`；
>       ③ **策略必用 `--strategy=smart_sentence_reverse`**（见下「策略说明」）。
>
> ### 策略说明（2026-06 修正，含证据）
> - **必须显式传 `--strategy`**：B 的 CLI 默认是 `hard_truncate`，且 `config.strategy` 总会被赋值，所以 `buildTrainingContext` 里那句"默认 reverse"的 fallback **从命令行永远不触发**。不传 = hard_truncate。
> - **用 reverse，不用 forward**：截断只影响训练样本的 input context，**不影响论文1的结构实验数字**（结构脚本读 graph .json，不读训练样本；已核验）。所以旧 runbook"smart_sentence 与论文一致"是误解。对"预测下一步"任务，forward 会丢掉最近的上下文（代码自己标 ❌），reverse 保留最近态（✅）。
> - **现有 v_smart8 数据 = smart_sentence forward**（反推证据：8000 样本里 32% 命中 1000 字上限，其中 88% 干净句界=smart 非 hard；截断样本 100% 以 role tag 开头=forward 非 reverse）。即旧数据对那 ~1/3 被截断的样本丢了最近上下文 → 本次 reverse 重生成是**真修复**，非整容；可能与 FT 未超 base 的 null 结果有关（待重训验证，勿过度声称）。
> 路径映射：`Y:\ai-agent` ＝ 容器内 `/ai-agent`（同一 NAS 共享）。

---

## 步骤 0 [笔记本]：把改过的脚本同步到 NAS（docker 才跑得到新逻辑）

```powershell
# 打标版权威 chunking(B) → NAS scripts
Copy-Item "C:\projects\personal-ai-agent-lab\cognitive-trajectory\scripts\2_representation\cognitive_chunking.js" "Y:\ai-agent\scripts\cognitive_chunking.js" -Force
# 更新过的 prepare_finetune（含 --format/--weighted-resample/--split-manifest）→ NAS scripts
Copy-Item "C:\projects\personal-ai-agent-lab\scripts\prepare_finetune.py" "Y:\ai-agent\scripts\prepare_finetune.py" -Force
```
> make_split_manifest.py / extract_heldout.py 不用传 NAS——它们在笔记本读 Y: 盘的图谱即可。

---

## 步骤 1 [NAS]：用权威版 B + smart_sentence_reverse 重生成「打标」样本

```bash
ssh vanessa@192.168.0.200 "docker exec openclaw rm -f  /ai-agent/training/cognitive_smart/cognitive_samples.jsonl"
ssh vanessa@192.168.0.200 "docker exec openclaw rm -rf /ai-agent/training/cognitive_smart/graphs/"
ssh vanessa@192.168.0.200 "docker exec openclaw node /ai-agent/scripts/cognitive_chunking.js /ai-agent/memory/conversations /ai-agent/training/cognitive_smart --strategy=smart_sentence_reverse"
```
> ⚠️ 必须带 `--strategy=smart_sentence_reverse`。漏掉 = 退回 hard_truncate（见上「策略说明」）。
> 重生成后自检：`python` 抽样看截断样本是否**以句子中部开头**（reverse 特征），不再是 100% role-tag 开头（那是 forward）。
完成后样本带 `source`=对话ID（重生成后才有）。位置：`/ai-agent/training/cognitive_smart/`（＝`Y:\ai-agent\training\cognitive_smart`）。

---

## 步骤 2 [笔记本]：建切分清单（读 Y: 图谱；输出写到 Y: 供 docker 用）

```powershell
cd C:\projects\personal-ai-agent-lab
python scripts/make_split_manifest.py `
  --graphs-dir Y:/ai-agent/training/cognitive_smart/graphs `
  --output Y:/ai-agent/training/cognitive_smart/split_manifest.json
# 同时本地留一份给 eval 用
Copy-Item "Y:\ai-agent\training\cognitive_smart\split_manifest.json" "eval_pipeline\data\split_manifest.json" -Force
```

## 步骤 3 [笔记本]：抽 held-out 评测集（与训练同 universe、零泄漏）

```powershell
python eval_pipeline/experiments/exp3_cloze/extract_heldout.py --graphs-dir Y:/ai-agent/training/cognitive_smart/graphs --split-manifest eval_pipeline/data/split_manifest.json --split-type temporal --split test --output eval_pipeline/data/exp3_cloze_heldout_temporal.json
python eval_pipeline/experiments/exp3_cloze/extract_heldout.py --graphs-dir Y:/ai-agent/training/cognitive_smart/graphs --split-manifest eval_pipeline/data/split_manifest.json --split-type random  --split test --output eval_pipeline/data/exp3_cloze_heldout_random.json
```

---

## 步骤 4 [NAS]：prepare_finetune → mixed + 加权 + 只取 train 切分

**⚠️ 单行执行**（多行 `\` 续行容易被终端弄断，导致 `unrecognized arguments`）。在 NAS 交互 shell 里：
```bash
docker exec openclaw python3 /ai-agent/scripts/prepare_finetune.py --cognitive-only --input-dir /ai-agent/training/cognitive_smart --output /ai-agent/training/finetune_smart --format mixed --weighted-resample --split-manifest /ai-agent/training/cognitive_smart/split_manifest.json --split-type temporal --split train --dataset-name personal_cognitive_v_smart8 --min 0 --max 1091033
```
检查输出日志：①切分过滤行(应 31814 train，剔除 5141 ≥2025测试)；②format 分布 v3/v5/free 各~1/3；③加权重采样行。

---

## 步骤 4.5 [笔记本]：⛔ 重训前自检（gate，别跳）

烧 GPU 之前先跑 pre-flight，任一 FAIL 就别开训（会自动退出码 1）：
```powershell
python scripts/check_finetune_data.py `
  --dataset Y:/ai-agent/training/finetune_smart/dataset.json `
  --raw-samples Y:/ai-agent/training/cognitive_smart/cognitive_samples.jsonl `
  --split-manifest eval_pipeline/data/split_manifest.json --split-type temporal `
  --expect-format mixed --expect-resample `
  --config config/lora_train.yaml --cutoff-year 2025
```
必须全 PASS，尤其 **[reverse]**（截断样本应以句中开头；若报 forward 说明步骤1漏了 `--strategy=smart_sentence_reverse`）。
其余检查项：schema / format 均衡 / scaffold(v3v5含required_relation、free剥离) / weight(重采样重复率+权重相关) / leakage(train全<2025) / config(train_on_prompt=false)。
> 现有 forward 数据跑此检查会 **[FAIL] reverse**（预期）——这正是本次要修的。reverse 重生成后应转 PASS。

---

## 步骤 5 [笔记本]：训练(run_finetune.py) → merge → GGUF → Ollama

```powershell
C:\ai-training\env\Scripts\Activate.ps1   # 必须先激活 venv

# 1. 训练：run_finetune.py 会从 NAS 拷数据 + 跑 QLoRA（你真实的训练入口；输出 adapter 到 C:/ai-training/output/lora_v_smart8）
cd C:\projects\personal-ai-agent-lab
python scripts/run_finetune.py `
  --nas-ip 192.168.0.200 --nas-user vanessa `
  --nas-path /share/CACHEDEV1_DATA/docker/ai-agent/training/finetune_smart `
  --version v_smart8 --init-from base --batch-size 5000
#  （OOM/过热：可调 config/lora_train.yaml 的 batch/grad_accum/cutoff。run_finetune 不做 export，需下面手动。）

# 2. merge adapter
cd C:\ai-training\LLaMA-Factory
llamafactory-cli export --model_name_or_path C:/ai-training/models/Qwen2.5-7B-Instruct --adapter_name_or_path C:/ai-training/output/lora_v_smart8 --template qwen --finetuning_type lora --export_dir C:/ai-training/merged/qwen2.5-7b-v_smart8 --export_size 4
# ⚠️ 必须 q4_K_M（不是 q8_0）！q8_0≈8GB 会和 bge-m3 抢爆 8GB 显存→评测 /api/embeddings 间歇500+极慢换载。
#    q4_K_M≈4.7GB，与 base 同精度、对比更公平，且能与 bge-m3(1.2GB) 同时常驻。
cd C:\ai-training\llama.cpp
python convert_hf_to_gguf.py C:/ai-training/merged/qwen2.5-7b-v_smart8 --outfile C:/ai-training/llama.cpp/qwen2.5-7b-v_smart8-f16.gguf --outtype f16
C:\ai-training\llama.cpp\build\bin\Release\llama-quantize.exe C:/ai-training/llama.cpp/qwen2.5-7b-v_smart8-f16.gguf C:/ai-training/llama.cpp/qwen2.5-7b-v_smart8-q4km.gguf q4_k_m
cd C:\projects\personal-ai-agent-lab
python scripts/make_ollama_modelfile.py --gguf C:/ai-training/llama.cpp/qwen2.5-7b-v_smart8-q4km.gguf --name qwen2.5:7b-v_smart8 --create
```

---

## 步骤 6 [笔记本]：评测（held-out + deploy，核心实验）

```powershell
# v_smart8(mixed)：informat 用 smart3 格式即可，deploy 格式无关
python eval_pipeline/experiments/exp3_cloze/run_cloze_fair.py `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --base-model qwen2.5:7b-instruct-q4_K_M --qa-model qwen2.5:7b-v_qa_pilot_fixed `
  --trajectory-model qwen2.5:7b-v_smart8 --trajectory-format smart3 `
  --modes informat,deploy,oldstyle `
  --output eval_pipeline/results/exp3_heldout_v_smart8.json
```
看点：held-out 上 trajectory≥base(泛化)；**deploy 关系自选准确率从~0%显著上升**(free回报)；deploy 语义≥base(部署有效)。

### Phase 3 RAG 基线（回答"为何微调而非检索"）
```powershell
python eval_pipeline/baselines/run_rag_baseline.py `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --train-samples Y:/ai-agent/training/cognitive_smart/cognitive_samples.jsonl `
  --split-manifest eval_pipeline/data/split_manifest.json --split-type temporal `
  --base-model qwen2.5:7b-instruct-q4_K_M --topk 3 `
  --output eval_pipeline/results/exp3_rag_heldout_temporal.json
```
看点：RAG 相对 base 的提升 vs trajectory-FT 的提升——若 FT>RAG，支撑"微调比检索更能内化你的认知方式"。

### RAG 消融（in-context/few-shot 对照，回答"是检索有用还是只要有示例"）
```powershell
# rag(检索) + random(随机few-shot) 一起跑；base(none) 始终计算 → 三方对照
python eval_pipeline/baselines/run_rag_baseline.py `
  --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json `
  --train-samples Y:/ai-agent/training/cognitive_smart/cognitive_samples.jsonl `
  --split-manifest eval_pipeline/data/split_manifest.json --split-type temporal `
  --base-model qwen2.5:7b-instruct-q4_K_M --topk 3 --modes rag,random `
  --output eval_pipeline/results/exp3_rag_abl_heldout.json
```
看点：rag > random ≈ base 说明"是**检索到你的相关历史**起作用"，而非单纯有示例。

### QA-SFT 基线（可选，Phase6 完整消融用；现非必须）
> 现有 v_qa_pilot 在全量上训、对 held-out 有泄漏，不能用。要干净对照就在 **train 切分**上训一个 v_qa8：
```bash
# [NAS] 单行：用新加的 --format qa 在 train 切分上生成纯QA数据
docker exec openclaw python3 /ai-agent/scripts/prepare_finetune.py --cognitive-only --input-dir /ai-agent/training/cognitive_smart --output /ai-agent/training/finetune_qa8 --format qa --weighted-resample --split-manifest /ai-agent/training/cognitive_smart/split_manifest.json --split-type temporal --split train --dataset-name personal_cognitive_qa8 --min 0 --max 1091033
```
```powershell
# [笔记本] 训练 → merge → gguf → ollama（同 v_smart8 流程，名字换 v_qa8）
python scripts/run_finetune.py --nas-ip 192.168.0.200 --nas-user vanessa --nas-path /share/CACHEDEV1_DATA/docker/ai-agent/training/finetune_qa8 --version v_qa8 --init-from base --batch-size 5000
# ...export / convert_hf_to_gguf / make_ollama_modelfile --name qwen2.5:7b-v_qa8 ...
# 评测（qa 模型用 --trajectory-format qa）
python eval_pipeline/experiments/exp3_cloze/run_cloze_fair.py --benchmark eval_pipeline/data/exp3_cloze_heldout_temporal.json --base-model qwen2.5:7b-instruct-q4_K_M --qa-model qwen2.5:7b-v_qa8 --trajectory-model qwen2.5:7b-v_qa8 --trajectory-format qa --modes informat,deploy --output eval_pipeline/results/exp3_heldout_v_qa8.json
```

### Phase 6 消融（可选）
`pure-v3(v_smart3_fixed)/pure-v5(v_smart5)/mixed(v_smart8)/qa(v_qa8)` × `{informat,deploy}` 在 held-out 各跑一遍。

---

## 数据/路径备忘
| 项 | 路径 |
|---|---|
| 打标样本(NAS) | `/ai-agent/training/cognitive_smart/cognitive_samples.jsonl`（=`Y:\...`） |
| 图谱 | `Y:/ai-agent/training/cognitive_smart/graphs` |
| 切分清单 | `eval_pipeline/data/split_manifest.json`（+ Y: 一份给 docker） |
| held-out | `eval_pipeline/data/exp3_cloze_heldout_{temporal,random}.json` |
| 训练数据(NAS出) | `/ai-agent/training/finetune_smart/` → 拷到 `C:\ai-training\finetune\` |
| adapter | `C:/ai-training/output/lora_v_smart8` |
| 模型名 | `qwen2.5:7b-v_smart8` |
