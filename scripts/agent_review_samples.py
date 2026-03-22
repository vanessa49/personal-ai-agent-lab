#!/usr/bin/env python3
import json
import time
import urllib.request
from pathlib import Path

PENDING_FILE = '/ai-agent/training/dataset/pending_review.jsonl'
AGENT_REVIEWED_FILE = '/ai-agent/training/dataset/agent_reviewed.jsonl'
REVIEW_LOG = '/ai-agent/logs/agent_review.log'
OLLAMA_URL = 'http://192.168.0.198:11434/api/generate'
MODEL_NAME = 'qwen3.5:9b-q4_K_M'

def call_ollama(prompt):
    try:
        data = json.dumps({
            'model': MODEL_NAME,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.3,
                'num_predict': 200,
                'stop': ['\n\n']
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=40) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '').strip()
    except Exception as e:
        print(f'  调用失败: {type(e).__name__}: {str(e)[:80]}')
        return None

def main():
    print('测试 Ollama 连接...')
    test = call_ollama('简短回答：你好')
    if not test:
        print('✗ 连接失败或响应为空')
        print('  尝试增加 num_predict 或检查模型配置')
        return
    print(f'✓ 连接成功: {test[:50]}...\n')

    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    
    print(f'开始 Agent 审核，共 {len(lines)} 条样本\n')
    
    processed = approved = rejected = failed = 0
    
    for line in lines:
        sample = json.loads(line)
        
        inst = sample['instruction'][:180].replace('\n', ' ').replace('"', "'")
        outp = sample['output'][:180].replace('\n', ' ').replace('"', "'")
        
        prompt = f"""评估对话样本质量。标准：有明确问题和解决方案、有技术价值、回答质量高、非闲聊。

样本：
指令: {inst}
输出: {outp}
评分: {sample['score']}

直接回答：[通过/拒绝] 理由（10字内）"""

        response = call_ollama(prompt)
        
        if not response:
            failed += 1
            processed += 1
            print(f'[{processed}/{len(lines)}] ✗ 失败')
            continue
        
        is_approved = '通过' in response
        reason = response[:50].replace('\n', ' ')
        
        reviewed = dict(sample)
        reviewed['agent_decision'] = 'approved' if is_approved else 'rejected'
        reviewed['agent_reason'] = reason
        reviewed['agent_review_time'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        with open(AGENT_REVIEWED_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(reviewed, ensure_ascii=False) + '\n')
        
        if is_approved:
            approved += 1
        else:
            rejected += 1
        
        processed += 1
        print(f'[{processed}/{len(lines)}] {"✓" if is_approved else "✗"} | {reason[:25]}')
        
        if processed % 10 == 0:
            log = f'[{time.strftime("%Y-%m-%dT%H:%M:%SZ")}] 已处理 {processed}/{len(lines)}, 通过 {approved}, 拒绝 {rejected}, 失败 {failed}\n'
            Path(REVIEW_LOG).parent.mkdir(parents=True, exist_ok=True)
            with open(REVIEW_LOG, 'a', encoding='utf-8') as f:
                f.write(log)
            print(f'  进度: {processed/len(lines)*100:.1f}%')
        
        time.sleep(3)
    
    print(f'\n=== Agent 审核完成 ===')
    print(f'总计: {processed}, 通过: {approved}, 拒绝: {rejected}, 失败: {failed}')
    if processed > 0:
        print(f'成功率: {(processed-failed)/processed*100:.1f}%')
    print(f'结果: {AGENT_REVIEWED_FILE}')

if __name__ == '__main__':
    main()
