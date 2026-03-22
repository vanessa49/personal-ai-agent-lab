/**
 * Qdrant Auto Checker Hook Handler
 * 
 * 检测到 Qdrant 相关请求时自动提醒 Agent
 */

const QDRANT_KEYWORDS = [
  'qdrant',
  '向量',
  'vector',
  'collection',
  '数据库',
  '检查',
];

const QDRANT_INSTRUCTION = `

🔍 Qdrant 检查指令（强制执行）：
用户提到了 Qdrant 相关内容，你必须立即执行：

\`\`\`bash
curl -s http://qdrant:6333/collections
\`\`\`

然后格式化回复结果，包括：
- Collections 列表
- 每个 collection 的向量数量
- 状态信息

`;

/**
 * 检查消息是否包含 Qdrant 关键词
 */
function containsQdrantKeyword(message: string): boolean {
  const lowerMessage = message.toLowerCase();
  return QDRANT_KEYWORDS.some(keyword => lowerMessage.includes(keyword));
}

/**
 * Hook 处理函数
 */
export default async function handler(event: any, context: any) {
  // 只处理 bootstrap 事件
  if (event.type !== 'agent:bootstrap') {
    return;
  }
  
  try {
    // 获取用户消息
    const userMessage = context?.userMessage || '';
    
    // 检查是否包含 Qdrant 关键词
    if (containsQdrantKeyword(userMessage)) {
      // 注入指令到 bootstrap 文件
      if (context.bootstrapFiles && Array.isArray(context.bootstrapFiles)) {
        context.bootstrapFiles.push({
          name: 'QDRANT_CHECK.md',
          path: '/ai-agent/.openclaw/QDRANT_CHECK.md',
          content: QDRANT_INSTRUCTION,
          missing: false,
        });
      }
    }
  } catch (err) {
    console.error('[qdrant-auto-checker] 处理失败:', err);
  }
}
