---
name: qdrant_check
description: 检查 Qdrant 向量数据库状态
version: 1.0.0
requirements: ["bash"]
---

# Qdrant Check

## 触发条件

当用户说以下任何词时：
- "检查 Qdrant"、"Qdrant 状态"
- "向量库状态"、"检查向量数据库"

## 执行步骤

1. 调用 `bash` tool 执行：
   ```bash
   curl -s http://qdrant:6333/collections
   ```

2. 解析 JSON 响应，格式化回复：
   ```
   📊 Qdrant 状态报告
   
   ✅ 运行正常
   
   Collections:
   - memory: X vectors
   - skills: Y vectors
   - cognition: Z vectors
   ```

3. 如果连接失败，回复错误信息和排查建议

## 规则

- 在容器内使用 `qdrant:6333`，不是 `192.168.0.200:6333`
- 每次检查后自动调用 task-logger skill 记录