#!/usr/bin/env node
/**
 * 认知图谱评估器
 *
 * 用法：
 *   # 单数据集
 *   node scripts/evaluate_cognitive_graphs.js <graphs_dir>
 *
 *   # 对比模式（论文 Table 1）
 *   node scripts/evaluate_cognitive_graphs.js --compare \
 *     --personal  test_output/cognitive/graphs \
 *     --baseline  squad_cognitive/graphs \
 *     --label-a   "Personal AI" \
 *     --label-b   "SQuAD"
 */
'use strict';

const fs   = require('fs');
const path = require('path');

// ── CLI 解析 ──────────────────────────────────────────────

const args = process.argv.slice(2);
const compareMode = args.includes('--compare');

let dirsToRun = [];

if (compareMode) {
  const get = (flag) => {
    const i = args.indexOf(flag);
    return i !== -1 ? args[i + 1] : null;
  };
  dirsToRun = [
    { dir: get('--personal'),  label: get('--label-a') || 'Personal AI' },
    { dir: get('--baseline'),  label: get('--label-b') || 'Baseline'    },
    { dir: get('--ablation'),  label: get('--label-c') || 'Ablation'    },
  ].filter(d => d.dir);
} else {
  const dir = args[0] || path.join(__dirname, '..', 'test_output', 'cognitive', 'graphs');
  dirsToRun = [{ dir, label: 'Dataset' }];
}

// ── 核心统计函数 ──────────────────────────────────────────

function analyzeGraphs(graphsDir) {
  if (!fs.existsSync(graphsDir)) {
    console.error(`目录不存在: ${graphsDir}`);
    process.exit(1);
  }

  const files = fs.readdirSync(graphsDir).filter(f => f.endsWith('.json'));
  if (files.length === 0) {
    console.error(`没有 .json 文件: ${graphsDir}`);
    process.exit(1);
  }

  let totalNodes = 0, totalEdges = 0;
  let pairEdges = 0, reasoningEdges = 0;
  let relationCounts = {};
  let assistantInitiated = 0;
  let depthHistogram = {};
  let chainLengths = [];
  let inputLengths = [];

  for (const file of files) {
    const data  = JSON.parse(fs.readFileSync(path.join(graphsDir, file), 'utf-8'));
    const nodes = data.nodes || [];
    const edges = data.edges || [];

    totalNodes += nodes.length;
    totalEdges += edges.length;

    // 收集 input 长度
    nodes.forEach(n => {
      if (n.content) inputLengths.push(n.content.length);
    });

    // 统一字段名（兼容 from/to 和 source/target）
    nodes.forEach(n => { n.id = String(n.id); });
    edges.forEach(e => {
      e.source   = String(e.source || e.from || '');
      e.target   = String(e.target || e.to   || '');
      e.type     = e.type || e.relation || 'unknown';
    });

    // 关系分布
    edges.forEach(e => {
      const t = e.type;
      relationCounts[t] = (relationCounts[t] || 0) + 1;

      if (t === 'responds') pairEdges++;
      else reasoningEdges++;

      const src = nodes.find(n => n.id === e.source);
      const tgt = nodes.find(n => n.id === e.target);
      if (src?.role === 'assistant' && tgt?.role === 'assistant') {
        assistantInitiated++;
      }
    });

    // 只统计 refines/contrasts 构成的修正链长度（不是整图深度）
    const refinementAdj = {};
    edges.filter(e => e.type === 'refines' || e.type === 'contrasts').forEach(e => {
      if (!refinementAdj[e.source]) refinementAdj[e.source] = [];
      refinementAdj[e.source].push(e.target);
    });

    const refinementTargets = new Set(
      edges.filter(e => e.type === 'refines' || e.type === 'contrasts').map(e => e.target)
    );

    function dfsChain(node, depth, visited = new Set()) {
      if (!refinementAdj[node] || visited.has(node)) return depth;
      visited.add(node);
      const depths = refinementAdj[node].map(n => dfsChain(n, depth + 1, new Set(visited)));
      return Math.max(...depths);
    }

    const chainStarts = Object.keys(refinementAdj).filter(n => !refinementTargets.has(n));
    if (chainStarts.length > 0) {
      chainStarts.forEach(n => {
        const d = dfsChain(n, 1);
        chainLengths.push(d);
        depthHistogram[d] = (depthHistogram[d] || 0) + 1;
      });
    } else {
      // 没有修正链，记录深度 1
      chainLengths.push(1);
      depthHistogram[1] = (depthHistogram[1] || 0) + 1;
    }
  }

  const total = pairEdges + reasoningEdges || 1;
  const avgChain = chainLengths.reduce((a, b) => a + b, 0) / (chainLengths.length || 1);
  const maxChain = Math.max(...chainLengths, 0);
  const avgInput = inputLengths.reduce((a, b) => a + b, 0) / (inputLengths.length || 1);

  // 关系熵
  const entropy = (() => {
    let e = 0;
    for (const k in relationCounts) {
      const p = relationCounts[k] / totalEdges;
      if (p > 0) e -= p * Math.log2(p);
    }
    return e;
  })();

  // 长链占比（≥ 4 步）
  const longChains = chainLengths.filter(d => d >= 4).length;
  const longChainRatio = longChains / (chainLengths.length || 1);

  return {
    graphs: files.length,
    totalNodes,
    totalEdges,
    pairEdges,
    reasoningEdges,
    infoPreserved: reasoningEdges / total,
    relationCounts,
    entropy,
    assistantInitiated,
    initiativeRatio: assistantInitiated / (totalEdges || 1),
    avgChain,
    maxChain,
    longChainRatio,
    depthHistogram,
    avgInput,
  };
}

// ── 输出函数 ──────────────────────────────────────────────

function printSingle(label, s) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`${label}`);
  console.log('='.repeat(60));

  console.log(`\nGraphs:  ${s.graphs}  |  Nodes: ${s.totalNodes}  |  Edges: ${s.totalEdges}`);

  console.log('\n--- Pair vs Trajectory ---');
  console.log(`Pair (responds):     ${s.pairEdges}`);
  console.log(`Reasoning edges:     ${s.reasoningEdges}`);
  console.log(`Info preserved:      ${(s.infoPreserved * 100).toFixed(1)}%`);

  console.log('\n--- Relation Distribution ---');
  const sorted = Object.entries(s.relationCounts).sort((a, b) => b[1] - a[1]);
  sorted.forEach(([k, v]) => {
    console.log(`  ${k.padEnd(18)} ${v}  (${(v / s.totalEdges * 100).toFixed(1)}%)`);
  });
  console.log(`  Entropy: ${s.entropy.toFixed(3)} bits`);

  console.log('\n--- Trajectory Depth ---');
  Object.keys(s.depthHistogram).sort((a, b) => a - b).forEach(d => {
    console.log(`  Depth ${d}: ${s.depthHistogram[d]}`);
  });
  console.log(`  Avg chain length:  ${s.avgChain.toFixed(2)}`);
  console.log(`  Max chain length:  ${s.maxChain}`);
  console.log(`  Long chain (≥4):   ${(s.longChainRatio * 100).toFixed(1)}%`);

  console.log('\n--- Content ---');
  console.log(`  Avg input length:  ${s.avgInput.toFixed(0)} chars`);
  console.log(`  Initiative ratio:  ${(s.initiativeRatio * 100).toFixed(1)}%`);
}

function printComparison(results) {
  console.log('\n' + '='.repeat(70));
  console.log('Paper Table 1 — Dataset Comparison');
  console.log('='.repeat(70));

  const labels = results.map(r => r.label);
  const stats  = results.map(r => r.stats);

  // 表头
  const col = 22;
  console.log('\nMetric'.padEnd(col) + labels.map(l => l.padEnd(col)).join(''));
  console.log('-'.repeat(col + col * labels.length));

  const row = (name, fn) =>
    console.log(name.padEnd(col) + stats.map(s => String(fn(s)).padEnd(col)).join(''));

  row('Graphs',           s => s.graphs);
  row('Nodes',            s => s.totalNodes);
  row('Edges',            s => s.totalEdges);
  row('Avg chain length', s => s.avgChain.toFixed(2));
  row('Max chain length', s => s.maxChain);
  row('Long chain (≥4)',  s => (s.longChainRatio * 100).toFixed(1) + '%');
  row('Info preserved',   s => (s.infoPreserved * 100).toFixed(1) + '%');
  row('Relation entropy', s => s.entropy.toFixed(3) + ' bits');
  row('derives+refines',  s => {
    const d = (s.relationCounts['derives'] || 0) + (s.relationCounts['refines'] || 0);
    return (d / s.totalEdges * 100).toFixed(1) + '%';
  });
  row('responds',         s => ((s.relationCounts['responds'] || 0) / s.totalEdges * 100).toFixed(1) + '%');
  row('Initiative ratio', s => (s.initiativeRatio * 100).toFixed(1) + '%');
  row('Avg input length', s => s.avgInput.toFixed(0) + ' chars');

  console.log('\n--- TSV (copy to spreadsheet) ---');
  console.log('Metric\t' + labels.join('\t'));
  const tsv = (name, fn) => console.log(name + '\t' + stats.map(fn).join('\t'));
  tsv('Graphs',           s => s.graphs);
  tsv('AvgChain',         s => s.avgChain.toFixed(2));
  tsv('MaxChain',         s => s.maxChain);
  tsv('LongChain≥4',      s => (s.longChainRatio * 100).toFixed(1) + '%');
  tsv('InfoPreserved',    s => (s.infoPreserved * 100).toFixed(1) + '%');
  tsv('RelationEntropy',  s => s.entropy.toFixed(3));
  tsv('derives+refines',  s => {
    const d = (s.relationCounts['derives'] || 0) + (s.relationCounts['refines'] || 0);
    return (d / s.totalEdges * 100).toFixed(1) + '%';
  });
  tsv('AvgInputLength',   s => s.avgInput.toFixed(0));
}

// ── 主流程 ────────────────────────────────────────────────

const results = dirsToRun.map(({ dir, label }) => {
  console.log(`\n分析: ${label}  (${dir})`);
  const stats = analyzeGraphs(dir);
  return { label, stats };
});

if (compareMode) {
  results.forEach(({ label, stats }) => printSingle(label, stats));
  printComparison(results);
} else {
  printSingle(results[0].label, results[0].stats);
}
