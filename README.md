# Personal AI Agent Lab

[English](README.md) | [中文](README.zh.md)

> Experimental system for building a self-improving personal AI agent based on conversation history and long-term memory.

**Status: Research Prototype / Work in Progress**

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

---

## Key Components

### Plugins (`/plugins`)

Extend the OpenClaw agent runtime with custom behaviors:

| Plugin | Description |
|---|---|
| `tool-logger` | Records every tool call to a log file |
| `task-logger` | Tracks agent task lifecycle |
| `safe-delete-enforcer` | Prevents unsafe file deletion |
| `qdrant-auto-checker` | Injects diagnostics when vector DB keywords appear |
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

Utility scripts for the training pipeline:

```
conversation logs
      ↓
batch_process_conversations.js   # parse and chunk conversations
      ↓
training-sample-generator        # generate candidate samples
      ↓
agent_review_samples.js/.py      # agent auto-review
      ↓
review_samples.js                # human review interface
      ↓
fine-tuning dataset
```

---

## Memory System

The agent stores long-term memory using:

- SQLite + sqlite-vec (vector extension)
- Embedding model: `bge-m3` via Ollama
- Hybrid search: vector (0.7) + text (0.3)

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

---

## Why This Project Exists

Most modern AI assistants are stateless. Every conversation starts from zero.

Human intelligence doesn't work this way — our identity, preferences, and thinking patterns are shaped by accumulated experience.

This project explores what happens when you give a local LLM:
- persistent memory of past conversations
- a personal knowledge base
- a self-improvement loop driven by real usage

The hypothesis: a local model, trained on your own interactions, can gradually become something closer to a personalized cognitive assistant rather than a generic tool.

Cloud-scale models reflect collective human intelligence. Local models have the potential to reflect *personal* intelligence.

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
