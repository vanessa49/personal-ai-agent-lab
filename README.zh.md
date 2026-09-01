# Personal AI Agent Lab（个人 AI Agent 实验室）

[English](README.md) | [中文](README.zh.md)

> 一个早期个人 AI 原型的公开工程快照：本地大模型、长期记忆、Agent 插件、对话处理与微调探索。

**状态：历史原型 / 作为公开项目记录维护**

这个仓库记录了我最初探索长期 Personal AI 时搭建的工程原型。它现在**不是**后来研究工作的最新 scientific authority，也不是当前 CHI 稿件或复现代码的主仓。

最初的系统横跨 GPU 笔记本与常驻 NAS，组合 Ollama、OpenClaw、SQLite/sqlite-vec、Qdrant、自定义插件以及对话处理流水线。真正把这个项目推向下一阶段的，不是又换了一个模型，而是一个数据表示问题：如果 Personal AI 想从一个人的长期交互中学习，真的应该把这些历史压成彼此独立的 Q&A 吗？

这个问题后来发展成独立的 longitudinal human-AI interaction / thought trajectory 研究。当前论文与复现工作在独立仓库中维护；这里保留的一些 cognitive / fine-tuning 脚本属于探索过程中的历史路径，不应被理解为后续论文的最新实现或证据来源。

## 我做了什么

这个原型主要探索 Personal AI 的四层能力：

1. **本地推理** —— GPU 机器运行 Ollama。
2. **常驻 Agent Runtime** —— NAS / 常开服务器运行 OpenClaw。
3. **长期记忆与检索** —— 主 memory path 使用 SQLite + sqlite-vec；Qdrant 作为独立实验向量库。
4. **学习流水线探索** —— 对话导入、训练样本生成与审核、认知切分，以及面向 QLoRA 的微调实验。

### 系统架构

```text
┌─────────────────────────┐        ┌──────────────────────────────┐
│   GPU 机器              │        │   NAS / 常驻服务器           │
│                         │        │                              │
│   Ollama                │◄──────►│   OpenClaw（Docker）         │
│   - 本地 LLM            │        │   - Plugin System            │
│   - bge-m3 embedding    │        │   - Memory (SQLite + vec)    │
└─────────────────────────┘        │   - Processing Pipelines     │
                                   │                              │
                                   │   Qdrant（Docker）           │
                                   │   - Experimental vector DB   │
                                   └──────────────────────────────┘
```

OpenClaw 的主记忆路径使用 SQLite + sqlite-vec。这个快照中的 Qdrant 是外部实验数据库，并没有接入 OpenClaw 的 `memory_search` 主链路。

## Agent 扩展

原型阶段实现了 6 个自定义插件：

| Plugin | 用途 |
|---|---|
| `tool-logger` | 记录工具调用 |
| `task-logger` | 追踪任务生命周期 |
| `safe-delete-enforcer` | 保护高风险删除操作 |
| `qdrant-auto-checker` | 查询 / 诊断外部 Qdrant |
| `training-sample-generator` | 从对话生成候选训练样本 |
| `memory-compressor` | 压缩过长对话上下文 |

另外还有 task logging、memory compression、Qdrant diagnosis、safe deletion、sample generation 对应的 hooks / skills。

## 这里保留的两条数据处理路径

```text
传统路径
conversation logs
    ↓
按 user / assistant turn 处理
    ↓
候选训练样本
    ↓
Agent + 人工审核
    ↓
fine-tuning dataset
```

```text
探索性 cognitive path
conversation logs
    ↓
semantic / cognitive segmentation
    ↓
typed trajectory graph
    ↓
weighted sample preparation
    ↓
fine-tuning + evaluation experiments
```

第二条路径正是这个工程项目逐渐变成研究问题的桥梁。它在这里保留是为了记录 project lineage，而不是作为后续研究的 canonical implementation。

## 项目演进

### 1. 从产品问题出发

一个本地 AI 系统能不能通过持续学习个人的真实交互历史，逐渐变得比通用云模型更“属于这个人”？

### 2. 先把东西做出来

我先搭了 GPU + NAS 的本地系统，补上持续记忆、自定义 Agent 行为和训练数据处理路径。

### 3. 真正的问题变成数据表示

当我开始准备历史对话用于学习时，核心问题从“用哪个模型”变成了“长期交互到底应该怎样表示”。简单 Q&A slicing 会丢掉大量迭代、修正和前后依赖结构。

### 4. 研究与原型正式拆开

这个观察后来发展成独立研究。于是工程原型、科学证据与投稿材料不再共用一个仓库 authority；当前研究代码和 manuscript workflow 已经迁到独立仓库。

## 相关文章

- **Medium** — [What if your AI could grow with you?](https://medium.com/design-bootcamp/what-if-your-ai-could-grow-with-you-a4a6dcc512ac)  
  最初的产品问题，以及“growth ownership”的概念。
- **Dev.to** — [Building a personal AI agent that grows with you](https://dev.to/vanessa49/building-a-personal-ai-agent-that-grows-with-you-4c29)  
  早期工程实现与踩坑记录。
- **Medium** — [Personal AI isn't about answers — it's about thought trajectories](https://medium.com/design-bootcamp/personal-ai-isnt-about-answers-it-s-about-thought-trajectories-d1afd1d4b87b)  
  工程实践如何引出数据表示问题。
- **Dev.to** — [Personal AI isn't Q&A, it's iteration](https://dev.to/vanessa49/personal-ai-isnt-qa-its-iteration-3496)  
  Thought trajectory 思路的技术伴随文章。

## 历史原型快速启动

> 这是实验快照，不是持续支持的生产套件。不要直接拿真实个人数据跑；先检查配置、路径与当前 OpenClaw 兼容性。

```bash
git clone https://github.com/vanessa49/personal-ai-agent-lab.git
cd personal-ai-agent-lab
cp config/openclaw.json.example ~/.openclaw/config.json
```

配置 Ollama host 和本机 volume 后：

```bash
docker compose up -d
```

这个原型曾基于 OpenClaw `2026.3.11` 构建和测试；当前上游行为可能已经不同。

## 其他公开项目

- [`obsidian-qdrant-pipeline-oss`](https://github.com/vanessa49/obsidian-qdrant-pipeline-oss) —— 本地优先的 Obsidian + Qdrant 文档入库与检索管道，包含明确的隐私边界和 public-release guard。
- [`nvidia-api-lifecycle-guard`](https://github.com/vanessa49/nvidia-api-lifecycle-guard) —— 用于审计 NVIDIA hosted API / NIM 变化与兼容性的 Python 工具。
- [`Fractal-Scripts`](https://github.com/vanessa49/Fractal-Scripts) —— 早期 creative-coding 项目，用 Python 生成和探索分形图像。

## 隐私与研究边界

真实对话历史、个人 memory store、private knowledge base、训练语料、模型 artifact，以及当前研究材料都不应该提交到这里。

如果你是沿着后续论文或研究线索来到这里，请把这个仓库理解为**早期工程原型**，而不是当前 manuscript / evidence 的 source of truth。

## License

MIT
