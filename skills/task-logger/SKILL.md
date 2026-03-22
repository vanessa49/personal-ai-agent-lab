---
name: auto_task_logger
description: Automatically log completed tasks to agent_log.md with experience scoring
version: 1.0.0
requirements: ["bash"]
---

# Auto Task Logger

## 触发条件

在以下情况自动使用此 skill：
- 完成任何用户任务后
- 用户说"完成"、"done"、"搞定"
- 用户说"记录任务"、"写日志"

## 执行步骤

### 1. 记录任务日志

调用 `bash` tool 获取时间：
```bash
date '+%Y-%m-%d %H:%M:%S'
```

调用 `write` tool（追加模式）写入 `/ai-agent/logs/agent_log.md`：
```
[YYYY-MM-DD HH:MM:SS] 任务标题
用户请求：{原始请求}
执行过程：{简要描述}
最终结果：{成功/失败 + 原因}
使用工具：{工具列表}
---

```

### 2. 经验评分

对任务进行 0-10 评分：
- **重要性**：这个任务对系统有多重要？
- **新颖性**：是否是首次遇到的问题？
- **通用性**：解法是否可复用？

计算平均分：`score = (重要性 + 新颖性 + 通用性) / 3`

### 3. 训练样本生成（仅当 score >= 7）

如果平均分 >= 7，生成 JSONL 格式训练样本并进行自我审查。

如果 `confidence > 8 且 generalizability > 6`：
- 调用 `write` tool 追加到 `/ai-agent/training/dataset/samples.jsonl`

否则：
- 调用 `write` tool 追加到 `/ai-agent/training/dataset/pending_review.jsonl`

## 规则

- **必须使用 `write` tool**，不能只是"说"要写
- **每次任务完成后自动执行**
- **不要记录"记录日志"这个操作本身**（避免递归）