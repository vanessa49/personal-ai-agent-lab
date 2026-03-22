---
name: safe-delete-enforcer
description: "拦截 rm 命令，强制使用安全删除"
homepage: https://github.com/openclaw/openclaw
metadata:
  openclaw:
    emoji: "🗑️"
    events:
      - agent:tool:pre
    install:
      - id: workspace
        kind: bundled
        label: Workspace Hook
---

# Safe Delete Enforcer

拦截包含 `rm` 命令的工具调用，强制使用安全删除（移动到回收站）。

## 工作原理

在 Agent 调用 exec 工具之前（pre 阶段），检查命令是否包含 `rm`。
如果包含，则：
1. 拦截命令执行
2. 提示 Agent 使用 `mv` 到回收站
3. 提供正确的命令示例

## 拦截规则

拦截以下命令：
- `rm file.txt`
- `rm -rf directory/`
- `sudo rm ...`
- 任何包含 `rm ` 的命令

## 安全删除命令

```bash
mkdir -p /ai-agent/trash-pending && mv [文件] /ai-agent/trash-pending/
```

## 特点

- ✅ 100% 拦截，防止误删
- ✅ 自动提示正确命令
- ✅ 保护重要文件

## 配置

无需配置，开箱即用。
