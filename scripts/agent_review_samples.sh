#!/bin/bash

PENDING_FILE="/ai-agent/training/dataset/pending_review.jsonl"
AGENT_REVIEWED_FILE="/ai-agent/training/dataset/agent_reviewed.jsonl"
REVIEW_LOG="/ai-agent/logs/agent_review.log"
OLLAMA_URL="http://192.168.0.198:11434/api/generate"
MODEL_NAME="qwen3.5:9b-q4_K_M"

echo "测试 Ollama 连接..."
test_resp=$(curl -s -m 10 "$OLLAMA_URL" -H 'Content-Type: application/json' -d "{\"model\":\"$MODEL_NAME\",\"prompt\":\"你好\",\"stream\":false}")
test_text=$(echo "$test_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response',''))" 2>/dev/null)
if [ -n "$test_text" ]; then
    echo "✓ 连接成功: ${test_text:0:30}..."
else
    echo "✗ 连接失败或响应为空"
    exit 1
fi

total=$(wc -l < "$PENDING_FILE")
echo -e "\n开始 Agent 审核，共 $total 条样本\n"

processed=0
approved=0
rejected=0
failed=0

while IFS= read -r line; do
    ((processed++))
    
    # 用 Python 提取字段
    instruction=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['instruction'][:180].replace('\n',' '))" 2>/dev/null)
    output=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['output'][:180].replace('\n',' '))" 2>/dev/null)
    score=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin)['score'])" 2>/dev/null)
    
    # 转义双引号
    instruction=$(echo "$instruction" | sed 's/"/\\"/g')
    output=$(echo "$output" | sed 's/"/\\"/g')
    
    prompt="评估对话样本质量。标准：有明确问题和解决方案、有技术价值、回答质量高、非闲聊。样本：指令: $instruction 输出: $output 评分: $score 直接回答：[通过/拒绝] 理由（10字内）"
    
    response=$(curl -s -m 40 "$OLLAMA_URL" -H 'Content-Type: application/json' -d "{\"model\":\"$MODEL_NAME\",\"prompt\":\"$prompt\",\"stream\":false,\"options\":{\"temperature\":0.3,\"num_predict\":200}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response',''))" 2>/dev/null)
    
    if [ -z "$response" ]; then
        ((failed++))
        echo "[$processed/$total] ✗ 失败"
        continue
    fi
    
    if echo "$response" | grep -q "通过"; then
        decision="approved"
        ((approved++))
        symbol="✓"
    else
        decision="rejected"
        ((rejected++))
        symbol="✗"
    fi
    
    reason=$(echo "$response" | head -c 50 | tr '\n' ' ')
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 用 Python 生成 JSON
    echo "$line" | python3 -c "
import sys, json
sample = json.load(sys.stdin)
sample['agent_decision'] = '$decision'
sample['agent_reason'] = '''$reason'''
sample['agent_review_time'] = '$timestamp'
print(json.dumps(sample, ensure_ascii=False))
" >> "$AGENT_REVIEWED_FILE"
    
    echo "[$processed/$total] $symbol | ${reason:0:25}"
    
    if [ $((processed % 10)) -eq 0 ]; then
        echo "[$timestamp] 已处理 $processed/$total, 通过 $approved, 拒绝 $rejected, 失败 $failed" >> "$REVIEW_LOG"
        echo "  进度: $(awk "BEGIN {printf \"%.1f\", $processed/$total*100}")%"
    fi
    
    sleep 3
done < "$PENDING_FILE"

echo -e "\n=== Agent 审核完成 ==="
echo "总计: $processed, 通过: $approved, 拒绝: $rejected, 失败: $failed"
if [ $processed -gt 0 ]; then
    echo "成功率: $(awk "BEGIN {printf \"%.1f\", ($processed-$failed)/$processed*100}")%"
fi
echo "结果: $AGENT_REVIEWED_FILE"
