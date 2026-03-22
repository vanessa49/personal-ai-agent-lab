#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function appendJsonl(filePath, data) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, JSON.stringify(data) + '\n', 'utf-8');
}

// 解析 markdown 对话文件（适配 seeds_to_memory.py 输出格式）
function parseConversation(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const turns = [];
  let currentTurn = null;
  let inCodeBlock = false;

  for (const line of lines) {
    // 检测代码块
    if (line.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      if (currentTurn) currentTurn.content += line + '\n';
      continue;
    }

    // 检测角色标记（适配多种格式）
    if (!inCodeBlock && (line.match(/^##\s*(User|用户|Human)/i) || line.startsWith('**User'))) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'user', content: '' };
    } else if (!inCodeBlock && (line.match(/^##\s*(Assistant|Claude|GPT|AI)/i) || line.startsWith('**Assistant'))) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'assistant', content: '' };
    } else if (currentTurn) {
      currentTurn.content += line + '\n';
    }
  }
  
  if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
  return turns;
}

function scoreTurn(userMsg, assistantMsg) {
  let score = 5;
  const combined = (userMsg + ' ' + assistantMsg).toLowerCase();
  
  const techKeywords = ['docker', 'plugin', 'config', 'error', 'fix', 'deploy', 'api', 'database', 'vector', 'qdrant', 'ollama', 'python', 'node', 'typescript', 'openclaw', 'sqlite', 'feishu', 'hook', 'agent'];
  const matchedTech = techKeywords.filter(k => combined.includes(k)).length;
  score += Math.min(3, matchedTech * 0.5);
  
  if (assistantMsg.length > 500) score += 1;
  if (assistantMsg.includes('```')) score += 1.5;
  if (combined.match(/因为|原因|解决|方案|步骤|问题|错误|修复/)) score += 1;
  if (userMsg.length > 100 && assistantMsg.length > 300) score += 0.5;
  
  const chatPatterns = ['天气', '你好', '谢谢', '再见', 'hello', 'thanks', 'bye', '哈哈', '嗯嗯'];
  if (chatPatterns.some(p => combined.includes(p)) && assistantMsg.length < 200) score -= 3;
  
  return Math.min(10, Math.max(0, score));
}

function canExtractKnowledge(userMsg, assistantMsg) {
  const combined = userMsg + ' ' + assistantMsg;
  const hasProblem = /问题|错误|失败|bug|issue|报错/i.test(combined);
  const hasReason = /因为|原因|导致|由于|是因为/i.test(combined);
  const hasSolution = /解决|方案|修复|步骤|方法|可以用|建议/i.test(combined);
  const hasCode = assistantMsg.includes('```');
  
  return ((hasProblem && hasReason && hasSolution) || hasCode) && assistantMsg.length > 300;
}

function extractKnowledgeCard(userMsg, assistantMsg, filename) {
  const title = userMsg.substring(0, 50).replace(/[^\w\u4e00-\u9fa5]/g, '_');
  const category = assistantMsg.includes('docker') ? 'docker' : 
                   assistantMsg.includes('plugin') ? 'plugins' :
                   assistantMsg.includes('qdrant') || assistantMsg.includes('vector') ? 'vector-db' :
                   assistantMsg.includes('openclaw') ? 'openclaw' : 'general';
  
  return {
    category,
    filename: `${title}_${Date.now()}.md`,
    content: `# ${userMsg.split('\n')[0].substring(0, 100)}

## 问题
${userMsg.substring(0, 1000)}

## 解决方案
${assistantMsg.substring(0, 2000)}

## 元数据
- 来源文件: ${filename}
- 提取时间: ${new Date().toISOString()}
- 来源: Claude 历史对话
`
  };
}

async function processBatch(conversationsDir, dryRun = false) {
  const processedDir = path.join(conversationsDir, 'processed');
  if (!fs.existsSync(processedDir)) fs.mkdirSync(processedDir, { recursive: true });
  
  const files = fs.readdirSync(conversationsDir)
    .filter(f => f.endsWith('.md') && !f.startsWith('.'));
  
  let totalTurns = 0;
  let samplesCount = 0;
  let pendingCount = 0;
  let knowledgeCards = [];
  let processedFiles = [];
  
  console.log(`发现 ${files.length} 个对话文件`);
  if (dryRun) console.log('*** DRY RUN 模式 - 不会实际写入 ***\n');
  
  for (const file of files) {
    const filePath = path.join(conversationsDir, file);
    console.log(`处理: ${file}`);
    
    try {
      const turns = parseConversation(filePath);
      console.log(`  解析到 ${turns.length} 个对话轮次`);
      
      for (let i = 0; i < turns.length - 1; i += 2) {
        if (turns[i].role !== 'user' || !turns[i+1] || turns[i+1].role !== 'assistant') continue;
        
        const userMsg = turns[i].content.trim();
        const assistantMsg = turns[i+1].content.trim();
        
        if (!userMsg || !assistantMsg || userMsg.length < 10) continue;
        
        totalTurns++;
        const score = scoreTurn(userMsg, assistantMsg);
        
        if (score >= 5) {
          const sample = {
            instruction: userMsg.substring(0, 500),
            input: '',
            reasoning: `从历史对话提取 (${file})`,
            output: assistantMsg.substring(0, 1000),
            score: parseFloat(score.toFixed(1)),
            timestamp: new Date().toISOString(),
            source: 'claude'
          };
          
          if (!dryRun) {
            const targetFile = score >= 7 
              ? '/ai-agent/training/dataset/samples.jsonl'
              : '/ai-agent/training/dataset/pending_review.jsonl';
            appendJsonl(targetFile, sample);
          }
          
          if (score >= 7) samplesCount++;
          else pendingCount++;
          
          if (score >= 7 && canExtractKnowledge(userMsg, assistantMsg)) {
            knowledgeCards.push(extractKnowledgeCard(userMsg, assistantMsg, file));
          }
        }
      }
      
      processedFiles.push(file);
      
    } catch (e) {
      console.error(`  错误: ${e.message}`);
    }
  }
  
  // 写入知识卡片
  if (!dryRun) {
    for (const card of knowledgeCards) {
      const skillDir = `/ai-agent/skills/${card.category}`;
      if (!fs.existsSync(skillDir)) fs.mkdirSync(skillDir, { recursive: true });
      const skillPath = path.join(skillDir, card.filename);
      fs.writeFileSync(skillPath, card.content, 'utf-8');
    }
    
    // 移动已处理文件
    for (const file of processedFiles) {
      const src = path.join(conversationsDir, file);
      const dst = path.join(processedDir, file);
      fs.renameSync(src, dst);
    }
    
    // 写入处理日志
    const logEntry = `[${new Date().toISOString()}] 处理 ${processedFiles.length} 个文件, 生成 ${samplesCount} samples + ${pendingCount} pending, ${knowledgeCards.length} 知识卡片\n`;
    fs.appendFileSync('/ai-agent/logs/batch_process.log', logEntry, 'utf-8');
  }
  
  // 汇报
  console.log('\n=== 批量处理完成 ===');
  console.log(`处理文件数: ${processedFiles.length}`);
  console.log(`处理对话轮次: ${totalTurns}`);
  console.log(`生成训练样本: ${samplesCount} (samples.jsonl)`);
  console.log(`待审核样本: ${pendingCount} (pending_review.jsonl)`);
  console.log(`提炼知识卡片: ${knowledgeCards.length}`);
  
  if (knowledgeCards.length > 0) {
    console.log(`\n知识卡片分类:`);
    const categories = {};
    knowledgeCards.forEach(c => categories[c.category] = (categories[c.category] || 0) + 1);
    Object.entries(categories).forEach(([cat, count]) => console.log(`  ${cat}: ${count}`));
  }
  
  if (!dryRun) {
    console.log(`\n已处理文件移动到: ${processedDir}`);
  }
}

const conversationsDir = process.argv[2] || '/ai-agent/memory/conversations';
const dryRun = process.argv.includes('--dry-run');
processBatch(conversationsDir, dryRun).catch(console.error);