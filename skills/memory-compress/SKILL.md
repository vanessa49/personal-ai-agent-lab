---
name: memory_compress
description: 压缩对话记忆为摘要
version: 1.0.0
requirements: ["bash"]
---

# Memory Compress

## 触发条件

以下任一情况触发：
- 对话轮次超过 20 轮
- 用户明确说"压缩记忆"、"生成摘要"

## 执行步骤

1. 读取当前对话历史（最近 20 轮）

2. 生成摘要（≤500字），包含：
   - 解决的问题（3-5条）
   - 未完成的任务（如有）
   - 重要决策或配置变更

3. 调用 `bash` tool 获取日期：`date '+%Y-%m-%d'`

4. 调用 `write` tool 保存到 `/ai-agent/memory/short_term/summary_[日期].md`

5. 回复用户："📝 对话记忆已压缩"

## 规则

- 摘要必须简洁，突出关键信息
- 不要包含敏感信息（密码、token等）
