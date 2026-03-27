#!/usr/bin/env node
/**
 * 审核样本工具 - 显示完整上下文
 * 
 * 用于人工审核时查看多轮对话的完整上下文
 */

'use strict';
const fs = require('fs');
const readline = require('readline');

function readJsonl(filePath) {
  if (!fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf-8')
    .trim()
    .split('\n')
    .filter(l => l)
    .map(l => JSON.parse(l));
}

function appendJsonl(filePath, data) {
  const dir = require('path').dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, JSON.stringify(data) + '\n', 'utf-8');
}

function displaySample(sample, index, total) {
  console.clear();
  console.log('='.repeat(80));
  console.log(`样本 ${index + 1} / ${total}`);
  console.log(`分数: ${sample.score} | 轮数: ${sample.turn_count || 1} | 来源: ${sample.source}`);
  console.log('='.repeat(80));
  console.log('');
  
  // 如果有完整上下文，显示多轮对话
  if (sample.full_context && sample.full_context.length > 0) {
    console.log('【完整对话上下文】');
    console.log('-'.repeat(80));
    
    for (let i = 0; i < sample.full_context.length; i++) {
      const msg = sample.full_context[i];
      const roleLabel = msg.role === 'user' ? '👤 USER' : '🤖 ASSISTANT';
      const turnNum = msg.role === 'user' 
        ? `[第 ${sample.full_context.slice(0, i + 1).filter(m => m.role === 'user').length} 轮]`
        : '';
      
      console.log(`\n${roleLabel} ${turnNum}`);
      console.log(msg.content.substring(0, 800));
      if (msg.content.length > 800) console.log('... (内容过长，已截断)');
    }
  } else {
    // 单轮对话（旧格式）
    console.log('【INSTRUCTION】');
    console.log(sample.instruction.substring(0, 500));
    if (sample.instruction.length > 500) console.log('... (已截断)');
    
    console.log('\n【OUTPUT】');
    console.log(sample.output.substring(0, 1000));
    if (sample.output.length > 1000) console.log('... (已截断)');
  }
  
  console.log('\n' + '='.repeat(80));
  console.log('操作: [y] 接受 | [n] 拒绝 | [s] 跳过 | [q] 退出');
  console.log('='.repeat(80));
}

async function reviewSamples(inputFile) {
  const samples = readJsonl(inputFile);
  
  if (samples.length === 0) {
    console.log('没有待审核样本');
    return;
  }
  
  console.log(`加载 ${samples.length} 个样本`);
  console.log('开始人工审核...\n');
  
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  let accepted = 0;
  let rejected = 0;
  let skipped = 0;
  
  for (let i = 0; i < samples.length; i++) {
    const sample = samples[i];
    displaySample(sample, i, samples.length);
    
    const answer = await new Promise(resolve => {
      rl.question('> ', resolve);
    });
    
    const choice = answer.trim().toLowerCase();
    
    if (choice === 'y') {
      appendJsonl('/ai-agent/training/dataset/samples.jsonl', sample);
      accepted++;
      console.log('✓ 已接受');
    } else if (choice === 'n') {
      appendJsonl('/ai-agent/training/dataset/rejected.jsonl', sample);
      rejected++;
      console.log('✗ 已拒绝');
    } else if (choice === 's') {
      skipped++;
      console.log('⊙ 已跳过');
    } else if (choice === 'q') {
      console.log('\n中止审核');
      break;
    } else {
      i--;  // 无效输入，重新显示
      console.log('无效输入，请重新选择');
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  
  rl.close();
  
  console.log('\n=== 审核完成 ===');
  console.log(`接受: ${accepted}`);
  console.log(`拒绝: ${rejected}`);
  console.log(`跳过: ${skipped}`);
}

const inputFile = process.argv[2] || '/ai-agent/training/dataset/pending_review.jsonl';
reviewSamples(inputFile).catch(console.error);
