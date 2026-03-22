---
name: safe_delete
description: 安全删除文件（软删除到回收站）
version: 1.0.0
requirements: ["bash"]
---

# Safe Delete

## 触发条件

当用户说"删除 [文件名]"或"rm [文件名]"时使用此 skill。

## 执行步骤

1. **确认操作**：先问用户："确认删除 [文件名] 吗？这将移动到回收站，可恢复。"

2. 用户确认后，执行：
   ```bash
   mkdir -p /ai-agent/trash-pending
   mkdir -p /ai-agent/trash-index
   mv [文件路径] /ai-agent/trash-pending/
   ```

3. 调用 `write` tool 创建索引文件 `/ai-agent/trash-index/[文件名].md`

4. 回复用户："🗑️ 已移至回收站：trash-pending/[文件名]"

## 规则

- **绝对禁止直接 rm**，必须先移动到 trash-pending
- 删除前必须确认
- 禁止删除的路径：/nas/Photos/, /nas/homes/, /nas/.system/