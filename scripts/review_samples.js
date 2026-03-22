#!/usr/bin/env node
'use strict';

const fs = require('fs');
const readline = require('readline');

const PENDING_FILE = '/ai-agent/training/dataset/pending_review.jsonl';
const SAMPLES_FILE = '/ai-agent/training/dataset/samples.jsonl';
const REJECTED_FILE = '/ai-agent/training/dataset/rejected.jsonl';

async function reviewSamples(batchSize = 50) {
  if (!fs.existsSync(PENDING_FILE)) {
    console.log('pending_review.jsonl 不存在');
    return;
  }

  const lines = fs.readFileSync(PENDING_FILE, 'utf-8').trim().split('\n').filter(l => l);
  if (lines.length === 0) {
    console.log('pending_review.jsonl 为空');
    return;
  }

  const toReview = lines.slice(0, Math.min(batchSize, lines.length));
  const remaining = lines.slice(toReview.length);

  console.log(`\n待审核: ${toReview.length} 条 (剩余 ${remaining.length} 条)\n`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  let approved = 0, rejected = 0, skipped = 0;

  for (let i = 0; i < toReview.length; i++) {
    const sample = JSON.parse(toReview[i]);
    
    console.log(`\n[${i + 1}/${toReview.length}] Score: ${sample.score}`);
    console.log(`Instruction: ${sample.instruction.substring(0, 200)}...`);
    console.log(`Output: ${sample.output.substring(0, 200)}...`);
    
    const answer = await new Promise(resolve => {
      rl.question('\n[y]通过 [n]拒绝 [s]跳过 [q]退出: ', resolve);
    });

    if (answer === 'q') {
      console.log('\n退出审核');
      remaining.unshift(...toReview.slice(i));
      break;
    } else if (answer === 'y') {
      fs.appendFileSync(SAMPLES_FILE, toReview[i] + '\n', 'utf-8');
      approved++;
    } else if (answer === 'n') {
      fs.appendFileSync(REJECTED_FILE, toReview[i] + '\n', 'utf-8');
      rejected++;
    } else {
      remaining.unshift(toReview[i]);
      skipped++;
    }
  }

  rl.close();

  // 更新 pending 文件
  fs.writeFileSync(PENDING_FILE, remaining.join('\n') + (remaining.length > 0 ? '\n' : ''), 'utf-8');

  console.log(`\n=== 审核完成 ===`);
  console.log(`通过: ${approved}, 拒绝: ${rejected}, 跳过: ${skipped}`);
  console.log(`剩余待审核: ${remaining.length}`);
  
  const samplesCount = fs.readFileSync(SAMPLES_FILE, 'utf-8').trim().split('\n').filter(l => l).length;
  console.log(`当前 samples 总数: ${samplesCount}`);
  if (samplesCount >= 500) {
    console.log('🎉 已达到 500 条，可以触发微调！');
  }
}

const batchSize = parseInt(process.argv[2]) || 50;
reviewSamples(batchSize).catch(console.error);