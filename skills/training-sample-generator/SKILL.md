---
name: training_sample_generator
description: 从任务经验生成训练样本
version: 1.0.0
requirements: ["bash"]
---

# Training Sample Generator

## 触发条件

当 task-logger skill 记录任务后，如果满足以下条件之一：
- 用户明确说"这个任务很重要"
- 任务涉及新技术或新方法
- 任务解决了复杂问题

## 执行步骤

1. **评分**：对任务进行评分（0-10）
   - 重要性、新颖性、通用性
   - 平均分 = (重要性 + 新颖性 + 通用性) / 3

2. **判断**：如果平均分 < 7，只记录日志，不生成样本

3. **生成样本**：创建 JSONL 格式训练样本

4. **自我审查**：
   - confidence（置信度 0-10）
   - generalizability（通用性 0-10）
   
   如果 confidence > 8 且 generalizability > 6：
   - 追加到 `/ai-agent/training/dataset/samples.jsonl`
   
   否则：
   - 追加到 `/ai-agent/training/dataset/pending_review.jsonl`

5. **检查微调触发条件**：
   ```bash
   wc -l /ai-agent/training/dataset/samples.jsonl
   ```
   
   如果 ≥ 500 条，通知用户

## 规则

- 不要为简单任务生成样本
- 敏感信息必须脱敏