# Personal AI Fine-tuning Evaluation Pipeline

针对"认知轨迹学习"目标设计的评估系统。
测试fine-tuned模型是否真的学会了迭代式推理，而不只是更快地给答案。

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置（编辑 config.py）
```python
BASE_MODEL_NAME = "qwen2.5:7b"       # 你的baseline模型名
FT_MODEL_NAME   = "qwen2.5:7b-ft"   # 微调后的模型名（改成实际名字）
JUDGE_BACKEND   = "pollinations"     # 或 "deepseek"
```

如果用DeepSeek作为judge：
```bash
export DEEPSEEK_API_KEY=your_key_here
```

### 3. 先做快速测试（验证pipeline能跑通）
```bash
python run_eval.py --quick --no-judge
```
这会跑每类前3个题，不调judge，只确认Ollama连接正常。

### 4. 完整评估

**推荐流程（省积分）：**
```bash
# Step 1: 先收集所有回答，不花judge积分
python run_eval.py --no-judge

# Step 2: 看看results/raw_*.json，确认回答质量正常

# Step 3: 再跑judge
python run_judge_only.py --input results/raw_XXXXXXXX.json
```

**一步到位：**
```bash
python run_eval.py
```

---

## 输出说明

```
Category       Model    IterReas   Correct      Traj     Coher
─────────────────────────────────────────────────────────────
style/base     base      2.80±0.6  2.50±0.7  2.30±0.8  3.50±0.5
style/ft       ft        3.90±0.4  3.70±0.5  3.80±0.4  4.10±0.3
```

- **IterReas**: 迭代推理倾向（1=直接给答案，5=多角度探索再得出结论）
- **Correct**: 修正意愿（1=从不修正，5=自然地修正假设）
- **Traj**: 轨迹感（1=孤立答案，5=像正在进行推理过程的一部分）
- **Coher**: 连贯性

---

## 测试题设计逻辑

| 类型 | 数量 | 测试什么 |
|------|------|---------|
| style | 10 | 回答风格：探索式 vs 直接给答案 |
| trajectory | 5 | 多轮对话中的轨迹延续能力 |
| correction | 10 | 对错误假设的温和纠正能力 |

---

## 如何解读结果

**微调成功的信号：**
- FT模型在 IterReas 和 Traj 维度显著高于baseline（差值 > 0.8）
- FT胜率 > 60%
- Correction类别提升最大（因为这类测试最接近refines边的训练数据）

**需要继续优化的信号：**
- FT在Coherence上下降（说明过拟合了style但损失了质量）
- Trajectory类别无提升（说明多轮对话的训练数据不够）
- 三个类别提升不均匀

---

## 文件结构

```
evaluation_pipeline/
├── config.py              # 配置（模型名、API key、参数）
├── run_eval.py            # 主入口
├── run_judge_only.py      # 单独跑judge（节省积分）
├── requirements.txt
│
├── data/
│   └── test_cases.json    # 30个测试题
│
├── models/
│   └── model_runner.py    # Ollama调用
│
├── judge/
│   └── llm_judge.py       # LLM评分（Pollinations/DeepSeek双后端）
│
├── analysis/
│   └── statistics.py      # 统计和输出
│
└── results/               # 自动生成
    ├── raw_*.json          # 原始回答 + judge结果
    └── summary_*.json      # 汇总统计
```
