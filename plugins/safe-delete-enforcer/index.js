'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');

const TRASH_DIR = '/ai-agent/trash-pending';
const TRASH_INDEX_DIR = '/ai-agent/trash-index';

function containsRmCommand(command) {
  return /\brm\s+/i.test(command);
}

function extractFilePath(command) {
  const match = command.match(/\brm\s+(?:-[a-z]+\s+)*(.+)/i);
  return match ? match[1].trim() : '[文件]';
}

function generateSafeDeleteCommand(filePath) {
  return 'mkdir -p ' + TRASH_DIR + ' && mv ' + filePath + ' ' + TRASH_DIR + '/';
}

function isMoveToTrash(command) {
  // 匹配 mv ... /ai-agent/trash-pending/... 的命令
  return /\bmv\b/.test(command) && command.includes(TRASH_DIR);
}

function extractMvPaths(command) {
  // 提取 mv <src> <dst> 的源路径
  const match = command.match(/\bmv\s+(?:-[a-z]+\s+)*(\S+)\s+(\S+)/);
  if (!match) return null;
  return { src: match[1], dst: match[2] };
}

function register(api) {
  // 原有逻辑：拦截 rm 命令
  api.on('before_tool_call', function(event) {
    if (event.toolName !== 'exec') return;
    const command = (event.params && event.params.command) || '';
    if (!containsRmCommand(command)) return;
    const filePath = extractFilePath(command);
    const safeCmd = generateSafeDeleteCommand(filePath);
    throw new Error(
      '[safe-delete] 禁止使用 rm 命令！\n' +
      '检测到: ' + command + '\n' +
      '请改用安全删除: ' + safeCmd
    );
  });

  // 新增：mv 到 trash-pending 后自动创建索引记录
  api.on('after_tool_call', async function(event) {
    if (event.toolName !== 'exec') return;
    if (event.error) return;
    const command = (event.params && event.params.command) || '';
    if (!isMoveToTrash(command)) return;

    try {
      const paths = extractMvPaths(command);
      if (!paths) return;

      const srcPath = paths.src;
      const fileName = path.basename(srcPath);
      const now = new Date().toISOString();

      const indexContent = [
        '# 软删除记录：' + fileName,
        '',
        '- 原始路径：' + srcPath,
        '- 移动目标：' + TRASH_DIR + '/' + fileName,
        '- 时间：' + now,
        '- 操作命令：' + command,
        ''
      ].join('\n');

      await fs.mkdir(TRASH_INDEX_DIR, { recursive: true });
      await fs.writeFile(
        path.join(TRASH_INDEX_DIR, fileName + '.md'),
        indexContent,
        'utf-8'
      );
      console.log('[safe-delete-enforcer] 索引已创建:', fileName + '.md');
    } catch (e) {
      console.error('[safe-delete-enforcer] 索引创建失败:', e.message);
    }
  });

  console.log('[safe-delete-enforcer] Plugin 已加载');
}

module.exports = register;