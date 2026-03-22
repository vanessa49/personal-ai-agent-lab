---
name: auto-task-logger
description: "自动记录每次工具调用到 agent_log.md"
homepage: https://github.com/openclaw/openclaw
metadata:
  openclaw:
    emoji: "📝"
    events:
      - agent:tool:post
    install:
      - id: workspace
        kind: bundled
        label: Workspace Hook
---

# Auto Task Logger

在每次工具调用后自动触发，提醒 Agent 记录日志。

## 工作原理

1. 监听 agent:tool:post 事件（工具调用完成后）
2. 向 Agent 发送提示，要求记录日志
3. Agent 使用 read + write 组合追加日志

## 触发条件

监听以下工具的调用：
- write
- edit  
- exec
- read

## 记录格式

```
[YYYY-MM-DD HH:MM:SS] 工具：XXX | 参数：XXX | 结果：XXX
```

## 日志位置

`/ai-agent/logs/agent_log.md`

## 特点

- ✅ 自动触发，无需手动提醒
- ✅ 每次工具调用后都会记录
- ✅ 使用 read + write 组合避免覆盖
