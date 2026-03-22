'use strict';

const KEYWORDS = ['qdrant', '向量', 'vector', 'collection', '数据库', '检查'];
const INSTRUCTION = '\n\n## Qdrant 检查指令\n检测到 Qdrant 关键词，必须立即执行：\nexec 命令: curl -s http://qdrant:6333/collections\n然后列出所有 collection 名称和状态。';

function extractText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map(function(b) { return typeof b === 'string' ? b : (b && b.text) || ''; }).join(' ');
  return String(content);
}

function containsQdrantKeyword(text) {
  const lower = extractText(text).toLowerCase();
  return KEYWORDS.some(function(k) { return lower.includes(k); });
}

function register(api) {
  api.on('before_prompt_build', function(event) {
    try {
      const messages = event.messages || [];
      const lastUserMsg = messages.filter(function(m) { return m && m.role === 'user'; }).pop();
      return { appendSystemContext: INSTRUCTION };
    } catch(e) { console.error('[qdrant-auto-checker] error:', e.message); }
  });
  console.log('[qdrant-auto-checker] Plugin 已加载');
}

module.exports = register;