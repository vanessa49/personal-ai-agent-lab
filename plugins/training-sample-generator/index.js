'use strict';
const fs = require('fs');
const path = require('path');

function calculateScore(messages, toolCalls) {
  let importance = 5, novelty = 5, generalizability = 5;
  const turnCount = messages.filter(m => m.role === 'user').length;
  if (turnCount >= 5) importance += 2;
  if (toolCalls.length >= 3) importance += 1;
  if (toolCalls.some(t => t.includes('error') || t.includes('fix'))) importance += 1;
  const complexTools = ['docker', 'ssh_exec', 'write', 'read'];
  if (toolCalls.some(t => complexTools.some(ct => t.includes(ct)))) novelty += 2;
  if (messages.some(m => m.content && m.content.length > 500)) novelty += 1;
  const keywords = ['config', 'setup', 'install', 'deploy', 'fix', 'error'];
  if (messages.some(m => keywords.some(k => m.content && m.content.toLowerCase().includes(k)))) generalizability += 2;
  return Math.min(10, (importance + novelty + generalizability) / 3);
}

function extractSummary(messages) {
  const userMessages = messages.filter(m => m.role === 'user');
  const assistantMessages = messages.filter(m => m.role === 'assistant');
  const firstUser = userMessages[0]?.content?.substring(0, 200) || '';
  const lastAssistant = assistantMessages[assistantMessages.length - 1]?.content?.substring(0, 200) || '';
  return {
    instruction: firstUser,
    output: lastAssistant,
    reasoning: `对话轮数: ${userMessages.length}, 工具调用: ${assistantMessages.length}`
  };
}

function readJsonl(filePath) {
  if (!fs.existsSync(filePath)) return [];
  return fs.readFileSync(filePath, 'utf-8').trim().split('\n').filter(l => l).map(l => JSON.parse(l));
}

function appendJsonl(filePath, data) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, JSON.stringify(data) + '\n', 'utf-8');
}

function writeNotificationFile(message) {
  const notifPath = '/ai-agent/inbox/notifications.txt';
  const dir = path.dirname(notifPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(notifPath, `[${new Date().toISOString()}] ${message}\n`, 'utf-8');
}

function checkFinetuneTrigger(config) {
  const samplesPath = '/ai-agent/training/dataset/samples.jsonl';
  const metadataPath = '/ai-agent/training/metadata.json';
  if (!fs.existsSync(samplesPath)) return null;
  const samples = readJsonl(samplesPath);
  const totalSamples = samples.length;
  let metadata = { lastTrainDate: null, lastTrainSamples: 0, consecutiveFailures: 0 };
  if (fs.existsSync(metadataPath)) metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
  const newSamples = totalSamples - metadata.lastTrainSamples;
  const daysSinceTrain = metadata.lastTrainDate
    ? Math.floor((Date.now() - new Date(metadata.lastTrainDate).getTime()) / 86400000)
    : 999;
  if (totalSamples >= config.samplesTrigger) return { reason: '数据量', samples: totalSamples, newSamples };
  if (daysSinceTrain >= config.daysSinceLastTrain && newSamples >= config.minNewSamples) return { reason: '定期', samples: totalSamples, newSamples, days: daysSinceTrain };
  if (metadata.consecutiveFailures >= 3) return { reason: '能力下降', samples: totalSamples, failures: metadata.consecutiveFailures };
  return null;
}

function register(api) {
  const pluginConfig = {
    scoreThreshold: 7,
    samplesTrigger: 500,
    daysSinceLastTrain: 30,
    minNewSamples: 100
  };

  api.on('agent_end', async function(event, ctx) {
    try {
      const messages = event.messages || [];
      const toolCalls = messages
        .filter(m => m && m.role === 'toolResult' && m.toolName)
        .map(m => m.toolName);

      const score = calculateScore(messages, toolCalls);
      console.log('[training-sample-generator] score:', score.toFixed(1));

      if (score < pluginConfig.scoreThreshold) return;

      const summary = extractSummary(messages);
      const confidence = score;
      const generalizability = toolCalls.length >= 2 ? 7 : 5;
      const targetFile = (confidence > 8 && generalizability > 6)
        ? '/ai-agent/training/dataset/samples.jsonl'
        : '/ai-agent/training/dataset/pending_review.jsonl';

      appendJsonl(targetFile, {
        instruction: summary.instruction,
        input: '',
        reasoning: summary.reasoning,
        output: summary.output,
        score: parseFloat(score.toFixed(1)),
        timestamp: new Date().toISOString(),
        source: 'self',
        model_used: ctx.model || 'qwen3.5:9b'
      });
      console.log('[training-sample-generator] sample saved to', targetFile);

      const trigger = checkFinetuneTrigger(pluginConfig);
      if (trigger) {
        const message = `🔔 训练触发提醒\n当前训练样本：${trigger.samples} 条\n触发原因：${trigger.reason}\n建议操作：查看 /ai-agent/training/dataset/ 确认数据质量后回复「开始训练」`;
        writeNotificationFile(message);
        console.log('[training-sample-generator] trigger notification written');
      }
    } catch(e) {
      console.error('[training-sample-generator] error:', e.message);
    }
  });

  console.log('[training-sample-generator] Plugin 已加载');
}

module.exports = register;