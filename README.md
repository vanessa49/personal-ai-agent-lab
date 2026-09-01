# Personal AI Agent Lab

[English](README.md) | [中文](README.zh.md)

> A public engineering snapshot of an early personal-AI prototype: local LLM inference, long-term memory, agent plugins, conversation processing, and fine-tuning experiments.

**Status: Historical prototype / maintained as a public project record**

This repository documents the engineering prototype that started my exploration of long-term personal AI. It is intentionally **not** the current scientific authority for the research that later grew out of it.

The original build combined a GPU laptop, an always-on NAS, Ollama, OpenClaw, SQLite/sqlite-vec, Qdrant, custom plugins, and conversation-processing pipelines. While building it, a product question gradually turned into a data-representation question: if a personal AI is supposed to learn from a person over time, should its history really be reduced to independent Q&A pairs?

That question later developed into separate research work on longitudinal human-AI interaction and thought trajectories. Current manuscript and reproducibility work is maintained separately during the research/submission process. Some exploratory scripts remain here because they are part of the historical path, but they should not be treated as the latest paper implementation or evidence authority.

## What I built

The prototype explored four layers of a personal-AI system:

1. **Local inference** — Ollama on a GPU machine for local model serving.
2. **Persistent agent runtime** — OpenClaw on an always-on NAS/server.
3. **Long-term memory and retrieval** — SQLite + sqlite-vec for the primary memory path, with Qdrant used as a separate experimental vector store.
4. **Learning pipeline experiments** — conversation ingestion, sample generation/review, cognitive segmentation, and QLoRA-oriented fine-tuning experiments.

### System architecture

```text
┌─────────────────────────┐        ┌──────────────────────────────┐
│   GPU Machine           │        │   NAS / Always-on Server     │
│                         │        │                              │
│   Ollama                │◄──────►│   OpenClaw (Docker)          │
│   - local LLMs          │        │   - Plugin System            │
│   - bge-m3 embedding    │        │   - Memory (SQLite + vec)    │
└─────────────────────────┘        │   - Processing Pipelines     │
                                   │                              │
                                   │   Qdrant (Docker)            │
                                   │   - Experimental vector DB   │
                                   └──────────────────────────────┘
```

The primary OpenClaw memory path uses SQLite + sqlite-vec. Qdrant is an external experimental store and is **not** integrated into OpenClaw's `memory_search` path in this snapshot.

## Agent extensions

The repository includes six custom plugins used during the prototype phase:

| Plugin | Purpose |
|---|---|
| `tool-logger` | Record tool calls |
| `task-logger` | Track task lifecycle |
| `safe-delete-enforcer` | Guard destructive file operations |
| `qdrant-auto-checker` | Query/diagnose the external Qdrant service |
| `training-sample-generator` | Turn conversations into candidate training samples |
| `memory-compressor` | Compress long conversation context |

It also contains hooks and reusable skills for task logging, memory compression, Qdrant diagnostics, safe deletion, and sample generation.

## Two data-processing directions explored here

The repository contains both the original turn-oriented pipeline and the later exploratory cognitive-segmentation pipeline.

```text
Traditional path
conversation logs
    ↓
turn-based processing
    ↓
candidate samples
    ↓
automated + human review
    ↓
fine-tuning dataset
```

```text
Exploratory cognitive path
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

The second path was the bridge from a product prototype into a research question. It is retained here for lineage, not as the canonical implementation of the later research.

## Project lineage

### 1. Product question

Could a local AI system become more personally useful over time by learning from a user's own interaction history rather than relying only on generic cloud-model behavior?

### 2. Prototype build

I built a local-first system across a GPU machine and NAS, added persistent memory, custom agent behaviors, and a training-data workflow.

### 3. Representation problem

While preparing historical conversations for learning, the main difficulty stopped being model choice and became **how to represent longitudinal interaction data**. Independent Q&A slices discarded much of the iterative structure I cared about.

### 4. Research split

That observation became a separate research program. The research repositories and manuscript workflow were split away from this engineering lab so that the prototype, scientific evidence, and submission materials would not share one authority surface.

## Articles

- **Medium** — [What if your AI could grow with you?](https://medium.com/design-bootcamp/what-if-your-ai-could-grow-with-you-a4a6dcc512ac)  
  The original product idea and the concept of ownership of growth.
- **Dev.to** — [Building a personal AI agent that grows with you](https://dev.to/vanessa49/building-a-personal-ai-agent-that-grows-with-you-4c29)  
  Early implementation notes from the prototype.
- **Medium** — [Personal AI isn't about answers — it's about thought trajectories](https://medium.com/design-bootcamp/personal-ai-isnt-about-answers-it-s-about-thought-trajectories-d1afd1d4b87b)  
  How the engineering project led to a data-representation question.
- **Dev.to** — [Personal AI isn't Q&A, it's iteration](https://dev.to/vanessa49/personal-ai-isnt-qa-its-iteration-3496)  
  A technical companion piece on the trajectory idea.

## Quick start for the historical prototype

> This is an experimental snapshot, not a supported production package. Review configuration and paths before running it on any personal data.

```bash
git clone https://github.com/vanessa49/personal-ai-agent-lab.git
cd personal-ai-agent-lab
cp config/openclaw.json.example ~/.openclaw/config.json
```

Configure your Ollama host and local volumes, then start the agent-side services:

```bash
docker compose up -d
```

The prototype was built around OpenClaw `2026.3.11`; current upstream behavior may differ.

## Other public projects

- [`obsidian-qdrant-pipeline-oss`](https://github.com/vanessa49/obsidian-qdrant-pipeline-oss) — local-first document ingestion and retrieval for Obsidian + Qdrant, with explicit privacy boundaries and public-release guards.
- [`nvidia-api-lifecycle-guard`](https://github.com/vanessa49/nvidia-api-lifecycle-guard) — a small Python toolkit for safely auditing changing NVIDIA hosted API / NIM integrations.
- [`Fractal-Scripts`](https://github.com/vanessa49/Fractal-Scripts) — an early creative-coding project for generating and exploring fractal images.

## Privacy and research boundary

Real conversation history, personal memory stores, private knowledge bases, training corpora, model artifacts, and current research material are not intended to be committed here.

If you are reading this repository as part of the later research lineage, treat it as an **early engineering artifact**, not as the current manuscript or evidence source of truth.

## License

MIT
