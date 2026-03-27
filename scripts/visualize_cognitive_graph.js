#!/usr/bin/env node
/**
 * 认知图谱可视化工具
 * 
 * 用于查看切分后的认知节点和关系
 */

'use strict';
const fs = require('fs');

function visualizeGraph(graphPath) {
  const graph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));
  
  console.log('='.repeat(100));
  console.log(`认知图谱: ${graphPath}`);
  console.log('='.repeat(100));
  console.log(`节点数: ${graph.nodes.length}`);
  console.log(`边数: ${graph.edges.length}`);
  console.log('');
  
  // 统计关系类型
  const relationCounts = {};
  graph.edges.forEach(e => {
    relationCounts[e.relation] = (relationCounts[e.relation] || 0) + 1;
  });
  
  console.log('关系类型分布:');
  Object.entries(relationCounts).forEach(([rel, count]) => {
    console.log(`  ${rel}: ${count}`);
  });
  console.log('');
  
  // 显示节点和关系
  console.log('认知流程:');
  console.log('-'.repeat(100));
  
  graph.nodes.forEach((node, i) => {
    const roleIcon = node.role === 'user' ? '👤' : '🤖';
    const preview = node.content.substring(0, 80).replace(/\n/g, ' ');
    
    console.log(`\n${roleIcon} ${node.id}`);
    console.log(`   ${preview}${node.content.length > 80 ? '...' : ''}`);
    
    // 显示到下一个节点的关系
    const edge = graph.edges.find(e => e.from === node.id);
    if (edge) {
      const relationLabel = {
        'follows': '→ 顺序',
        'derives': '⇒ 推导',
        'refines': '⟳ 修正',
        'contrasts': '⇄ 对比',
        'responds': '↔ 回应'
      }[edge.relation] || edge.relation;
      
      console.log(`   ${relationLabel}`);
    }
  });
  
  console.log('\n' + '='.repeat(100));
}

function compareWithTraditional(graphPath) {
  const graph = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));
  
  // 统计用户-助手对话轮次
  let userCount = 0;
  let assistantCount = 0;
  graph.nodes.forEach(n => {
    if (n.role === 'user') userCount++;
    if (n.role === 'assistant') assistantCount++;
  });
  
  const traditionalSamples = Math.min(userCount, assistantCount);
  const cognitiveSamples = graph.edges.length;
  
  console.log('\n对比分析:');
  console.log('-'.repeat(100));
  console.log(`传统切分（对话对）: ${traditionalSamples} 个样本`);
  console.log(`认知切分（思考推进）: ${cognitiveSamples} 个样本`);
  console.log(`样本增加: ${((cognitiveSamples / traditionalSamples - 1) * 100).toFixed(1)}%`);
  console.log('');
  console.log('关键差异:');
  console.log('  传统: user → assistant (学习回答)');
  console.log('  认知: thought_t → thought_t+1 (学习思考)');
  console.log('-'.repeat(100));
}

// 主程序
const graphPath = process.argv[2];

if (!graphPath) {
  console.log('用法: node visualize_cognitive_graph.js <graph.json>');
  console.log('');
  console.log('示例:');
  console.log('  node visualize_cognitive_graph.js /ai-agent/training/cognitive/graphs/example.json');
  process.exit(1);
}

if (!fs.existsSync(graphPath)) {
  console.error(`文件不存在: ${graphPath}`);
  process.exit(1);
}

visualizeGraph(graphPath);
compareWithTraditional(graphPath);
