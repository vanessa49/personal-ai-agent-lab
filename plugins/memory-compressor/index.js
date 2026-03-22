'use strict';
const fs = require('fs');
const path = require('path');

function writeNotificationFile(message) {
  const notifPath = '/ai-agent/inbox/notifications.txt';
  const dir = path.dirname(notifPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(notifPath, `[${new Date().toISOString()}] ${message}\n`, 'utf-8');
}

function generateSummary(messages, maxLength) {
  const userMsgs = messages.filter(m => m.role === 'user').slice(0, 20);
  const assistantMsgs = messages.filter(m => m.role === 'assistant').slice(0, 20);
  let summary = '## 对话摘要\n\n';
  summary += `对话轮数: ${userMsgs.length}\n`;
  summary += `主要话题: ${userMsgs[0]?.content?.substring(0, 100) || '未知'}\n\n### 关键交互\n`;
  for (let i = 0; i < Math.min(3, userMsgs.length); i++) {
    summary += `- 用户: ${userMsgs[i]?.content?.substring(0, 80) || ''}\n`;
    summary += `- 助手: ${assistantMsgs[i]?.content?.substring(0, 80) || ''}\n`;
  }
  return summary.substring(0, maxLength);
}

function compressLogs(logPath, keepRecent) {
  if (!fs.existsSync(logPath)) return 0;
  const lines = fs.readFileSync(logPath, 'utf-8').trim().split('\n').filter(l => l);
  if (lines.length <= keepRecent) return 0;
  const toCompress = lines.slice(0, -keepRecent);
  const toKeep = lines.slice(-keepRecent);
  const summary = `## 历史日志摘要 (${toCompress.length} 条)\n` +
    `时间范围: ${toCompress[0]?.match(/\[(.*?)\]/)?.[1] || ''} ~ ${toCompress[toCompress.length-1]?.match(/\[(.*?)\]/)?.[1] || ''}\n` +
    `总任务数: ${toCompress.length}\n\n---\n\n`;
  fs.writeFileSync(logPath, summary + toKeep.join('\n'), 'utf-8');
  return toCompress.length;
}

function checkLongTermMemory() {
  const shortTermDir = '/ai-agent/memory/short_term';
  const longTermDir = '/ai-agent/memory/long_term';
  if (!fs.existsSync(shortTermDir)) return [];
  const sevenDays = 7 * 24 * 60 * 60 * 1000;
  const moved = [];
  for (const file of fs.readdirSync(shortTermDir)) {
    if (!file.startsWith('summary_')) continue;
    const filePath = path.join(shortTermDir, file);
    if (Date.now() - fs.statSync(filePath).mtimeMs > sevenDays) {
      if (!fs.existsSync(longTermDir)) fs.mkdirSync(longTermDir, { recursive: true });
      fs.renameSync(filePath, path.join(longTermDir, file));
      moved.push(file);
    }
  }
  return moved;
}

function register(api) {
  const pluginConfig = {
    conversationTurnThreshold: 20,
    logLineThreshold: 100,
    keepRecentLogs: 20,
    summaryMaxLength: 500
  };

  api.on('agent_end', async function(event, ctx) {
    try {
      const messages = event.messages || [];
      const userTurns = messages.filter(m => m.role === 'user').length;

      if (userTurns >= pluginConfig.conversationTurnThreshold) {
        const summary = generateSummary(messages, pluginConfig.summaryMaxLength);
        const date = new Date().toISOString().split('T')[0];
        const summaryPath = `/ai-agent/memory/short_term/summary_${date}_${Date.now()}.md`;
        const dir = path.dirname(summaryPath);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(summaryPath, summary, 'utf-8');
        writeNotificationFile(`📝 对话记忆已压缩\n对话轮数: ${userTurns}\n摘要已保存: ${path.basename(summaryPath)}`);
        console.log('[memory-compressor] summary saved:', summaryPath);
      }

      const movedFiles = checkLongTermMemory();
      if (movedFiles.length > 0) {
        writeNotificationFile(`📦 记忆归档通知\n已将 ${movedFiles.length} 个摘要移入长期记忆`);
        console.log('[memory-compressor] moved to long_term:', movedFiles.length);
      }

      const logPath = '/ai-agent/logs/agent_log.md';
      if (fs.existsSync(logPath)) {
        const lines = fs.readFileSync(logPath, 'utf-8').trim().split('\n').filter(l => l);
        if (lines.length > pluginConfig.logLineThreshold) {
          const compressed = compressLogs(logPath, pluginConfig.keepRecentLogs);
          if (compressed) {
            writeNotificationFile(`🗜️ 日志已压缩\n压缩条目: ${compressed}\n保留最新: ${pluginConfig.keepRecentLogs}`);
            console.log('[memory-compressor] compressed', compressed, 'log entries');
          }
        }
      }
    } catch(e) {
      console.error('[memory-compressor] error:', e.message);
    }
  });

  console.log('[memory-compressor] Plugin 已加载');
}

module.exports = register;