# Personal AI Agent Lab

[English](README.md) | [中文](README.zh.md)

> Experimental system for building a self-improving personal AI agent based on conversation history and long-term memory.

**Status: Research Prototype / Work in Progress**

> Learn more about this project:

- **Medium (Concept & Philosophy)** – [What if your AI could grow with you](https://medium.com/design-bootcamp/what-if-your-ai-could-grow-with-you-a4a6dcc512ac)  
  Explores the ideas, design philosophy, and strategic thinking behind the personal AI system.  

- **Dev.to (Implementation & Lessons)** – [Building a personal AI agent that grows with you](https://dev.to/vanessa49/building-a-personal-ai-agent-that-grows-with-you-4c29)  
  Shares technical implementation, challenges, and practical lessons learned during development.

---

## Project Idea

Humans are shaped by their past experiences. Conversations, knowledge, and memories gradually form our personality and decision-making patterns.

This project explores the idea that:

> If an LLM is given access to its past interactions and learning history, it may gradually evolve into a personalized digital cognitive assistant.

The goal is to build an AI agent that behaves more like another version of yourself, rather than a generic chatbot.

```
local LLM  +  long-term memory  +  conversation history  →  personalized agent
```

---

## System Architecture

This project uses a **split deployment** model:

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│   GPU Machine           │        │   NAS / Always-on Server     │
│                         │        │                              │
│   Ollama                │◄──────►│   OpenClaw (Docker)          │
│   - qwen3.5:9b          │        │   - Plugin System            │
│   - qwen2.5:7b          │        │   - Memory (SQLite + vec)    │
│   - bge-m3 (embedding)  │        │   - Training Pipeline        │
└─────────────────────────┘        │                              │
                                   │   Qdrant (Docker)            │
                                   │   - Vector search            │
                                   └──────────────────────────────┘
```

The GPU machine runs Ollama for inference. The NAS/server runs OpenClaw and Qdrant via Docker, and connects to Ollama over the local network.

Note: Qdrant is currently an external database accessed via plugin API. OpenClaw's memory system is SQLite + sqlite-vec; hybrid search operates on SQLite vectors.

---

## Key Components

### Plugins (`/plugins`)

Extend the OpenClaw agent runtime with custom behaviors:

| Plugin | Description |
|---|---|
| `tool-logger` | Records every tool call to a log file |
| `task-logger` | Tracks agent task lifecycle |
| `safe-delete-enforcer` | Prevents unsafe file deletion |
| `qdrant-auto-checker` | Queries Qdrant via plugin API (external DB, not integrated with `memory_search`) |
| `training-sample-generator` | Converts conversations into training samples |
| `memory-compressor` | Compresses long conversation context automatically |

### Hooks (`/hooks`)

Agent hooks that fire on specific events:

| Hook | Trigger | Description |
|---|---|---|
| `auto-task-logger` | Task events | Logs task start/end automatically |
| `qdrant-auto-checker` | Keyword match | Runs Qdrant health check |
| `safe-delete-enforcer` | Pre-tool | Blocks dangerous delete operations |

### Skills (`/skills`)

Reusable skill definitions loaded into agent context:

- `memory-compress` — compress and summarize memory chunks
- `qdrant-check` — diagnose vector DB state
- `safe-delete` — safe file deletion workflow
- `task-logger` — structured task logging
- `training-sample-generator` — generate fine-tuning samples from conversations

### Scripts (`/scripts`)

Two training pipelines are available:

**Traditional pipeline** (turn-based segmentation):
```
conversation logs
      ↓
batch_process_conversations.js   # parse and chunk by user/assistant turns
      ↓
training-sample-generator        # generate candidate samples
      ↓
agent_review_samples.js/.py      # agent auto-review
      ↓
review_samples.js                # human review interface
      ↓
fine-tuning dataset
```

**Cognitive pipeline** (semantic segmentation):
```
conversation logs
      ↓
cognitive_chunking.js            # segment by cognitive events, not turn boundaries
      ↓                          # builds graph: nodes + typed edges
prepare_finetune.py              # weight samples by relation type + time decay
      ↓
run_finetune.py                  # kick off QLoRA training
      ↓
run_ab_test.py                   # compare baseline vs fine-tuned model
```

The cognitive pipeline segments conversations by semantic shift (topic change, correction marker, new idea) rather than user/assistant turn boundaries. Each segment becomes a node; edges between nodes carry a typed relation:

| Relation | Meaning |
|---|---|
| `follows` | Sequential continuation (default) |
| `derives` | Logical inference |
| `refines` | Explicit correction or improvement |
| `contrasts` | Perspective shift |
| `responds` | Direct reply across roles |
| `iteration_final` | Convergence after a correction chain |
| `hypothesizes` | Conditional / hypothetical reasoning |
| `restarts` | Thought reset or reconsideration |
| `clarifies` | More precise restatement |
| `speculates` | Uncertain inference or guess |

Samples are weighted during fine-tuning preparation:

```python
weight_map = {
    'iteration_final': 2.5,   # end of correction chain × depth bonus
    'refines':         2.0,   # explicit correction
    'contrasts':       2.0,   # perspective shift
    'derives':         1.5,   # logical consequence
    'clarifies':       1.5,   # precise restatement
    'hypothesizes':    1.3,   # conditional reasoning
    'restarts':        1.2,   # thought reset
    'follows':         1.0,   # default
}
# Plus time decay: weight ×= e^(-age_in_days / 1460)
```

Use `discover_relation_patterns.js` to analyze the relation distribution in your own graph data, and `compare_chunking_methods.js` to compare the two pipelines on a single conversation file.

---

## Memory System

The agent stores long-term memory using:

- SQLite + sqlite-vec (vector extension)
- Embedding model: `bge-m3` via Ollama
- Hybrid search: vector (0.7, SQLite) + text (0.3)

> Note: Vector search uses SQLite's internal vector store. Qdrant runs as a separate container and is queried manually via plugin — it is not yet integrated into the `memory_search` pipeline.
---

## Prerequisites

- Docker and Docker Compose on the agent node (NAS/server)
- Ollama running on a GPU machine reachable over the local network
- Models pulled on the Ollama host:
  ```bash
  ollama pull qwen3.5:9b-q4_K_M
  ollama pull qwen2.5:7b-instruct-q4_K_M
  ollama pull bge-m3
  ```

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/vanessa49/personal-ai-agent-lab.git
cd personal-ai-agent-lab

# Copy and edit the config
cp config/openclaw.json.example ~/.openclaw/config.json
# Replace <OLLAMA_HOST> with your GPU machine's IP
```

### 2. Edit `docker-compose.yml`

Replace the placeholder values:

```yaml
environment:
  - OLLAMA_HOST=http://<your-gpu-machine-ip>:11434
volumes:
  - /your/openclaw/config:/home/node/.openclaw
  - /your/ai-agent/path:/ai-agent
```

### 3. Start services on the agent node

```bash
docker-compose up -d
```

### 4. Copy plugins and config into the container

```bash
# Copy project files into the container workspace
docker cp plugins/ openclaw:/ai-agent/plugins/
docker cp hooks/   openclaw:/ai-agent/hooks/
docker cp skills/  openclaw:/ai-agent/skills/
docker cp scripts/ openclaw:/ai-agent/scripts/

# Restart to load plugins
docker restart openclaw
```

### 5. Ingest conversation history (optional)

```bash
# Process conversation logs into memory
docker exec openclaw node /ai-agent/scripts/batch_process_conversations.js /ai-agent/memory/conversations

# Review generated training samples
docker exec -it openclaw node /ai-agent/scripts/review_samples.js 50
```

---

## OpenClaw Version Note

This project was built and tested on **OpenClaw `2026.3.11`** (as referenced in `config/openclaw.json.example`).

> **NAS / air-gapped environments:** If your agent node has no direct internet access, you cannot `docker pull` directly. Transfer the image manually:
>
> ```bash
> # On a machine with internet access:
> docker pull ghcr.io/openclaw/openclaw:latest
> docker save ghcr.io/openclaw/openclaw:latest | gzip > openclaw-latest.tar.gz
>
> # Transfer the file to your NAS, then on the NAS:
> docker load < openclaw-latest.tar.gz
> ```
>
> Check [ghcr.io/openclaw/openclaw](https://ghcr.io/openclaw/openclaw) for the latest available version.

To check which version is currently running on your agent node:

```bash
# Check the running container's image label
docker inspect openclaw --format '{{index .Config.Labels "org.opencontainers.image.version"}}'

# Or check via the config file inside the container
docker exec openclaw cat /home/node/.openclaw/config.json | grep lastTouchedVersion

# Or SSH into your NAS and run:
docker images ghcr.io/openclaw/openclaw
```

---

## Current Status

Working:
- Plugin system (all 6 plugins)
- Memory ingestion and hybrid search
- Conversation processing pipeline
- Training sample generation and review

In progress:
- Memory retrieval accuracy tuning
- Automated fine-tuning pipeline
- Agent activity dashboard

> Note: Qdrant is used for experimental diagnostics and is not yet integrated into the memory retrieval pipeline.

---

## Why This Project Exists

Cloud AI models — GPT, Claude, Gemini — are trained on the output of billions of people. They represent collective intelligence at scale: optimized to be useful to everyone, shaped by aggregate data and company priorities.

That's genuinely powerful. But "useful to everyone" is a different thing from "shaped by you."

The question this project is exploring: what if a local, fine-tunable model could grow alongside a specific person? Not just remembering preferences on top — but having its actual reasoning patterns, tendencies, and ways of approaching problems gradually shaped by one individual's interactions over time.

The key difference is ownership of growth. Cloud models evolve based on what the company decides. A local model can evolve based on what *you* actually do and think about.

This is an early experiment in that direction. The architecture is in place; the self-improvement loop is still being assembled.

---

## Long-Term Vision

- Remember past conversations across sessions
- Learn from historical interactions over time
- Adapt to the habits and preferences of a specific user
- Assist with research, knowledge management, and task automation
- Integrate with personal devices and local services

The agent is not meant to replace human thinking — it's meant to extend it.

---

## Disclaimer

This is a **research prototype**, not a production system. Expect rough edges.

---

## License

MIT
