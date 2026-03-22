'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');

const LOG_FILE = '/ai-agent/logs/agent_log.md';

function formatTimestamp() {
  const now = new Date();
  return now.toISOString().replace('T', ' ').substring(0, 19);
}

function extractUserRequest(messages) {
  const userMsgs = messages.filter(function(m) { return m && m.role === 'user'; });
  if (userMsgs.length === 0) return '未知';
  const lastMsg = userMsgs[userMsgs.length - 1];
  const content = lastMsg.content || '';
  if (typeof content === 'string') return content.substring(0, 100);
  if (Array.isArray(content)) {
    const text = content.map(function(b) { return typeof b === 'string' ? b : (b && b.text) || ''; }).join(' ');
    return text.substring(0, 100);
  }
  return String(content).substring(0, 100);
}

function extractToolsUsed(messages) {
  const tools = [];
  messages.forEach(function(m) {
    if (m && m.role === 'toolResult' && m.toolName) {
      if (tools.indexOf(m.toolName) === -1) tools.push(m.toolName);
    }
  });
  return tools.length > 0 ? tools.join(', ') : '无';
}

function register(api) {
  api.on('agent_end', async function(event, ctx) {
    try {
      const messages = event.messages || [];
      const userRequest = extractUserRequest(messages);
      const toolsUsed = extractToolsUsed(messages);
      const result = event.success ? '成功' : ('失败: ' + (event.error || '未知错误'));
      const model = ctx.model || 'qwen3.5:9b';
      
      const logLine = '[' + formatTimestamp() + '] 任务：对话完成 | 用户请求：' + userRequest + ' | 结果：' + result + ' | 工具：' + toolsUsed + ' | model_used：' + model + '\n';
      
      await fs.mkdir(path.dirname(LOG_FILE), { recursive: true });
      await fs.appendFile(LOG_FILE, logLine, 'utf-8');
      console.log('[task-logger] 日志已记录');
    } catch(e) {
      console.error('[task-logger] 记录失败:', e.message);
    }
  });
  
  console.log('[task-logger] Plugin 已加载');
}

module.exports = register;