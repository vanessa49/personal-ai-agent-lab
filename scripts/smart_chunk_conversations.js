#!/usr/bin/env node
/**
 * 智能对话分段器 - 完整版
 * 
 * 核心功能：
 * 1. 识别多轮迭代优化的对话，保持完整性
 * 2. 自动分割不相关的话题
 * 3. 生成高质量训练样本
 */

'use strict';
const fs = require('fs');
const path = require('path');

// ============ Part 1: 延续性判断 ============

function isContinuation(userMsg, prevUserMsg, prevAssistantMsg) {
  const msg = userMsg.toLowerCase();
  
  // 明确的延续词
  const continuationWords = [
    '再', '还', '另外', '此外', '补充', '继续', '能不能', '可以', '可否', 
    '帮我', '请', '优化', '改进', '完善', '调整', '修改', '换成', '改成',
    'also', 'additionally', 'furthermore', 'can you', 'could you', 'please'
  ];
  
  if (continuationWords.some(w => msg.includes(w))) return true;
  
  // 代词引用
  const pronouns = ['这个', '那个', '它', '这', '那', 'this', 'that', 'it'];
  if (pronouns.some(p => msg.startsWith(p)) && userMsg.length < 100) return true;
  
  // 简短追问
  if (userMsg.length < 50 && (userMsg.includes('?') || userMsg.includes('？'))) return true;
  
  // 引用前文关键词
  if (prevAssistantMsg) {
    const prevWords = prevAssistantMsg.split(/\s+/).filter(w => w.length > 3).slice(0, 30);
    const matchCount = prevWords.filter(w => userMsg.includes(w)).length;
    if (matchCount >= 2) return true;
  }
  
  return false;
}

function isNewTopic(userMsg) {
  const msg = userMsg.toLowerCase();
  const newTopicMarkers = [
    '换个话题', '另一个问题', '新问题', '问一下', '顺便问', '对了',
    'new topic', 'different question', 'by the way', 'btw'
  ];
  return newTopicMarkers.some(m => msg.includes(m));
}

// ============ Part 2: 分段算法 ============

function segmentConversation(turns) {
  const segments = [];
  let currentSegment = { turns: [], startIndex: 0 };
  
  for (let i = 0; i < turns.length; i++) {
    const turn = turns[i];
    
    // 第一个 turn 或者是 assistant 回复，直接加入
    if (i === 0 || turn.role === 'assistant') {
      currentSegment.turns.push(turn);
      continue;
    }
    
    // 这是一个 user turn，判断是否延续
    if (turn.role === 'user') {
      const prevUserTurn = currentSegment.turns.filter(t => t.role === 'user').slice(-1)[0];
      const prevAssistantTurn = currentSegment.turns.filter(t => t.role === 'assistant').slice(-1)[0];
      
      const isNewTopicMsg = isNewTopic(turn.content);
      const isContinuationMsg = isContinuation(
        turn.content,
        prevUserTurn?.content || '',
        prevAssistantTurn?.content || ''
      );
      
      // 判断是否需要切分
      const shouldSplit = isNewTopicMsg || (!isContinuationMsg && currentSegment.turns.length >= 4);
      
      if (shouldSplit && currentSegment.turns.length > 0) {
        // 保存当前段，开始新段
        segments.push(currentSegment);
        currentSegment = { turns: [turn], startIndex: i };
      } else {
        // 延续当前段
        currentSegment.turns.push(turn);
      }
    }
  }
  
  // 保存最后一段
  if (currentSegment.turns.length > 0) {
    segments.push(currentSegment);
  }
  
  return segments;
}

// ============ Part 3: 样本生成 ============

function scoreSegment(segment) {
  let score = 5;
  
  const turnCount = segment.turns.filter(t => t.role === 'user').length;
  const totalLength = segment.turns.reduce((sum, t) => sum + t.content.length, 0);
  const combined = segment.turns.map(t => t.content).join(' ').toLowerCase();
  
  // 多轮迭代加分（这是核心）
  if (turnCount >= 3) score += 2;
  if (turnCount >= 5) score += 1.5;
  if (turnCount >= 7) score += 1;
  
  // 内容丰富度
  if (totalLength > 2000) score += 1.5;
  if (totalLength > 5000) score += 1;
  
  // 技术关键词
  const techKeywords = ['docker', 'plugin', 'config', 'error', 'fix', 'deploy', 'api', 
                        'database', 'vector', 'qdrant', 'ollama', 'python', 'node', 
                        'typescript', 'openclaw', 'sqlite', 'feishu'];
  const techScore = techKeywords.filter(k => combined.includes(k)).length;
  score += Math.min(2, techScore * 0.3);
  
  // 代码块加分
  const codeBlockCount = segment.turns.filter(t => t.content.includes('```')).length;
  score += Math.min(2, codeBlockCount * 0.5);
  
  // 问题解决模式加分
  if (combined.match(/因为|原因|解决|方案|步骤|问题|错误|修复/)) score += 1;
  
  // 闲聊扣分
  const chatPatterns = ['天气', '你好', '谢谢', '再见', 'hello', 'thanks', 'bye'];
  if (chatPatterns.some(p => combined.includes(p)) && totalLength < 500) score -= 3;
  
  return Math.min(10, Math.max(0, score));
}

function generateSample(segment, filename) {
  // 构建完整的多轮对话
  const messages = segment.turns.map(t => ({
    role: t.role,
    content: t.content.trim()
  }));
  
  // 提取第一个用户消息作为 instruction
  const firstUser = messages.find(m => m.role === 'user')?.content || '';
  
  // 提取最后一个助手消息作为 output
  const lastAssistant = messages.filter(m => m.role === 'assistant').slice(-1)[0]?.content || '';
  
  // 构建 reasoning（包含完整上下文）
  const userCount = messages.filter(m => m.role === 'user').length;
  const reasoning = `多轮对话 (${userCount} 轮迭代优化) - 来源: ${filename}`;
  
  const score = scoreSegment(segment);
  
  return {
    instruction: firstUser.substring(0, 1000),  // 增加长度限制
    input: '',
    reasoning,
    output: lastAssistant.substring(0, 2000),  // 增加长度限制
    full_context: messages,  // 保存完整上下文供审核使用
    score: parseFloat(score.toFixed(1)),
    turn_count: userCount,
    timestamp: new Date().toISOString(),
    source: 'claude'
  };
}

// ============ Part 4: 主处理流程 ============

function parseConversation(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const turns = [];
  let currentTurn = null;
  let inCodeBlock = false;

  for (const line of lines) {
    if (line.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      if (currentTurn) currentTurn.content += line + '\n';
      continue;
    }

    if (!inCodeBlock && (line.match(/^##\s*(User|用户|Human|USER)/i) || line.startsWith('**User'))) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'user', content: '' };
    } else if (!inCodeBlock && (line.match(/^##\s*(Assistant|Claude|GPT|AI|ASSISTANT)/i) || line.startsWith('**Assistant'))) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'assistant', content: '' };
    } else if (currentTurn) {
      currentTurn.content += line + '\n';
    }
  }
  
  if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
  return turns;
}

function appendJsonl(filePath, data) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, JSON.stringify(data) + '\n', 'utf-8');
}

async function processWithSmartChunking(conversationsDir, dryRun = false) {
  const processedDir = path.join(conversationsDir, 'processed');
  if (!fs.existsSync(processedDir)) fs.mkdirSync(processedDir, { recursive: true });
  
  const files = fs.readdirSync(conversationsDir)
    .filter(f => f.endsWith('.md') && !f.startsWith('.'));
  
  let totalSegments = 0;
  let samplesCount = 0;
  let pendingCount = 0;
  let multiTurnCount = 0;
  
  console.log(`发现 ${files.length} 个对话文件`);
  if (dryRun) console.log('*** DRY RUN 模式 - 不会实际写入 ***\n');
  
  for (const file of files) {
    const filePath = path.join(conversationsDir, file);
    console.log(`\n处理: ${file}`);
    
    try {
      const turns = parseConversation(filePath);
      console.log(`  解析到 ${turns.length} 个对话轮次`);
      
      // 智能分段
      const segments = segmentConversation(turns);
      console.log(`  分成 ${segments.length} 个对话段`);
      
      for (const segment of segments) {
        const userTurnCount = segment.turns.filter(t => t.role === 'user').length;
        
        // 至少要有一问一答
        if (userTurnCount === 0 || segment.turns.length < 2) continue;
        
        totalSegments++;
        const sample = generateSample(segment, file);
        
        console.log(`    段 ${totalSegments}: ${userTurnCount} 轮, 分数 ${sample.score}`);
        
        if (sample.score >= 5) {
          if (!dryRun) {
            const targetFile = sample.score >= 7 
              ? '/ai-agent/training/dataset/samples.jsonl'
              : '/ai-agent/training/dataset/pending_review.jsonl';
            appendJsonl(targetFile, sample);
          }
          
          if (sample.score >= 7) {
            samplesCount++;
            if (userTurnCount >= 3) multiTurnCount++;
          } else {
            pendingCount++;
          }
        }
      }
      
      // 移动已处理文件
      if (!dryRun) {
        const dst = path.join(processedDir, file);
        fs.renameSync(filePath, dst);
      }
      
    } catch (e) {
      console.error(`  错误: ${e.message}`);
    }
  }
  
  // 汇报
  console.log('\n=== 智能分段处理完成 ===');
  console.log(`处理文件数: ${files.length}`);
  console.log(`生成对话段: ${totalSegments}`);
  console.log(`高质量样本: ${samplesCount} (其中多轮迭代: ${multiTurnCount})`);
  console.log(`待审核样本: ${pendingCount}`);
  console.log(`\n多轮迭代样本占比: ${((multiTurnCount / samplesCount) * 100).toFixed(1)}%`);
  
  if (!dryRun) {
    const logEntry = `[${new Date().toISOString()}] 智能分段: ${files.length} 文件 → ${totalSegments} 段 (${samplesCount} 高质量, ${multiTurnCount} 多轮)\n`;
    fs.appendFileSync('/ai-agent/logs/batch_process.log', logEntry, 'utf-8');
  }
}

// ============ 主程序 ============

const conversationsDir = process.argv[2] || '/ai-agent/memory/conversations';
const dryRun = process.argv.includes('--dry-run');

console.log('智能对话分段器');
console.log('================');
console.log(`输入目录: ${conversationsDir}`);
console.log(`模式: ${dryRun ? 'DRY RUN（预览）' : '正式处理'}`);
console.log('');

processWithSmartChunking(conversationsDir, dryRun).catch(console.error);
