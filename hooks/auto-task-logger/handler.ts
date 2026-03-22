import fs from 'node:fs/promises';
import path from 'node:path';

const LOG_FILE = '/ai-agent/logs/agent_log.md';

function formatTimestamp(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function extractToolInfo(event) {
  const toolName = event.toolName || 'unknown';
  const params = event.params || {};
  
  let details = '';
  if (params.path) {
    details = ` | 路径: ${params.path}`;
  } else if (params.command) {
    details = ` | 命令: ${params.command.substring(0, 50)}`;
  }
  
  return `工具: ${toolName}${details}`;
}

export default async function handler(event) {
  try {
    // 只处理工具调用后事件
    if (event.type !== 'agent:tool:post') return;
    
    // 确保日志目录存在
    const logDir = path.dirname(LOG_FILE);
    await fs.mkdir(logDir, { recursive: true });
    
    // 格式化日志条目
    const timestamp = formatTimestamp(new Date());
    const toolInfo = extractToolInfo(event);
    const logEntry = `[${timestamp}] ${toolInfo}\n`;
    
    // 追加到日志文件
    await fs.appendFile(LOG_FILE, logEntry, 'utf-8');
  } catch (err) {
    console.error('[auto-task-logger] 记录失败:', err);
  }
}
