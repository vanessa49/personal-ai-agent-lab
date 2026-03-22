# Memory Compressor Plugin

## 功能说明

自动实现 AGENTS.md 中的对话压缩和日志压缩（第五、六步）：

### 第五步：对话记忆压缩
- 检测对话轮数，超过 20 轮时触发压缩
- 写入压缩请求文件，由 Agent 读取后执行压缩
- 生成摘要保存到 `/ai-agent/memory/short_term/summary_[日期].md`
- 发送飞书通知或写入通知文件

### 第六步：日志压缩
- 监控 `agent_log.md` 行数
- 超过 100 条时触发压缩
- 保留最新 20 条，将最早 80 条压缩为摘要
- 压缩后的摘要追加到文件开头

## 配置示例

在 `openclaw.json` 中添加：

```json
{
  "plugins": {
    "load": {
      "paths": [
        "/ai-agent/plugins/memory-compressor"
      ]
    },
    "entries": {
      "memory-compressor": {
        "enabled": true,
        "config": {
          "conversationTurnThreshold": 20,
          "logLineThreshold": 100,
          "keepRecentLogs": 20,
          "summaryMaxLength": 500,
          "feishuToken": "your-token-here",
          "feishuChatId": "your-chat-id"
        }
      }
    }
  }
}
```
## 工作流程
### 对话压缩流程
agent_end 事件触发，检查对话轮数
超过阈值时，写入 
compress_request.txt
Agent 读取该文件，调用 LLM 生成摘要
摘要保存到 memory/short_term/
发送通知
### 日志压缩流程
agent_end 事件触发，检查日志行数
超过阈值时，直接执行压缩
读取日志，提取最早 80 条和最新 20 条
生成简单摘要（统计信息）
重写日志文件：摘要 + 最新 20 条
## 输出文件
/ai-agent/memory/short_term/summary_[日期].md - 对话摘要
compress_request.txt
 - 压缩请求（触发 Agent）
notifications.txt
 - 通知降级文件
agent_log.md
 - 压缩后的日志
## 压缩请求格式
```
[COMPRESS_REQUEST]
Type: conversation
Turns: 25
Timestamp: 2026-03-22T08:00:00.000Z
Action: 请用 7B 模型对前 20 轮对话生成摘要（<=500字），保存到 /ai-agent/memory/short_term/summary_2026-03-22.md
```
## 注意事项
对话压缩需要 Agent 配合（Plugin 无法直接调用 LLM）
日志压缩是自动执行的，不需要 Agent 介入
飞书通知可选，不配置时仅写文件
压缩阈值可根据实际情况调整
7 天后的摘要需要手动或通过其他机制移入 long_term