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
    seeds_dir = Path('/ai-agent/seeds/claude')
    memory_dir = Path('/ai-agent/memory/conversations')

    if not seeds_dir.exists():
        print(f"Seeds directory not found: {seeds_dir}")
        print(f"Please create: mkdir -p /ai-agent/seeds/claude")
        return

    memory_dir.mkdir(parents=True, exist_ok=True)

    # 遍历目录下所有 .json 文件
    json_files = sorted(seeds_dir.glob('*.json'))
    if not json_files:
        print(f"No .json files found in {seeds_dir}")
        return

    print(f"Found {len(json_files)} file(s) in {seeds_dir}")
    print(f"Output directory: {memory_dir}")
    print()

    # 用 uuid 去重，同一个对话多次导出只保留最新（消息数最多）
    seen_uuids = {}  # uuid -> output_file（已写入的文件路径）

    total_processed = 0
    total_skipped = 0
    total_updated = 0

    for json_file in json_files:
        print(f"Processing: {json_file.name}")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  Failed to read: {e}")
            continue

        conversations = extract_conversations_from_claude_export(data)
        if not conversations:
            print(f"  No conversations found")
            continue

        print(f"  Found {len(conversations)} conversations")

        for idx, conv in enumerate(conversations, 1):
            try:
                conv_uuid = conv.get('uuid', f'conv_{idx}')
                conv_name = conv.get('name', f'Conversation {idx}')
                msg_count = len(conv.get('chat_messages', []))

                safe_name = "".join(
                    c for c in conv_name if c.isalnum() or c in (' ', '-', '_')
                ).strip() or f"conversation_{idx}"

                output_file = memory_dir / f"{safe_name}_{conv_uuid[:8]}.md"

                # 去重：同 uuid 已存在且消息数没增加则跳过
                if conv_uuid in seen_uuids:
                    prev_count = seen_uuids[conv_uuid]['msg_count']
                    if msg_count <= prev_count:
                        total_skipped += 1
                        continue
                    # 消息数增加，删旧文件
                    old_file = seen_uuids[conv_uuid]['path']
                    if old_file.exists():
                        old_file.unlink()
                    total_updated += 1
                else:
                    total_processed += 1

                md_content = convert_conversation_to_markdown(conv, idx)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)

                seen_uuids[conv_uuid] = {'path': output_file, 'msg_count': msg_count}

            except Exception as e:
                print(f"  [{idx}] Failed: {e}")
                total_skipped += 1

        print(f"  Done")

    print()
    print("=" * 60)
    print(f"Processing complete")
    print(f"   - New:     {total_processed} conversations")
    print(f"   - Updated: {total_updated} conversations (more messages)")
    print(f"   - Skipped: {total_skipped} conversations (duplicate)")
    print(f"   - Output:  {memory_dir}")
    print()
    print("Next steps:")
    print("   1. Wait for OpenClaw auto-indexing (1-2 minutes)")
    print("   2. Test with memory_search tool")
    print("=" * 60)

if __name__ == '__main__':
    main()
