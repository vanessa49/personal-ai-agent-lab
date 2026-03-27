#!/bin/bash
# NAS 环境验证脚本（针对 /ai-agent/ 目录结构）
# 
# 使用方式：
#   docker exec -it openclaw bash
#   cd /ai-agent/personal-ai-agent-lab-main
#   bash run_nas_validation.sh

set -e

echo "=========================================="
echo "Personal AI DevTo 验证流程 (NAS 版本)"
echo "=========================================="
echo ""

# 检测运行环境
if [ -f /.dockerenv ]; then
    echo "✓ 检测到 Docker 环境"
    BASE_DIR="/ai-agent"
else
    echo "⚠ 非 Docker 环境，使用相对路径"
    BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

echo "基础目录: $BASE_DIR"
echo ""

# 定义路径
SEEDS_DIR="$BASE_DIR/seeds/gpt"
CONVERSATIONS_DIR="$BASE_DIR/memory/conversations"
COGNITIVE_DIR="$BASE_DIR/training/cognitive"
GRAPHS_DIR="$COGNITIVE_DIR/graphs"
SAMPLES_FILE="$COGNITIVE_DIR/cognitive_samples.jsonl"
PROJECT_DIR="$BASE_DIR/personal-ai-agent-lab-main"

# 创建必要目录
mkdir -p "$CONVERSATIONS_DIR"
mkdir -p "$GRAPHS_DIR"
mkdir -p "$BASE_DIR/logs"

echo "📁 目录配置:"
echo "   Seeds: $SEEDS_DIR"
echo "   对话: $CONVERSATIONS_DIR"
echo "   输出: $COGNITIVE_DIR"
echo ""

# ============ 步骤 0: 检查数据 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 0: 检查数据状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查 seeds
if [ ! -d "$SEEDS_DIR" ]; then
    echo "❌ Seeds 目录不存在: $SEEDS_DIR"
    echo "   请先将 GPT 导出数据放到该目录"
    exit 1
fi

SEEDS_COUNT=$(find "$SEEDS_DIR" -name "*.json" -type f 2>/dev/null | wc -l)
echo "Seeds 文件数: $SEEDS_COUNT"

# 检查对话
CONV_COUNT=$(find "$CONVERSATIONS_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
echo "已转换对话: $CONV_COUNT"

# 检查图谱
GRAPH_COUNT=$(find "$GRAPHS_DIR" -name "*.json" -type f 2>/dev/null | wc -l)
echo "已生成图谱: $GRAPH_COUNT"

echo ""

# ============ 步骤 1: 数据导入（如果需要）============
if [ $CONV_COUNT -eq 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "步骤 1: 导入 GPT 对话数据"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [ $SEEDS_COUNT -eq 0 ]; then
        echo "❌ 没有找到 GPT 数据文件"
        echo "   请将 conversations-*.json 放到: $SEEDS_DIR"
        exit 1
    fi
    
    echo "转换 GPT JSON 为 Markdown..."
    python3 "$PROJECT_DIR/scripts/quick_gpt_to_md.py" \
        "$SEEDS_DIR" \
        "$CONVERSATIONS_DIR" \
        2>&1 | tee "$BASE_DIR/logs/01_import.log"
    
    CONV_COUNT=$(find "$CONVERSATIONS_DIR" -name "*.md" -type f | wc -l)
    echo ""
    echo "✅ 生成 $CONV_COUNT 个对话文件"
    echo ""
else
    echo "✓ 对话已导入，跳过步骤 1"
    echo ""
fi

# ============ 步骤 2: 切分方法对比 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2: 切分方法对比实验 ⭐ 核心"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 选择第一个对话文件
SAMPLE_CONV=$(find "$CONVERSATIONS_DIR" -name "*.md" -type f | head -1)

if [ -z "$SAMPLE_CONV" ]; then
    echo "❌ 没有找到对话文件"
    exit 1
fi

echo "使用示例对话: $(basename "$SAMPLE_CONV")"
echo ""

node "$PROJECT_DIR/scripts/compare_chunking_methods.js" \
    "$SAMPLE_CONV" \
    2>&1 | tee "$BASE_DIR/logs/02_chunking_comparison.log"

echo ""
echo "✅ 切分对比完成"
echo ""

# ============ 步骤 3: 认知切分处理 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3: 认知切分处理（生成认知图谱）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

node "$PROJECT_DIR/scripts/cognitive_chunking.js" \
    "$CONVERSATIONS_DIR" \
    "$COGNITIVE_DIR" \
    2>&1 | tee "$BASE_DIR/logs/03_cognitive_chunking.log"

echo ""
echo "✅ 认知切分完成"
echo "   - 认知图谱: $GRAPHS_DIR"
echo "   - 训练样本: $SAMPLES_FILE"
echo ""

# ============ 步骤 4: 关系模式发现 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 4: 关系模式发现分析"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -d "$GRAPHS_DIR" ]; then
    node "$PROJECT_DIR/scripts/discover_relation_patterns.js" \
        "$GRAPHS_DIR" \
        --top 20 \
        2>&1 | tee "$BASE_DIR/logs/04_relation_patterns.log"
    
    echo ""
    echo "✅ 关系模式分析完成"
    echo ""
else
    echo "⚠️  跳过：认知图谱目录不存在"
    echo ""
fi

# ============ 步骤 5: 数据统计 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 5: 数据统计汇总"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 统计对话
CONV_COUNT=$(find "$CONVERSATIONS_DIR" -name "*.md" -type f | wc -l)
echo "对话文件数: $CONV_COUNT"

# 统计图谱
GRAPH_COUNT=$(find "$GRAPHS_DIR" -name "*.json" -type f 2>/dev/null | wc -l)
echo "认知图谱数: $GRAPH_COUNT"

# 统计样本
if [ -f "$SAMPLES_FILE" ]; then
    SAMPLE_COUNT=$(wc -l < "$SAMPLES_FILE")
    echo "训练样本数: $SAMPLE_COUNT"
    
    # 统计迭代样本
    ITERATION_COUNT=$(grep -c '"iteration_depth":[1-9]' "$SAMPLES_FILE" 2>/dev/null || echo "0")
    echo "  - 迭代样本: $ITERATION_COUNT"
    
    # 统计修正样本
    REFINED_COUNT=$(grep -c '"is_refined":true' "$SAMPLES_FILE" 2>/dev/null || echo "0")
    echo "  - 修正样本: $REFINED_COUNT"
fi

echo ""

# ============ 生成报告 ============
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "生成验证报告"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

REPORT_FILE="$BASE_DIR/DEVTO_VALIDATION_REPORT.md"

cat > "$REPORT_FILE" << EOF
# Personal AI DevTo 文章验证报告

生成时间: $(date '+%Y-%m-%d %H:%M:%S')
运行环境: NAS Docker 容器

## 数据概览

- 对话文件: $CONV_COUNT 个
- 认知图谱: $GRAPH_COUNT 个
- 训练样本: ${SAMPLE_COUNT:-0} 条
  - 迭代样本: ${ITERATION_COUNT:-0} 条
  - 修正样本: ${REFINED_COUNT:-0} 条

## 数据位置

- 对话: \`$CONVERSATIONS_DIR\`
- 图谱: \`$GRAPHS_DIR\`
- 样本: \`$SAMPLES_FILE\`
- 日志: \`$BASE_DIR/logs/\`

## 验证步骤

### 1. 数据导入 ✅
- 日志: \`logs/01_import.log\`
- 输出: \`memory/conversations/\`

### 2. 切分方法对比 ✅
- 日志: \`logs/02_chunking_comparison.log\`
- 核心发现: 传统切分 vs 认知切分的差异

### 3. 认知切分处理 ✅
- 日志: \`logs/03_cognitive_chunking.log\`
- 输出: \`training/cognitive/\`

### 4. 关系模式发现 ✅
- 日志: \`logs/04_relation_patterns.log\`
- 分析: 认知关系分布和修正链

## DevTo 文章可用数据

查看日志文件获取详细数据：
- \`logs/02_chunking_comparison.log\` - 切分对比案例
- \`logs/04_relation_patterns.log\` - 关系分布统计

## 下一步

- [ ] 从日志提取关键数据
- [ ] 选择典型对话案例
- [ ] 撰写 DevTo 文章
- [ ] （可选）微调实验留给 Paper

---

所有数据已准备就绪，可以开始写文章了！
EOF

echo "✅ 验证报告生成: $REPORT_FILE"
echo ""

# ============ 完成 ============
echo "=========================================="
echo "✅ 所有验证步骤完成！"
echo "=========================================="
echo ""
echo "📊 查看结果:"
echo "   - 验证报告: $REPORT_FILE"
echo "   - 对话文件: $CONVERSATIONS_DIR"
echo "   - 认知图谱: $GRAPHS_DIR"
echo "   - 训练样本: $SAMPLES_FILE"
echo "   - 日志目录: $BASE_DIR/logs/"
echo ""
echo "📝 DevTo 文章素材已准备就绪！"
echo ""
