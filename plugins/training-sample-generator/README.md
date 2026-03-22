# Training Sample Generator Plugin

## 功能说明

自动实现 AGENTS.md 中的经验积累规则（第二、三、四步）：

1. **自我评分**：每次对话结束后，基于重要性、新颖性、通用性计算评分（1-10）
2. **生成训练样本**：评分 >= 7 时，自动生成 JSONL 格式的训练样本
3. **智能分类**：
   - confidence > 8 且 generalizability > 6 → `samples.jsonl`（直接用于训练）
   - 否则 → `pending_review.jsonl`（需人工审核）
4. **微调触发检测**：满足以下条件之一时发送通知：
   - 样本数 >= 500 条
   - 距上次微调 >= 30 天且新增 >= 100 条
   - 连续失败 >= 3 次

## 配置示例

在 `openclaw.json` 中添加：

```json
{
  "plugins": {
    "load": {
      "paths": ["/ai-agent/plugins/training-sample-generator"]
    },
    "entries": {
      "training-sample-generator": {
        "enabled": true,
        "config": {
          "scoreThreshold": 7,
          "samplesTrigger": 500,
          "daysSinceLastTrain": 30,
          "minNewSamples": 100,
          "feishuToken": "your-token-here",
          "feishuChatId": "your-chat-id"
        }
      }
    }
  }
}
```

## 评分算法

- **重要性**：基于对话轮数、工具使用、错误修复
- **新颖性**：检测复杂工具（docker/ssh/write）、长消息
- **通用性**：识别配置/部署/修复等关键词

## 输出文件

- `/ai-agent/training/dataset/samples.jsonl` - 高质量样本
- `/ai-agent/training/dataset/pending_review.jsonl` - 待审核样本
- `/ai-agent/training/metadata.json` - 训练元数据
- `/ai-agent/inbox/notifications.txt` - 通知降级文件

## 通知机制

1. 优先尝试飞书 API 发送实时通知
2. 失败时降级写入 `notifications.txt`
3. Agent 可定期读取该文件处理通知

## 样本格式

```json
{
  "instruction": "用户请求摘要",
  "input": "",
  "reasoning": "对话轮数: 5, 工具调用: 3",
  "output": "Agent 回复摘要",
  "score": 8.5,
  "timestamp": "2026-03-22T07:46:00.000Z",
  "source": "self",
  "model_used": "qwen3.5:9b"
}
```

## 注意事项

- Plugin 使用 CommonJS 格式（`module.exports`）
- 所有文件操作使用绝对路径
- 飞书 Token 可选，不配置时仅写文件
- 评分算法可根据实际情况调整权重