#!/usr/bin/env node
'use strict';

const fs = require('fs');
const { execSync } = require('child_process');

const PENDING_FILE = '/ai-agent/training/dataset/pending_review.jsonl';
const AGENT_REVIEWED_FILE = '/ai-agent/training/dataset/agent_reviewed.jsonl';
const REVIEW_LOG = '/ai-agent/logs/agent_review.log';
const OLLAMA_URL = 'http://192.168.0.198:11434/api/generate';
const MODEL_NAME = 'qwen3.5:9b-q4_K_M';

function callOllama(prompt) {
  try {
    const payload = {
      model: MODEL_NAME,
      prompt: prompt,
      stream: false,
      options: { temperature: 0.3, num_predict: 80 }
    };
    
    const cmd = `curl -s -m 30 '${OLLAMA_URL}' -H 'Content-Type: application/json' -d '${JSON.stringify(payload).replace(/'/g, "'\\''")}'`;
    const result = execSync(cmd, { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });
    const parsed = JSON.parse(result);
    
    if (parsed.error) {
      console.error('  Ollama 错误:', parsed.error);
      return null;
    }
    
    return parsed.response || null;
  } catch (e) {
    console.error('  调用失败:', e.message.substring(0, 100));
    return null;
  }
}

async function reviewWithAgent() {
  console.log('测试 Ollama 连接...');
  const testResponse = callOllama('你好');
  if (!testResponse) {
    console.log('✗ 连接失败');
    return;
  }
  console.log('✓ 连接成功\n');

  if (!fs.existsSync(PENDING_FILE)) {
    console.log('pending_review.jsonl 不存在');
    return;
  }

  const lines = fs.readFileSync(PENDING_FILE, 'utf-8').trim().split('\n').filter(l => l);
  console.log(`开始 Agent 审核，共 ${lines.length} 条样本\n`);

  let processed = 0, approved = 0, rejected = 0, failed = 0;

  for (const line of lines) {
    const sample = JSON.parse(line);
    
    const prompt = `你是训练数据质量评审专家。评估此对话样本是否适合AI训练。

评估标准：有明确问题和解决方案、有技术价值、回答质量高、非闲聊。

样本：
指令: ${sample.instruction.substring(0, 200).replace(/\n/g, ' ').replace(/"/g, '\\"')}
输出: ${sample.output.substring(0, 200).replace(/\n/g, ' ').replace(/"/g, '\\"')}
评分: ${sample.score}

回答格式：[通过/拒绝] 理由（15字内）`;

    const response = callOllama(prompt);
    
    if (!response) {
      failed++;
      processed++;
      console.log(`[${processed}/${lines.length}] ✗ 失败`);
      continue;
    }

    const isApproved = response.includes('通过');
    const reason = response.substring(0, 60).replace(/\n/g, ' ');

    const reviewed = {
      ...sample,
      agent_decision: isApproved ? 'approved' : 'rejected',
      agent_reason: reason,
      agent_review_time: new Date().toISOString()
    };

    fs.appendFileSync(AGENT_REVIEWED_FILE, JSON.stringify(reviewed) + '\n', 'utf-8');
    
    if (isApproved) approved++;
    else rejected++;

    processed++;
    console.log(`[${processed}/${lines.length}] ${isApproved ? '✓' : '✗'} | ${reason.substring(0, 30)}`);

    if (processed % 10 === 0) {
      const log = `[${new Date().toISOString()}] 已处理 ${processed}/${lines.length}, 通过 ${approved}, 拒绝 ${rejected}, 失败 ${failed}\n`;
      fs.appendFileSync(REVIEW_LOG, log, 'utf-8');
      console.log(`  进度: ${(processed / lines.length * 100).toFixed(1)}%`);
    }

    // 每条间隔 3 秒
    const start = Date.now();
    while (Date.now() - start < 3000) {}
  }

  console.log(`\n=== Agent 审核完成 ===`);
  console.log(`总计: ${processed}, 通过: ${approved}, 拒绝: ${rejected}, 失败: ${failed}`);
  console.log(`成功率: ${((processed - failed) / processed * 100).toFixed(1)}%`);
  console.log(`结果: ${AGENT_REVIEWED_FILE}`);
}

reviewWithAgent().catch(console.error);