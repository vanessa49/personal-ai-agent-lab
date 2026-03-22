## 可用工具

### 文件操作
- `read` - 读取文件内容
- `write` - 写入文件（会覆盖原有内容）
- `edit` - 编辑文件（字符串精确替换，要求 oldStr 完全匹配包括空格和换行）

### 命令执行
- `exec` / `bash` - 执行 shell 命令

## 工具使用建议

### 追加内容到文件（推荐方法）
使用 read + write 组合：
```
1. read 文件获取现有内容
2. 拼接：现有内容 + 新内容
3. write 完整内容
```

### edit 工具使用注意
- edit 要求 oldStr 必须**完全精确匹配**文件中的文本
- 包括所有空格、换行符、缩进
- 不推荐用于日志追加，容易因匹配失败而出错

### exec 工具说明
- exec 已配置为无需审批，可直接执行
- 查询 Qdrant：curl -s http://qdrant:6333/collections
- 不要使用 qdrant_search 工具（不存在）

## 重要路径
- 日志：/ai-agent/logs/agent_log.md
- 回收站：/ai-agent/trash-pending/
- Qdrant：http://qdrant:6333
