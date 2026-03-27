#!/usr/bin/env node
/**
 * 对比两种分段方法的效果
 * 
 * 用法：
 *   node compare_chunking_methods.js /path/to/conversation.md
 */

'use strict';
const fs = require('fs');

// ============ 旧方法：单轮切分 ============

function oldMethod_parseAndChunk(filePath) {
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

    if (!inCodeBlock && line.match(/^##\s*(User|用户|USER)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'user', content: '' };
    } else if (!inCodeBlock && line.match(/^##\s*(Assistant|ASSISTANT)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'assistant', content: '' };
    } else if (currentTurn) {
      currentTurn.content += line + '\n';
    }
  }
  
  if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
  
  // 单轮切分
  const samples = [];
  for (let i = 0; i < turns.length - 1; i += 2) {
    if (turns[i].role === 'user' && turns[i+1]?.role === 'assistant') {
      samples.push({
        turns: [turns[i], turns[i+1]],
        method: 'old'
      });
    }
  }
  
  return samples;
}

// ============ 新方法：智能分段 ============

function isContinuation(userMsg, prevAssistantMsg) {
  const msg = userMsg.toLowerCase();
  
  const continuationWords = [
    '再', '还', '另外', '此外', '补充', '继续', '能不能', '可以', 
    '优化', '改进', '完善', '调整', '修改', '换成', '改成'
  ];
  
  if (continuationWords.some(w => msg.includes(w))) return true;
  
  const pronouns = ['这个', '那个', '它', '这', '那'];
  if (pronouns.some(p => msg.startsWith(p)) && userMsg.length < 100) return true;
  
  if (userMsg.length < 50 && (userMsg.includes('?') || userMsg.includes('？'))) return true;
  
  if (prevAssistantMsg) {
    const prevWords = prevAssistantMsg.split(/\s+/).filter(w => w.length > 3).slice(0, 30);
    const matchCount = prevWords.filter(w => userMsg.includes(w)).length;
    if (matchCount >= 2) return true;
  }
  
  return false;
}

function isNewTopic(userMsg) {
  const msg = userMsg.toLowerCase();
  const markers = ['换个话题', '另一个问题', '新问题', '问一下', '顺便问'];
  return markers.some(m => msg.includes(m));
}

function newMethod_smartChunk(filePath) {
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

    if (!inCodeBlock && line.match(/^##\s*(User|用户|USER)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'user', content: '' };
    } else if (!inCodeBlock && line.match(/^##\s*(Assistant|ASSISTANT)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'assistant', content: '' };
    } else if (currentTurn) {
      currentTurn.content += line + '\n';
    }
  }
  
  if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
  
  // 智能分段
  const segments = [];
  let currentSegment = { turns: [] };
  
  for (let i = 0; i < turns.length; i++) {
    const turn = turns[i];
    
    if (i === 0 || turn.role === 'assistant') {
      currentSegment.turns.push(turn);
      continue;
    }
    
    if (turn.role === 'user') {
      const prevAssistant = currentSegment.turns.filter(t => t.role === 'assistant').slice(-1)[0];
      
      const shouldSplit = isNewTopic(turn.content) || 
                         (!isContinuation(turn.content, prevAssistant?.content || '') && 
                          currentSegment.turns.length >= 4);
      
      if (shouldSplit && currentSegment.turns.length > 0) {
        segments.push({ ...currentSegment, method: 'new' });
        currentSegment = { turns: [turn] };
      } else {
        currentSegment.turns.push(turn);
      }
    }
  }
  
  if (currentSegment.turns.length > 0) {
    segments.push({ ...currentSegment, method: 'new' });
  }
  
  return segments;
}

// ============ 对比展示 ============

function displayComparison(filePath) {
  console.log('='.repeat(100));
  console.log(`对话文件: ${filePath}`);
  console.log('='.repeat(100));
  console.log('');
  
  const oldSamples = oldMethod_parseAndChunk(filePath);
  const newSamples = newMethod_smartChunk(filePath);
  
  console.log('【旧方法：单轮切分】');
  console.log(`生成样本数: ${oldSamples.length}`);
  console.log('');
  
  oldSamples.forEach((sample, i) => {
    const userPreview = sample.turns[0].content.trim().substring(0, 60).replace(/\n/g, ' ');
    console.log(`  样本 ${i + 1}: ${userPreview}...`);
  });
  
  console.log('');
  console.log('-'.repeat(100));
  console.log('');
  
  console.log('【新方法：智能分段】');
  console.log(`生成样本数: ${newSamples.length}`);
  console.log('');
  
  newSamples.forEach((sample, i) => {
    const userCount = sample.turns.filter(t => t.role === 'user').length;
    const firstUser = sample.turns.find(t => t.role === 'user')?.content.trim().substring(0, 60).replace(/\n/g, ' ');
    const label = userCount >= 3 ? '🔥 多轮迭代' : '单轮';
    console.log(`  样本 ${i + 1} [${label}, ${userCount} 轮]: ${firstUser}...`);
  });
  
  console.log('');
  console.log('='.repeat(100));
  console.log('对比总结:');
  console.log(`  旧方法: ${oldSamples.length} 个样本（全部单轮）`);
  console.log(`  新方法: ${newSamples.length} 个样本（其中 ${newSamples.filter(s => s.turns.filter(t => t.role === 'user').length >= 3).length} 个多轮迭代）`);
  console.log(`  样本减少: ${((1 - newSamples.length / oldSamples.length) * 100).toFixed(1)}%（但质量更高）`);
  console.log('='.repeat(100));
  console.log('');
  
  // 详细展示第一个多轮样本
  const firstMultiTurn = newSamples.find(s => s.turns.filter(t => t.role === 'user').length >= 3);
  if (firstMultiTurn) {
    console.log('【多轮迭代样本示例】');
    console.log('-'.repeat(100));
    firstMultiTurn.turns.forEach((turn, i) => {
      const label = turn.role === 'user' ? '👤 USER' : '🤖 ASSISTANT';
      console.log(`\n${label} [Turn ${i + 1}]`);
      console.log(turn.content.trim().substring(0, 300));
      if (turn.content.length > 300) console.log('... (已截断)');
    });
    console.log('\n' + '-'.repeat(100));
  }
}

// ============ 主程序 ============

const filePath = process.argv[2];

if (!filePath) {
  console.log('用法: node compare_chunking_methods.js <对话文件.md>');
  console.log('');
  console.log('示例:');
  console.log('  node compare_chunking_methods.js /ai-agent/memory/conversations/example.md');
  process.exit(1);
}

if (!fs.existsSync(filePath)) {
  console.error(`文件不存在: ${filePath}`);
  process.exit(1);
}

displayComparison(filePath);
