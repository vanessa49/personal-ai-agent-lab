#!/usr/bin/env node
/**
 * 认知切分器 (Cognitive Chunking)
 * 
 * 哲学：
 * - 不切分"对话"，而是切分"思考推进"
 * - 不规定思维类型（problem/analysis/solution）
 * - 只记录：思考从这里推进到了那里
 * 
 * 目标：Personal Cognitive Model，而不是 Personal Chatbot
 */

'use strict';
const fs = require('fs');
const path = require('path');

// ============ 认知事件检测 ============

/**
 * 检测思考焦点改变 (Topic Shift)
 * 例如：AI训练 → 数据结构 → chunking
 */
function detectTopicShift(text, prevText) {
  if (!prevText) return false;
  
  // 提取关键词（简单实现：长度>3的词）
  const extractKeywords = (t) => {
    return t.toLowerCase()
      .split(/[\s,，。.!！?？;；]+/)
      .filter(w => w.length > 3)
      .slice(0, 10);
  };
  
  const currKeywords = extractKeywords(text);
  const prevKeywords = extractKeywords(prevText);
  
  // 关键词重叠度
  const overlap = currKeywords.filter(k => prevKeywords.includes(k)).length;
  const overlapRatio = overlap / Math.max(currKeywords.length, 1);
  
  // 重叠度 < 30% 认为是话题转移
  return overlapRatio < 0.3;
}

/**
 * 检测推理推进 (Reasoning Step)
 * 例如：因为A → 所以B
 */
function detectReasoningStep(text) {
  const reasoningMarkers = [
    // 因果关系
    '所以', '因此', '因为', '由于', '导致', '意味着',
    'so', 'therefore', 'thus', 'hence', 'because', 'since',
    
    // 推理推进
    '这说明', '这表明', '可以推出', '也就是说','那不就说明','那不就是',
    'this means', 'this implies', 'in other words',
    
    // 结论
    '总结', '综上', '总之', '归纳',
    'in summary', 'to conclude', 'in conclusion'
  ];
  
  return reasoningMarkers.some(m => text.includes(m));
}

/**
 * 检测观点修正 (Correction)
 * 例如：原本以为A，但其实B
 */
function detectCorrection(text) {
  const correctionMarkers = [
    // 转折
    '但是', '但', '然而', '不过', '其实', '实际上',
    'but', 'however', 'actually', 'in fact',
    
    // 修正
    '更准确地说', '换句话说', '应该是', '更确切',
    'more precisely', 'rather', 'instead',
    
    // 反思
    '重新思考', '再想想', '仔细想想',
    'rethinking', 'on second thought'
  ];
  
  return correctionMarkers.some(m => text.includes(m));
}

/**
 * 检测新想法 (New Idea)
 */
function detectNewIdea(text) {
  const ideaMarkers = [
    '我突然意识到', '我想到', '有个想法', '一个思路',
    '可以这样','我突然想到',
    'I realize', 'I think', 'an idea', 'could be'
  ];
  
  return ideaMarkers.some(m => text.includes(m));
}

/**
 * 检测假设推理 (Hypothesis)
 * 例如：如果A，那么B
 */
function detectHypothesis(text) {
  const hypothesisMarkers = [
    '如果', '假设', '假如', '倘若', '要是',
    'if', 'suppose', 'assuming', 'what if', 'provided that'
  ];
  
  return hypothesisMarkers.some(m => text.includes(m));
}

/**
 * 检测思路重启 (Restart)
 * 例如：重新考虑、再想想
 */
function detectRestart(text) {
  const restartMarkers = [
    '重新', '再', '重', '从头', '重来',
    '重新思考', '再想想', '再看看', '重新考虑',
    'restart', 'again', 'reconsider', 'start over', 're-'
  ];
  
  return restartMarkers.some(m => text.includes(m));
}

/**
 * 检测澄清说明 (Clarification)
 * 例如：更准确地说、换句话说
 */
function detectClarification(text) {
  const clarificationMarkers = [
    '更准确', '更确切', '准确地说', '确切地说',
    '换句话说', '也就是', '具体来说', '详细说',
    'more precisely', 'more accurately', 'to be clear',
    'in other words', 'specifically', 'to clarify'
  ];
  
  return clarificationMarkers.some(m => text.includes(m));
}

/**
 * 检测推测 (Speculation)
 * 例如：或许、也许、可能
 */
function detectSpeculation(text) {
  const speculationMarkers = [
    '或许', '也许', '可能', '大概', '估计', '应该',
    'maybe', 'perhaps', 'possibly', 'probably', 'might'
  ];
  
  return speculationMarkers.some(m => text.includes(m));
}

/**
 * 检测视角变化 (Perspective Shift)
 */
function detectPerspectiveShift(text) {
  const perspectiveMarkers = [
    '换个角度', '从另一个角度', '反过来看', '站在',
    '如果从', '换个思路','那如果说',
    'from another perspective', 'on the other hand',
    'alternatively', 'conversely'
  ];
  
  return perspectiveMarkers.some(m => text.includes(m));
}

/**
 * 综合判断：是否发生了认知事件
 */
function isCognitiveEvent(text, prevText) {
  // 太短的文本不算独立认知事件
  if (text.length < 20) return false;
  
  return (
    detectTopicShift(text, prevText) ||
    detectReasoningStep(text) ||
    detectCorrection(text) ||
    detectNewIdea(text) ||
    detectPerspectiveShift(text)
  );
}

// ============ 句子级切分 ============

/**
 * 将文本切分成句子
 */
function splitIntoSentences(text) {
  // 按标点符号切分，保留代码块完整性
  const sentences = [];
  let current = '';
  let inCodeBlock = false;
  
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    current += char;
    
    // 检测代码块
    if (text.substr(i, 3) === '```') {
      inCodeBlock = !inCodeBlock;
      i += 2;
      current += text.substr(i - 1, 2);
      continue;
    }
    
    // 在代码块内不切分
    if (inCodeBlock) continue;
    
    // 句子结束标志
    const isEnd = ['。', '.', '！', '!', '？', '?', '\n\n'].some(end => {
      return text.substr(i, end.length) === end;
    });
    
    if (isEnd && current.trim().length > 10) {
      sentences.push(current.trim());
      current = '';
    }
  }
  
  if (current.trim()) sentences.push(current.trim());
  return sentences;
}

/**
 * 将句子合并成认知节点
 */
function mergeSentencesIntoNodes(sentences) {
  if (sentences.length === 0) return [];
  
  const nodes = [];
  let currentNode = { content: sentences[0], sentences: [sentences[0]] };
  
  for (let i = 1; i < sentences.length; i++) {
    const sentence = sentences[i];
    const prevContent = currentNode.content;
    
    // 判断是否应该切分
    if (isCognitiveEvent(sentence, prevContent)) {
      // 保存当前节点
      if (currentNode.content.trim()) {
        nodes.push(currentNode);
      }
      // 开始新节点
      currentNode = { content: sentence, sentences: [sentence] };
    } else {
      // 合并到当前节点
      currentNode.content += '\n' + sentence;
      currentNode.sentences.push(sentence);
    }
  }
  
  // 保存最后一个节点
  if (currentNode.content.trim()) {
    nodes.push(currentNode);
  }
  
  return nodes;
}

// ============ 对话级切分 ============

/**
 * 解析对话文件，同时从文件头部提取原始创建时间
 * 支持 GPT 格式（**创建时间**: ...）和 Claude 格式（**Created**: ...）
 */
function parseConversation(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const turns = [];
  let currentTurn = null;
  let inCodeBlock = false;

  // 从文件头部提取原始对话时间（只看前 15 行）
  let conversationTime = null;
  for (let i = 0; i < Math.min(15, lines.length); i++) {
    const m = lines[i].match(/\*\*(?:创建时间|Created|Updated)\*\*[：:]\s*(.+)/);
    if (m) {
      const parsed = new Date(m[1].trim());
      if (!isNaN(parsed.getTime())) {
        conversationTime = parsed.toISOString();
        break;
      }
    }
  }

  for (const line of lines) {
    if (line.startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      if (currentTurn) currentTurn.content += line + '\n';
      continue;
    }

    if (!inCodeBlock && line.match(/^##\s*(User|用户|USER|Human)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'user', content: '' };
    } else if (!inCodeBlock && line.match(/^##\s*(Assistant|ASSISTANT|Claude|AI)/i)) {
      if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
      currentTurn = { role: 'assistant', content: '' };
    } else if (currentTurn) {
      currentTurn.content += line + '\n';
    }
  }

  if (currentTurn && currentTurn.content.trim()) turns.push(currentTurn);
  return { turns, conversationTime };
}

/**
 * 将对话切分成认知节点，节点时间戳使用对话原始时间
 */
function chunkConversationIntoCognitiveNodes(turns, conversationTime) {
  const allNodes = [];
  const nodeTime = conversationTime || new Date().toISOString();

  for (const turn of turns) {
    const text = turn.content.trim();
    if (!text) continue;

    const sentences = splitIntoSentences(text);
    const nodes = mergeSentencesIntoNodes(sentences);

    nodes.forEach(node => {
      node.role = turn.role;
      node.timestamp = nodeTime;  // 使用对话原始时间，而不是处理时间
    });

    allNodes.push(...nodes);
  }

  return allNodes;
}

// ============ 认知图谱构建 ============

/**
 * 构建节点之间的关系
 *
 * relation 字段：五个内置枚举（follows/derives/refines/contrasts/responds）
 * tags 字段：开放数组，供后期"关系类型发现"写入自定义标签，不影响当前训练逻辑
 *   例如：["hypothesis", "analogy", "example"] 等涌现出的模式
 *   写入方式：直接编辑 graphs/*.json 里的 edge.tags，或用分析脚本批量标注
 */
function buildCognitiveGraph(nodes) {
  const graph = {
    nodes: [],
    edges: []
  };

  // 内置关系枚举（用于训练 instruction 映射）
  const BUILTIN_RELATIONS = new Set([
    'follows',      // 顺序跟随（默认）
    'derives',      // 推理推进
    'refines',      // 观点修正
    'contrasts',    // 视角对比
    'responds',     // 角色应答
    'hypothesizes', // 假设推理
    'restarts',     // 思路重启
    'clarifies',    // 澄清说明
    'speculates'    // 推测猜想
  ]);

  nodes.forEach((node, i) => {
    graph.nodes.push({
      id: `node_${i}`,
      content: node.content,
      role: node.role,
      timestamp: node.timestamp,
      length: node.content.length
    });

    if (i > 0) {
      const prevNode = nodes[i - 1];

      let relationType = 'follows';

      // 优先级从高到低判断（更具体的关系优先）
      if (detectReasoningStep(node.content)) {
        relationType = 'derives';
      } else if (detectCorrection(node.content)) {
        relationType = 'refines';
      } else if (detectClarification(node.content)) {
        relationType = 'clarifies';
      } else if (detectRestart(node.content)) {
        relationType = 'restarts';
      } else if (detectHypothesis(node.content)) {
        relationType = 'hypothesizes';
      } else if (detectSpeculation(node.content)) {
        relationType = 'speculates';
      } else if (detectPerspectiveShift(node.content)) {
        relationType = 'contrasts';
      } else if (node.role !== prevNode.role) {
        relationType = 'responds';
      }

      graph.edges.push({
        from: `node_${i - 1}`,
        to: `node_${i}`,
        relation: relationType,       // 内置枚举，训练用
        tags: [],                     // 开放扩展槽，后期关系发现写这里
        // 示例：tags: ["hypothesis", "analogy"] 由分析脚本或人工标注写入
      });
    }
  });

  // ── 生成 iteration_final 边 ──────────────────────────────
  // 检测修正链并添加从起点到终点的直接边
  const refinedBy = {};
  for (const edge of graph.edges) {
    if (edge.relation === 'refines' || edge.relation === 'contrasts') {
      refinedBy[edge.from] = edge.to;
    }
  }

  // 追踪完整修正链
  function getRefinementChain(nodeId) {
    const chain = [nodeId];
    const visited = new Set([nodeId]);
    let cur = nodeId;
    while (refinedBy[cur] && !visited.has(refinedBy[cur])) {
      cur = refinedBy[cur];
      visited.add(cur);
      chain.push(cur);
    }
    return chain.length > 1 ? chain : null;
  }

  // 为每条修正链添加 iteration_final 边
  const allTargets = new Set(Object.values(refinedBy));
  for (const nodeId of Object.keys(refinedBy)) {
    if (!allTargets.has(nodeId)) {  // 只处理链的起点
      const chain = getRefinementChain(nodeId);
      if (chain && chain.length > 1) {
        const startId = chain[0];
        const endId = chain[chain.length - 1];
        graph.edges.push({
          from: startId,
          to: endId,
          relation: 'iteration_final',
          tags: ['refinement_chain'],
          chain_length: chain.length,
          chain_nodes: chain
        });
      }
    }
  }

  return graph;
}

// ============ 训练样本生成 ============

/**
 * 从认知图谱生成训练样本
 *
 * 关键：不是 input → output，而是 state_t → state_t+1
 * 改造一：增加迭代追踪
 *   - 标记被后续 refines/contrasts 修正过的节点（is_refined）
 *   - 额外生成"迭代完整样本"：原始节点 → 最终修正版本
 */
function generateTrainingSamples(graph, windowSize = 3) {
  const samples = [];

  // ── 预处理：找出哪些节点被后续修正了 ──────────────────────
  // refined_by[node_id] = 直接修正它的下一个节点 id
  const refinedBy = {};
  for (const edge of graph.edges) {
    if (edge.relation === 'refines' || edge.relation === 'contrasts') {
      refinedBy[edge.from] = edge.to;
    }
  }

  // 追踪完整修正链，返回 { chain: [id1, id2, ...], depth }
  // chain 包含起点到终点的所有节点 id
  function getRefinementChain(nodeId) {
    const chain = [nodeId];
    const visited = new Set([nodeId]);
    let cur = nodeId;
    while (refinedBy[cur] && !visited.has(refinedBy[cur])) {
      cur = refinedBy[cur];
      visited.add(cur);
      chain.push(cur);
    }
    return chain.length > 1 ? chain : null;  // null 表示没有被修正
  }

  // 预计算每个节点的修正链（只计算链的起点）
  const allTargets = new Set(Object.values(refinedBy));
  const chainCache = {};       // 链起点 → 完整链
  const nodeInChain = new Set(); // 所有在修正链里的节点（含中间节点）
  for (const nodeId of Object.keys(refinedBy)) {
    if (!allTargets.has(nodeId)) {  // 只处理链的起点
      const chain = getRefinementChain(nodeId);
      if (chain) {
        chainCache[nodeId] = chain;
        chain.forEach(id => nodeInChain.add(id));
      }
    }
  }

  // ── 主循环：滑动窗口样本 ──────────────────────────────────
  for (let i = 0; i < graph.nodes.length - 1; i++) {
    const contextStart = Math.max(0, i - windowSize + 1);
    const contextNodes = graph.nodes.slice(contextStart, i + 1);
    const nextNode = graph.nodes[i + 1];

    const stateT = contextNodes.map(n => ({ role: n.role, content: n.content }));
    const stateTplus1 = { role: nextNode.role, content: nextNode.content };

    const edge = graph.edges.find(e => e.to === nextNode.id);
    const relation = edge ? edge.relation : 'follows';

    // 检查当前节点是否在某条修正链里
    const chain = chainCache[graph.nodes[i].id];
    const isRefined = nodeInChain.has(graph.nodes[i].id);
    const iterationDepth = chain ? chain.length - 1 : 0;

    samples.push({
      state_t: stateT,
      state_t_plus_1: stateTplus1,
      relation,
      is_refined: isRefined,
      iteration_depth: iterationDepth,
      final_node_id: chain ? chain[chain.length - 1] : null,
      timestamp: graph.nodes[i].timestamp || new Date().toISOString(),
      source: 'cognitive_chunking'
    });
  }

  // ── 额外生成"迭代完整样本" ────────────────────────────────
  const nodeMap = Object.fromEntries(graph.nodes.map(n => [n.id, n]));

  for (const [rootId, chain] of Object.entries(chainCache)) {
    const finalId = chain[chain.length - 1];
    const rootIdx = graph.nodes.findIndex(n => n.id === rootId);
    if (rootIdx < 0) continue;

    const contextStart = Math.max(0, rootIdx - windowSize + 1);
    const contextNodes = graph.nodes.slice(contextStart, rootIdx + 1);

    // 中间修正过程（chain 里除首尾的节点）
    const midNodes = chain.slice(1, -1).map(id => nodeMap[id]).filter(Boolean);

    const finalNode = nodeMap[finalId];
    if (!finalNode) continue;

    const contextPart = contextNodes.map(n => `[${n.role}] ${n.content}`).join('\n\n');
    const midPart = midNodes.length > 0
      ? '\n\n[中间讨论]\n' + midNodes.map(n => `[${n.role}] ${n.content}`).join('\n\n')
      : '';

    samples.push({
      state_t: contextNodes.map(n => ({ role: n.role, content: n.content })),
      state_t_plus_1: { role: finalNode.role, content: finalNode.content },
      relation: 'iteration_final',
      is_refined: false,
      iteration_depth: chain.length - 1,  // 修正链深度
      final_node_id: finalId,
      root_node_id: rootId,
      _iteration_input_override: contextPart + midPart,
      timestamp: contextNodes[0]?.timestamp || new Date().toISOString(),
      source: 'cognitive_chunking'
    });
  }

  return samples;
}

/**
 * 转换为 Ollama 训练格式
 */
function convertToOllamaFormat(sample) {
  const context = sample._iteration_input_override
    || sample.state_t.map(s => `[${s.role}] ${s.content}`).join('\n\n');

  const target = sample.state_t_plus_1.content;

  const relationInstruction = {
    'follows':        '根据上文，自然延续这个思路：',
    'derives':        '根据上文的前提，推导出下一步结论：',
    'refines':        '对上文的观点进行修正或完善：',
    'contrasts':      '从不同角度重新审视上文的判断：',
    'responds':       '针对上文的问题或想法，给出回应：',
    'iteration_final':'综合上文的讨论过程，给出最终修正后的判断：',
    'hypothesizes':   '基于上文，提出假设性推理：',
    'restarts':       '重新审视上文，从新的角度出发：',
    'clarifies':      '对上文的表述进行更精确的说明：',
    'speculates':     '基于上文，给出推测性判断：',
  }[sample.relation] || '根据上文，继续推进：';

  return {
    instruction: relationInstruction,
    input: context,
    output: target,
    reasoning: `认知推进 (${sample.relation})`,
    is_refined: sample.is_refined || false,
    iteration_depth: sample.iteration_depth || 0,
    timestamp: sample.timestamp || new Date().toISOString(),
    source: sample.source
  };
}

// ============ 主处理流程 ============

function appendJsonl(filePath, data) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(filePath, JSON.stringify(data) + '\n', 'utf-8');
}

async function processCognitiveChunking(conversationsDir, outputDir, dryRun = false) {
  const files = fs.readdirSync(conversationsDir)
    .filter(f => f.endsWith('.md') && !f.startsWith('.'));
  
  console.log(`发现 ${files.length} 个对话文件`);
  if (dryRun) console.log('*** DRY RUN 模式 ***\n');
  
  let totalNodes = 0;
  let totalSamples = 0;
  const relationStats = {};
  
  for (const file of files) {
    const filePath = path.join(conversationsDir, file);

    // 已生成过 graph 就跳过，保证幂等（重复跑不会产生重复样本）
    const graphPath = path.join(outputDir, 'graphs', `${path.basename(file, '.md')}.json`);
    if (!dryRun && fs.existsSync(graphPath)) {
      console.log(`跳过 (已处理): ${file}`);
      continue;
    }

    console.log(`\n处理: ${file}`);
    
    try {
      // 1. 解析对话（同时提取原始时间）
      const { turns, conversationTime } = parseConversation(filePath);
      console.log(`  对话轮次: ${turns.length}${conversationTime ? '  时间: ' + conversationTime.slice(0, 10) : ''}`);

      // 2. 切分成认知节点（节点时间戳使用对话原始时间）
      const nodes = chunkConversationIntoCognitiveNodes(turns, conversationTime);
      console.log(`  认知节点: ${nodes.length}`);
      totalNodes += nodes.length;
      
      // 3. 构建认知图谱
      const graph = buildCognitiveGraph(nodes);
      
      // 4. 生成训练样本
      const samples = generateTrainingSamples(graph, 3);
      console.log(`  训练样本: ${samples.length}`);
      totalSamples += samples.length;
      
      // 统计关系类型
      samples.forEach(s => {
        relationStats[s.relation] = (relationStats[s.relation] || 0) + 1;
      });
      
      if (!dryRun) {
        // 保存认知图谱
        const graphPath = path.join(outputDir, 'graphs', `${path.basename(file, '.md')}.json`);
        const graphDir = path.dirname(graphPath);
        if (!fs.existsSync(graphDir)) fs.mkdirSync(graphDir, { recursive: true });
        fs.writeFileSync(graphPath, JSON.stringify(graph, null, 2), 'utf-8');
        
        // 保存训练样本
        const samplesPath = path.join(outputDir, 'cognitive_samples.jsonl');
        samples.forEach(sample => {
          const ollamaFormat = convertToOllamaFormat(sample);
          appendJsonl(samplesPath, ollamaFormat);
        });
      }
      
    } catch (e) {
      console.error(`  错误: ${e.message}`);
    }
  }
  
  // 汇报
  console.log('\n' + '='.repeat(80));
  console.log('认知切分完成');
  console.log('='.repeat(80));
  console.log(`处理文件: ${files.length}`);
  console.log(`认知节点: ${totalNodes}`);
  console.log(`训练样本: ${totalSamples}`);
  console.log(`\n关系类型分布:`);
  Object.entries(relationStats)
    .sort((a, b) => b[1] - a[1])
    .forEach(([rel, count]) => {
      const pct = ((count / totalSamples) * 100).toFixed(1);
      console.log(`  ${rel}: ${count} (${pct}%)`);
    });
  
  if (!dryRun) {
    console.log(`\n输出目录: ${outputDir}`);
    console.log(`  - 认知图谱: ${outputDir}/graphs/*.json`);
    console.log(`  - 训练样本: ${outputDir}/cognitive_samples.jsonl`);
  }
}

// ============ 主程序 ============

const conversationsDir = process.argv[2] || '/ai-agent/memory/conversations';
const outputDir = process.argv[3] || '/ai-agent/training/cognitive';
const dryRun = process.argv.includes('--dry-run');

console.log('认知切分器 (Cognitive Chunking)');
console.log('='.repeat(80));
console.log('哲学：记录思考推进，而不是对话结构');
console.log('目标：Personal Cognitive Model');
console.log('='.repeat(80));
console.log(`输入: ${conversationsDir}`);
console.log(`输出: ${outputDir}`);
console.log(`模式: ${dryRun ? 'DRY RUN' : '正式处理'}`);
console.log('');

processCognitiveChunking(conversationsDir, outputDir, dryRun).catch(console.error);
