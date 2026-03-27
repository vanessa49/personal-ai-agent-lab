#!/usr/bin/env node
/**
 * 关系类型发现分析器
 *
 * 用途：
 *   当认知图谱积累到一定量后，分析 graphs/*.json 里的边，
 *   找出数据里自然涌现的连接模式，为后期自定义 tags 提供依据。
 *
 * 分析维度：
 *   1. 内置 relation 分布（当前九类的比例）
 *   2. 节点内容的高频词对（from → to 的词汇变化）
 *   3. 角色转换模式（user→user / user→assistant / assistant→user）
 *   4. 修正链长度分布（单次修正 vs 多级修正）
 *   5. 候选自定义 tag（基于词汇共现聚类）
 *
 * 用法：
 *   node discover_relation_patterns.js [graphs目录] [--top 20]
 */

'use strict';
const fs = require('fs');
const path = require('path');

function loadAllGraphs(graphsDir) {
  if (!fs.existsSync(graphsDir)) {
    console.error(`目录不存在: ${graphsDir}`);
    process.exit(1);
  }
  const files = fs.readdirSync(graphsDir).filter(f => f.endsWith('.json'));
  console.log(`加载 ${files.length} 个图谱文件...`);

  const graphs = [];
  for (const file of files) {
    try {
      const g = JSON.parse(fs.readFileSync(path.join(graphsDir, file), 'utf-8'));
      graphs.push({ file, ...g });
    } catch (e) {
      console.warn(`  跳过 ${file}: ${e.message}`);
    }
  }
  return graphs;
}

// ── 分析1：relation 分布 ──────────────────────────────────────
function analyzeRelationDistribution(graphs) {
  const counts = {};
  let total = 0;
  for (const g of graphs) {
    for (const edge of (g.edges || [])) {
      counts[edge.relation] = (counts[edge.relation] || 0) + 1;
      total++;
    }
  }
  console.log('\n── 内置 relation 分布 ──────────────────────────────');
  Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .forEach(([rel, cnt]) => {
      const pct = ((cnt / total) * 100).toFixed(1);
      const bar = '█'.repeat(Math.round(cnt / total * 40));
      console.log(`  ${rel.padEnd(16)} ${String(cnt).padStart(5)}  ${pct.padStart(5)}%  ${bar}`);
    });
  console.log(`  ${'total'.padEnd(16)} ${String(total).padStart(5)}`);
  return counts;
}

// ── 分析2：角色转换模式 ───────────────────────────────────────
function analyzeRoleTransitions(graphs) {
  const patterns = {};
  for (const g of graphs) {
    const nodeMap = Object.fromEntries((g.nodes || []).map(n => [n.id, n]));
    for (const edge of (g.edges || [])) {
      const from = nodeMap[edge.from];
      const to   = nodeMap[edge.to];
      if (!from || !to) continue;
      const key = `${from.role}→${to.role} (${edge.relation})`;
      patterns[key] = (patterns[key] || 0) + 1;
    }
  }
  console.log('\n── 角色转换模式（Top 10）────────────────────────────');
  Object.entries(patterns)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .forEach(([pat, cnt]) => console.log(`  ${pat.padEnd(35)} ${cnt}`));
  return patterns;
}

// ── 分析3：修正链长度分布 ─────────────────────────────────────
function analyzeRefinementChains(graphs) {
  const chainLengths = [];
  for (const g of graphs) {
    // 找所有 refines/contrasts 边，构建修正链
    const refinedBy = {};
    for (const edge of (g.edges || [])) {
      if (edge.relation === 'refines' || edge.relation === 'contrasts') {
        refinedBy[edge.from] = edge.to;
      }
    }
    // 找链的起点（没有被其他节点修正的节点）
    const allTargets = new Set(Object.values(refinedBy));
    for (const startId of Object.keys(refinedBy)) {
      if (allTargets.has(startId)) continue; // 不是起点
      let len = 1;
      let cur = startId;
      const visited = new Set();
      while (refinedBy[cur] && !visited.has(cur)) {
        visited.add(cur);
        cur = refinedBy[cur];
        len++;
      }
      chainLengths.push(len);
    }
  }

  if (chainLengths.length === 0) {
    console.log('\n── 修正链：无数据');
    return;
  }

  const dist = {};
  chainLengths.forEach(l => { dist[l] = (dist[l] || 0) + 1; });
  console.log('\n── 修正链长度分布 ───────────────────────────────────');
  Object.entries(dist).sort((a, b) => a[0] - b[0]).forEach(([len, cnt]) => {
    console.log(`  长度 ${len}: ${cnt} 条`);
  });
  const avg = (chainLengths.reduce((a, b) => a + b, 0) / chainLengths.length).toFixed(2);
  console.log(`  平均链长: ${avg}`);
}

// ── 分析4：候选自定义 tag（高频词对变化）────────────────────────
function analyzeCandidateTags(graphs, topN = 20) {
  // 提取每条边 from→to 的内容，找高频的"转折词"
  const transitionWords = {};
  const correctionMarkers = [
    '但是', '但', '然而', '不过', '其实', '实际上', '换个角度',
    '更准确', '应该是', '重新', '所以', '因此', '意味着',
    '这说明', '总结', '归纳', '或许', '也许', '如果',
  ];

  for (const g of graphs) {
    const nodeMap = Object.fromEntries((g.nodes || []).map(n => [n.id, n]));
    for (const edge of (g.edges || [])) {
      const to = nodeMap[edge.to];
      if (!to) continue;
      for (const marker of correctionMarkers) {
        if (to.content.includes(marker)) {
          const key = `${marker} (→${edge.relation})`;
          transitionWords[key] = (transitionWords[key] || 0) + 1;
        }
      }
    }
  }

  console.log(`\n── 候选自定义 tag（高频转折词，Top ${topN}）──────────────`);
  console.log('  （这些词出现在 follows 类边里，可能值得细分为新 relation）');
  Object.entries(transitionWords)
    .filter(([k]) => k.includes('→follows'))  // 重点看被归为 follows 但含转折词的
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .forEach(([word, cnt]) => console.log(`  ${word.padEnd(30)} ${cnt}`));
}

// ── 分析5：tags 字段使用情况 ─────────────────────────────────
function analyzeExistingTags(graphs) {
  const tagCounts = {};
  let taggedEdges = 0;
  let totalEdges = 0;
  for (const g of graphs) {
    for (const edge of (g.edges || [])) {
      totalEdges++;
      if (edge.tags && edge.tags.length > 0) {
        taggedEdges++;
        for (const tag of edge.tags) {
          tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        }
      }
    }
  }
  console.log('\n── 自定义 tags 使用情况 ─────────────────────────────');
  console.log(`  已标注边: ${taggedEdges} / ${totalEdges}`);
  if (Object.keys(tagCounts).length > 0) {
    console.log('  Tag 分布:');
    Object.entries(tagCounts).sort((a, b) => b[1] - a[1])
      .forEach(([tag, cnt]) => console.log(`    ${tag}: ${cnt}`));
  } else {
    console.log('  （暂无自定义 tags，等数据积累后可手动或用脚本批量标注）');
  }
}

// ── 主程序 ────────────────────────────────────────────────────
const graphsDir = process.argv[2] || '/ai-agent/training/cognitive/graphs';
const topN = parseInt(process.argv[3]?.replace('--top', '') || '20');

console.log('关系类型发现分析器');
console.log('='.repeat(60));
console.log(`图谱目录: ${graphsDir}`);

const graphs = loadAllGraphs(graphsDir);
if (graphs.length === 0) {
  console.log('没有图谱数据，请先运行 cognitive_chunking.js');
  process.exit(0);
}

analyzeRelationDistribution(graphs);
analyzeRoleTransitions(graphs);
analyzeRefinementChains(graphs);
analyzeCandidateTags(graphs, topN);
analyzeExistingTags(graphs);

console.log('\n' + '='.repeat(60));
console.log('如果发现某类词汇高频出现在 follows 边里，');
console.log('可以考虑新增 relation 类型，或在 edge.tags 里标注。');
console.log('批量写入 tags 示例：');
console.log('  // 在 graphs/*.json 里找到目标边，手动加：');
console.log('  { "from": "node_3", "to": "node_4", "relation": "follows", "tags": ["analogy"] }');
