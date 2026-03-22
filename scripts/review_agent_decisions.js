#!/usr/bin/env node
'use strict';

const fs = require('fs');
const readline = require('readline');

const AGENT_REVIEWED_FILE = '/ai-agent/training/dataset/agent_reviewed.jsonl';
const SAMPLES_FILE = '/ai-agent/training/dataset/samples.jsonl';
const REJECTED_FILE = '/ai-agent/training/dataset/rejected.jsonl';
const DISAGREEMENT_FILE = '/ai-agent/training/dataset/human_agent_disagreement.jsonl';

async function reviewAgentDecisions(batchSize = 50) {
  if (!fs.existsSync(AGENT_REVIEWED_FILE)) {
    console.log('agent_reviewed.jsonl 不存在，请先运行 agent 审核');
    return;
  }

  const lines = fs.readFileSync(AGENT_REVIEWED_FILE, 'utf-8').trim().split('\n').filter(l => l);
  if (lines.length === 0) {
    console.log('agent_reviewed.jsonl 为空');
    return;
  }

  const toReview = lines.slice(0, Math.min(batchSize, lines.length));
  const remaining = lines.slice(toReview.length);

  console.log(`\n待复核 Agent 决策: ${toReview.length} 条 (剩余 ${remaining.length} 条)\n`);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  let humanApproved = 0, humanRejected = 0, skipped = 0;
  let agreed = 0, disagreed = 0;

  for (let i = 0; i < toReview.length; i++) {
    const sample = JSON.parse(toReview[i]);
    
    console.log(`\n[${i + 1}/${toReview.length}] Score: ${sample.score}`);
    console.log(`🤖 Agent 决策: ${sample.agent_decision === 'approved' ? '✓ 通过' : '✗ 拒绝'}`);
    console.log(`🤖 Agent 理由: ${sample.agent_reason}`);
    console.log(`\nInstruction: ${sample.instruction.substring(0, 200)}...`);
    console.log(`Output: ${sample.output.substring(0, 200)}...`);
    
    const answer = await new Promise(resolve => {
      rl.question('\n👤 你的判断 [y]通过 [n]拒绝 [s]跳过 [q]退出: ', resolve);
    });

    if (answer === 'q') {
      console.log('\n退出复核');
      remaining.unshift(...toReview.slice(i));
      break;
    } else if (answer === 's') {
      remaining.unshift(toReview[i]);
      skipped++;
      continue;
    }

    const humanDecision = answer === 'y' ? 'approved' : 'rejected';
    const agentDecision = sample.agent_decision;

    // 记录人类决策
    const reviewed = {
      ...sample,
      human_decision: humanDecision,
      human_review_time: new Date().toISOString()
    };

    // 判断是否一致
    if (humanDecision === agentDecision) {
      agreed++;
      console.log('  ✓ 与 Agent 一致');
    } else {
      disagreed++;
      console.log('  ✗ 与 Agent 不一致 - 记录到 disagreement.jsonl');
      fs.appendFileSync(DISAGREEMENT_FILE, JSON.stringify(reviewed) + '\n', 'utf-8');
    }

    // 按人类决策分类
    if (humanDecision === 'approved') {
      fs.appendFileSync(SAMPLES_FILE, JSON.stringify(sample) + '\n', 'utf-8');
      humanApproved++;
    } else {
      fs.appendFileSync(REJECTED_FILE, JSON.stringify(sample) + '\n', 'utf-8');
      humanRejected++;
    }
  }

  rl.close();

  // 更新 agent_reviewed 文件
  fs.writeFileSync(AGENT_REVIEWED_FILE, remaining.join('\n') + (remaining.length > 0 ? '\n' : ''), 'utf-8');

  console.log(`\n=== 复核完成 ===`);
  console.log(`人类决策: 通过 ${humanApproved}, 拒绝 ${humanRejected}, 跳过 ${skipped}`);
  console.log(`与 Agent 一致: ${agreed}, 不一致: ${disagreed}`);
  console.log(`一致率: ${(agreed / (agreed + disagreed) * 100).toFixed(1)}%`);
  console.log(`剩余待复核: ${remaining.length}`);
  
  const samplesCount = fs.readFileSync(SAMPLES_FILE, 'utf-8').trim().split('\n').filter(l => l).length;
  console.log(`当前 samples 总数: ${samplesCount}`);
}

const batchSize = parseInt(process.argv[2]) || 50;
reviewAgentDecisions(batchSize).catch(console.error);