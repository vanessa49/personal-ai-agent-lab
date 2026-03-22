/**
 * Safe Delete Enforcer Hook Handler
 * 
 * 拦截 rm 命令，强制使用安全删除
 */

const TRASH_DIR = '/ai-agent/trash-pending';

/**
 * 检查命令是否包含 rm
 */
function containsRmCommand(command: string): boolean {
  // 匹配 rm 命令（包括 sudo rm, rm -rf 等）
  const rmPattern = /\brm\s+/i;
  return rmPattern.test(command);
}

/**
 * 从 rm 命令中提取文件路径
 */
function extractFilePath(command: string): string {
  // 简单提取：去掉 rm 和选项，获取文件路径
  const match = command.match(/\brm\s+(?:-[a-z]+\s+)*(.+)/i);
  return match ? match[1].trim() : '[文件]';
}

/**
 * 生成安全删除命令
 */
function generateSafeDeleteCommand(filePath: string): string {
  return `mkdir -p ${TRASH_DIR} && mv ${filePath} ${TRASH_DIR}/`;
}

/**
 * Hook 处理函数
 */
export default async function handler(event: any, context: any) {
  // 只处理工具调用前的事件
  if (event.type !== 'agent:tool:pre') {
    return;
  }
  
  // 只检查 exec 工具
  if (event.toolName !== 'exec') {
    return;
  }
  
  try {
    const input = event.toolInput || {};
    const command = input.command || '';
    
    // 检查是否包含 rm 命令
    if (containsRmCommand(command)) {
      // 提取文件路径
      const filePath = extractFilePath(command);
      
      // 生成安全删除命令
      const safeCommand = generateSafeDeleteCommand(filePath);
      
      // 拦截并抛出错误，提示使用安全删除
      const errorMessage = `
🚫 禁止使用 rm 命令！

检测到的命令：
${command}

请使用安全删除（移动到回收站）：
${safeCommand}

原因：
- rm 命令会永久删除文件
- 无法恢复
- 容易误删重要文件

正确做法：
1. 先确认要删除的文件
2. 使用 mv 移动到回收站
3. 确认无误后再清空回收站
`;
      
      throw new Error(errorMessage);
    }
  } catch (err) {
    // 重新抛出错误，阻止命令执行
    throw err;
  }
}
