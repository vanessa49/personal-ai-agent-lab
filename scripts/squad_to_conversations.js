#!/usr/bin/env node
/**
 * SQuAD → Conversation Markdown
 *
 * 将 SQuAD train-v1.1.json 转换为与个人对话相同的 ## USER / ## ASSISTANT 格式，
 * 使其可以直接走 cognitive_chunking.js → evaluate_cognitive_graphs.js 流程。
 *
 * SQuAD 结构：context + question + answer
 * 转换策略：
 *   - USER:      question（提问）
 *   - ASSISTANT: answer + 相关 context 片段（回答 + 依据）
 *
 * 这样生成的对话是单轮 QA，预期：
 *   - avg chain length ≈ 1.0（无修正链）
 *   - derives/refines 占比极低（无推理推进）
 *   - 与个人对话形成对比基线
 *
 * 用法：
 *   node scripts/squad_to_conversations.js [train-v1.1.json] [output_dir] [--limit 3000]
 */

'use strict';
const fs = require('fs');
const path = require('path');

const inputFile  = process.argv[2] || 'train-v1.1.json';
const outputDir  = process.argv[3] || 'squad_conversations';
const limitArg   = process.argv.indexOf('--limit');
const limit      = limitArg !== -1 ? parseInt(process.argv[limitArg + 1]) : 3000;

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

console.log(`读取: ${inputFile}`);
const raw = JSON.parse(fs.readFileSync(inputFile, 'utf-8'));

// SQuAD 固定时间戳（用于 cognitive_chunking 的时间字段，设为 2020-01-01）
const SQUAD_TIMESTAMP = '2020-01-01 00:00:00';

let count = 0;
let skipped = 0;

for (const article of raw.data) {
  if (count >= limit) break;

  const title = article.title || 'SQuAD';

  for (const para of article.paragraphs) {
    if (count >= limit) break;

    const context = para.context || '';

    for (const qa of para.qas) {
      if (count >= limit) break;

      const question = qa.question || '';
      const answers  = qa.answers || [];

      if (!question || answers.length === 0) {
        skipped++;
        continue;
      }

      // 取第一个答案
      const answer = answers[0].text || '';
      if (!answer) { skipped++; continue; }

      // 提取 context 中包含答案的句子（最多 2 句，作为 assistant 的依据）
      const answerStart = answers[0].answer_start;
      const contextSnippet = extractContextSnippet(context, answerStart, answer);

      // 生成 markdown
      const md = [
        `# ${title} - Q${count + 1}`,
        '',
        `**来源**: SQuAD v1.1`,
        `**创建时间**: ${SQUAD_TIMESTAMP}`,
        `**消息数**: 2`,
        '',
        '---',
        '',
        '## USER',
        '',
        question.trim(),
        '',
        '## ASSISTANT',
        '',
        contextSnippet
          ? `${answer.trim()}\n\n${contextSnippet}`
          : answer.trim(),
        '',
      ].join('\n');

      const filename = `squad_${String(count).padStart(5, '0')}.md`;
      fs.writeFileSync(path.join(outputDir, filename), md, 'utf-8');
      count++;
    }
  }
}

console.log(`生成: ${count} 个对话文件 → ${outputDir}/`);
console.log(`跳过: ${skipped} 条（无答案）`);
console.log(`\n下一步：`);
console.log(`  node scripts/cognitive_chunking.js ${outputDir} squad_cognitive`);
console.log(`  node scripts/evaluate_cognitive_graphs.js squad_cognitive/graphs`);

// ── 工具函数 ──────────────────────────────────────────────

/**
 * 从 context 中提取包含答案的句子片段
 * 返回格式：「依据：...」
 */
function extractContextSnippet(context, answerStart, answer) {
  if (!context || answerStart === undefined) return '';

  // 找答案所在句子的边界
  let start = answerStart;
  let end   = answerStart + answer.length;

  // 向前找句子开头
  while (start > 0 && !/[.!?。！？\n]/.test(context[start - 1])) start--;
  // 向后找句子结尾
  while (end < context.length && !/[.!?。！？\n]/.test(context[end])) end++;

  const sentence = context.slice(start, end + 1).trim();
  if (!sentence || sentence === answer.trim()) return '';

  return `（依据：${sentence}）`;
}
