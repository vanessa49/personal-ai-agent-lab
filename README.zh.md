# Personal AI Agent Lab（个人 AI Agent 实验室）

> 基于对话历史与长期记忆，构建自我演化个人 AI Agent 的实验性系统。

**状态：研究原型 / 开发中**

---

## 项目理念

人的个性来自于记忆。对话、知识和经历，逐渐塑造了我们的思维方式和决策模式。

这个项目探索的核心问题是：

> 如果一个 LLM 能够访问自己的历史交互和学习记录，它是否会逐渐演化成一个个性化的数字认知助手？

目标是构建一个 AI Agent，让它的行为更像"另一个你"，而不是一个通用聊天机器人。

```
本地 LLM  +  长期记忆  +  对话历史  →  个性化 Agent
```

---

## 系统架构

本项目采用**分布式部署**方案：

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│   GPU 机器              │        │   NAS / 常驻服务器           │
│                         │        │                              │
│   Ollama                │◄──────►│   OpenClaw（Docker）         │
│   - qwen3.5:9b          │        │   - 插件系统                 │
│   - qwen2.5:7b          │        │   - 记忆（SQLite + vec）     │
│   - bge-m3（向量嵌入）  │        │   - 训练数据流水线           │
└─────────────────────────┘        │                              │
                                   │   Qdrant（Docker）           │
                                   │   - 向量检索                 │
                                   └──────────────────────────────┘
```

GPU 机器负责推理（Ollama），NAS/服务器通过 Docker 运行 OpenClaw 和 Qdrant，通过局域网连接 Ollama。

---

## 核心组件

### 插件（`/plugins`）

扩展 OpenClaw Agent 运行时的自定义行为：

| 插件 | 说明 |
|---|---|
| `tool-logger` | 记录每次工具调用到日志文件 |
| `task-logger` | 追踪 Agent 任务生命周期 |
| `safe-delete-enforcer` | 防止不安全的文件删除操作 |
| `qdrant-auto-checker` | 检测到向量数据库相关关键词时自动注入诊断指令 |
| `training-sample-generator` | 将对话自动转换为训练样本 |
| `memory-compressor` | 自动压缩过长的对话上下文 |

### Hooks（`/hooks`）

基于事件触发的 Agent 钩子：

| Hook | 触发时机 | 说明 |
|---|---|---|
| `auto-task-logger` | 任务事件 | 自动记录任务开始/结束 |
| `qdrant-auto-checker` | 关键词匹配 | 运行 Qdrant 健康检查 |
| `safe-delete-enforcer` | 工具调用前 | 拦截危险删除操作 |

### Skills（`/skills`）

加载到 Agent 上下文的可复用技能定义：

- `memory-compress` — 压缩和摘要记忆块
- `qdrant-check` — 诊断向量数据库状态
- `safe-delete` — 安全文件删除工作流
- `task-logger` — 结构化任务日志
- `training-sample-generator` — 从对话生成微调样本

### 脚本（`/scripts`）

训练数据流水线工具：

```
对话日志
    ↓
batch_process_conversations.js   # 解析和分块对话
    ↓
training-sample-generator        # 生成候选训练样本
    ↓
agent_review_samples.js/.py      # Agent 自动评审
    ↓
review_samples.js                # 人工审核界面
    ↓
微调数据集
```

---

## 记忆系统

Agent 使用以下方案存储长期记忆：

- SQLite + sqlite-vec（向量扩展）
- 嵌入模型：`bge-m3`（通过 Ollama）
- 混合检索：向量（0.7）+ 文本（0.3）

---

## 前置条件

- Agent 节点（NAS/服务器）已安装 Docker 和 Docker Compose
- GPU 机器运行 Ollama，且在局域网内可访问
- Ollama 主机已拉取所需模型：
  ```bash
  ollama pull qwen3.5:9b-q4_K_M
  ollama pull qwen2.5:7b-instruct-q4_K_M
  ollama pull bge-m3
  ```

---

## 快速开始

### 1. 克隆并配置

```bash
git clone https://github.com/vanessa49/personal-ai-agent-lab.git
cd personal-ai-agent-lab

# 复制并编辑配置文件
cp config/openclaw.json.example ~/.openclaw/config.json
# 将 <OLLAMA_HOST> 替换为你的 GPU 机器 IP
```

### 2. 编辑 `docker-compose.yml`

替换占位符：

```yaml
environment:
  - OLLAMA_HOST=http://<你的GPU机器IP>:11434
volumes:
  - /你的/openclaw/配置路径:/home/node/.openclaw
  - /你的/ai-agent/路径:/ai-agent
```

### 3. 在 Agent 节点启动服务

```bash
docker-compose up -d
```

### 4. 将插件和配置复制到容器

```bash
docker cp plugins/ openclaw:/ai-agent/plugins/
docker cp hooks/   openclaw:/ai-agent/hooks/
docker cp skills/  openclaw:/ai-agent/skills/
docker cp scripts/ openclaw:/ai-agent/scripts/

# 重启以加载插件
docker restart openclaw
```

### 5. 导入对话历史（可选）

```bash
# 将对话日志处理为记忆
docker exec openclaw node /ai-agent/scripts/batch_process_conversations.js /ai-agent/memory/conversations

# 审核生成的训练样本
docker exec -it openclaw node /ai-agent/scripts/review_samples.js 50
```

---

## OpenClaw 版本说明

本项目基于 **OpenClaw `2026.3.11`** 构建和测试（见 `config/openclaw.json.example` 中的 `lastTouchedVersion`）。

> **NAS / 离线环境注意：** 如果 Agent 节点无法直接访问互联网，无法直接 `docker pull`，需要手动转存镜像：
>
> ```bash
> # 在有网络的机器上：
> docker pull ghcr.io/openclaw/openclaw:latest
> docker save ghcr.io/openclaw/openclaw:latest | gzip > openclaw-latest.tar.gz
>
> # 将文件传输到 NAS，然后在 NAS 上执行：
> docker load < openclaw-latest.tar.gz
> ```
>
> 最新版本请查看 [ghcr.io/openclaw/openclaw](https://ghcr.io/openclaw/openclaw)。

查看当前运行的 OpenClaw 版本：

```bash
# 查看容器镜像标签
docker inspect openclaw --format '{{index .Config.Labels "org.opencontainers.image.version"}}'

# 或查看容器内配置文件
docker exec openclaw cat /home/node/.openclaw/config.json | grep lastTouchedVersion

# SSH 到 NAS 后执行：
docker images ghcr.io/openclaw/openclaw
```

---

## 当前状态

已完成：
- 插件系统（全部 6 个插件）
- 记忆导入与混合检索
- 对话处理流水线
- 训练样本生成与审核

进行中：
- 记忆检索精度调优
- 自动化微调流水线
- Agent 活动仪表盘

---

## 为什么做这个项目

大多数现代 AI 助手是无状态的，每次对话都从零开始。

但人类的智能不是这样运作的——我们的个性、偏好和思维模式，是由积累的经历塑造的。

这个项目探索的是：当你给一个本地 LLM 提供持久记忆、个人知识库和基于真实使用的自我改进循环，会发生什么。

云端大模型反映的是人类的集体智慧。本地模型有潜力反映的是*个人*智慧。

---

## 长期愿景

- 跨会话记住历史对话
- 从历史交互中持续学习
- 适应特定用户的习惯和偏好
- 辅助研究、知识管理和任务自动化
- 与个人设备和本地服务集成

这个 Agent 不是为了取代人类思考，而是为了延伸它。

---

## 免责声明

这是一个**研究原型**，不适用于生产环境。

---

## License

MIT
