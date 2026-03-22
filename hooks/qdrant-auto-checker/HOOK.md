---
name: qdrant-auto-checker
description: "检测到 Qdrant 相关请求时自动提醒 Agent"
homepage: https://github.com/openclaw/openclaw
metadata:
  openclaw:
    emoji: "🔍"
    events:
      - agent:bootstrap
    install:
      - id: workspace
        kind: bundled
        label: Workspace Hook
---

# Qdrant Auto Checker

当用户消息包含 Qdrant 相关关键词时，自动在系统 Prompt 中注入检查指令。

## 工作原理

在 Agent 启动时（bootstrap 阶段），检查用户消息是否包含：
- "qdrant"
- "向量"
- "vector"
- "collection"

如果包含，则在系统 Prompt 中注入强制指令。

## 注入的指令

```
🔍 Qdrant 检查指令（强制执行）：
用户提到了 Qdrant，你必须执行：
curl -s http://qdrant:6333/collections
然后格式化回复结果。
```

## 特点

- ✅ 关键词触发，自动注入
- ✅ 强制 Agent 执行检查命令
- ✅ 不依赖 AGENTS.md

## 配置

无需配置，开箱即用。
