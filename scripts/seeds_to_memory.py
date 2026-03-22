#!/usr/bin/env python3
"""
将 seeds 目录下的对话记录转换为 memory/*.md 格式
让 OpenClaw 自动索引到 Qdrant

用法:
    python3 /ai-agent/scripts/seeds_to_memory.py

输出:
    /ai-agent/memory/conversations/*.md
"""
import json
import os
from pathlib import Path
from datetime import datetime

def extract_conversations_from_claude_export(data):
    """从 Claude 导出的 conversations.json 中提取对话"""
    conversations_list = []
    
    if isinstance(data, list):
        # 直接是对话列表
        for conv in data:
            if isinstance(conv, dict) and 'uuid' in conv:
                conversations_list.append(conv)
    elif isinstance(data, dict):
        # 可能是包装在对象中
        if 'conversations' in data:
            conversations_list = data['conversations']
        elif 'messages' in data:
            # 单个对话
            conversations_list = [data]
    
    return conversations_list

def convert_conversation_to_markdown(conv, index):
    """将单个对话转换为 Markdown 格式"""
    md_lines = []
    
    # 标题
    title = conv.get('name', f'Conversation {index}')
    md_lines.append(f"# {title}")
    md_lines.append("")
    
    # 元数据
    md_lines.append(f"**UUID**: `{conv.get('uuid', 'unknown')}`")
    md_lines.append(f"**Created**: {conv.get('created_at', 'unknown')}")
    md_lines.append(f"**Updated**: {conv.get('updated_at', 'unknown')}")
    md_lines.append(f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 提取对话内容
    chat_messages = conv.get('chat_messages', [])
    
    if not chat_messages:
        md_lines.append("*（无对话内容）*")
    else:
        for msg in chat_messages:
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            
            # 跳过空消息
            if not text or not text.strip():
                continue
            
            # 格式化发送者
            if sender == 'human':
                md_lines.append("## USER")
            elif sender == 'assistant':
                md_lines.append("## ASSISTANT")
            else:
                md_lines.append(f"## {sender.upper()}")
            
            md_lines.append("")
            md_lines.append(text.strip())
            md_lines.append("")
    
    return '\n'.join(md_lines)

def main():
    seeds_dir = Path('/ai-agent/seeds')
    memory_dir = Path('/ai-agent/memory/conversations')
    
    # 检查 seeds 目录是否存在
    if not seeds_dir.exists():
        print(f"Seeds directory not found: {seeds_dir}")
        print(f"Please create directory and add conversation files")
        return
    
    # 创建输出目录
    memory_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {memory_dir}")
    
    # 查找 conversations.json
    conv_file = seeds_dir / 'conversations.json'
    
    if not conv_file.exists():
        print(f"conversations.json not found: {conv_file}")
        return
    
    print(f"Processing: {conv_file.name}")
    
    # 读取并解析 JSON
    try:
        with open(conv_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return
    except Exception as e:
        print(f"File read error: {e}")
        return
    
    # 提取对话列表
    conversations = extract_conversations_from_claude_export(data)
    
    if not conversations:
        print("No conversations found")
        return
    
    print(f"Found {len(conversations)} conversations")
    
    # 转换每个对话
    processed = 0
    skipped = 0
    
    for idx, conv in enumerate(conversations, 1):
        try:
            # 生成文件名
            conv_uuid = conv.get('uuid', f'conv_{idx}')
            conv_name = conv.get('name', f'Conversation {idx}')
            
            # 清理文件名（移除非法字符）
            safe_name = "".join(c for c in conv_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_name:
                safe_name = f"conversation_{idx}"
            
            output_file = memory_dir / f"{safe_name}_{conv_uuid[:8]}.md"
            
            # 转换为 Markdown
            md_content = convert_conversation_to_markdown(conv, idx)
            
            # 保存文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"   [{idx}/{len(conversations)}] {output_file.name}")
            processed += 1
            
        except Exception as e:
            print(f"   [{idx}/{len(conversations)}] Failed: {e}")
            skipped += 1
    
    # 输出统计
    print("")
    print("=" * 60)
    print(f"Processing complete")
    print(f"   - Success: {processed} conversations")
    print(f"   - Skipped: {skipped} conversations")
    print(f"   - Output: {memory_dir}")
    print("")
    print("Next steps:")
    print("   1. Wait for OpenClaw auto-indexing (1-2 minutes)")
    print("   2. Test with memory_search tool")
    print("   3. Example: memory_search: query='conversation'")
    print("=" * 60)

if __name__ == '__main__':
    main()
