#!/usr/bin/env node
/**
 * 个人对话 → 单轮 QA 格式（Ablation Study 用）
 *
 * 把个人对话的每一对 user/assistant turn 拆成独立的单轮对话，
 * 格式与 SQuAD 转换后完全一致，用于 ablation：
 *   同样的数据 + QA 切分 vs 认知切分 → 结构差异来自 pipeline 还是数据？
 *
 * 用法：
 *   node scripts/personal_to_qa.js <conversations_dir> <output_dir> [--limit 3000]
 */
'use strict';
const fs   = require('fs');
const path = require('path');

const inputDir  = process.argv[2] || 'test_output/personal_conversations';
const outputDir = process.argv[3] || 'test_output/personal_qa';
const limitArg  = process.argv.indexOf('--limit');
const limit     = limitArg !== -1 ? parseInt(process.argv[limitArg + 1]) : Infinity;

if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

const files = fs.readdirSync(inputDir).filter(f => f.endsWith('.md'));
console.log(`读取 ${files.length} 个对话文件: ${inputDir}`);

let count = 0;

for (const file of files) {
  if (count >= limit) break;

  const content = fs.readFileSync(path.join(inputDir, file), 'utf-8');
  const lines   = content.split('\n');

  // 提取时间戳
  let timestamp = '2023-01-01 00:00:00';
  for (let i = 0; i < Math.min(15, lines.length); i++) {
    const m = lines[i].match(/\*\*(?:创建时间|Created|Updated)\*\*[：:]\s*(.+)/);
    if (m) { timestamp = m[1].trim(); break; }
  }

  // 解析 turns
  const turns = [];
  let current = null;
  let inCode  = false;

  for (const line of lines) {
    if (line.startsWith('```')) { inCode = !inCode; if (current) current.content += line + '\n'; continue; }
    if (!inCode && line.match(/^##\s*(User|用户|USER|Human)/i)) {
      if (current?.content.trim()) turns.push(current);
      current = { role: 'user', content: '' };
    } else if (!inCode && line.match(/^##\s*(Assistant|ASSISTANT|Claude|AI)/i)) {
      if (current?.content.trim()) turns.push(current);
      current = { role: 'assistant', content: '' };
    } else if (current) {
      current.content += line + '\n';
    }
  }
  if (current?.content.trim()) turns.push(current);

  // 每对 user+assistant 生成一个独立 QA 文件
  for (let i = 0; i < turns.length - 1; i++) {
    if (count >= limit) break;
    const u = turns[i];
    const a = turns[i + 1];
    if (u.role !== 'user' || a.role !== 'assistant') continue;

    const question = u.content.trim();
    const answer   = a.content.trim();
    if (!question || !answer) continue;

    const md = [
      `# QA_${count}`,
      '',
      `**来源**: Personal AI (QA slice)`,
      `**创建时间**: ${timestamp}`,
      `**消息数**: 2`,
      '',
      '---',
      '',
      '## USER',
      '',
      question,
      '',
      '## ASSISTANT',
      '',
      answer,
      '',
    ].join('\n');

    fs.writeFileSync(
      path.join(outputDir, `qa_${String(count).padStart(6, '0')}.md`),
      md, 'utf-8'
    );
    count++;
  }
}

console.log(`生成: ${count} 个 QA 文件 → ${outputDir}/`);
console.log(`\n下一步：`);
console.log(`  node scripts/cognitive_chunking.js ${outputDir} test_output/personal_qa_cognitive`);
console.log(`  node scripts/evaluate_cognitive_graphs.js --compare --personal test_output/personal_graphs --baseline test_output/squad_cognitive/graphs --ablation test_output/personal_qa_cognitive/graphs --label-a "Personal AI (Cognitive)" --label-b "SQuAD" --label-c "Personal AI (QA slice)"`);
