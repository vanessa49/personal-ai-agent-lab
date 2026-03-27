#!/usr/bin/env python3
"""
快速 GPT JSON 转 Markdown
直接处理当前目录的 gpt/*.json 文件
"""
import json
import sys
from pathlib import Path
from datetime import datetime

def parse_gpt_json(json_path):
    """解析 GPT conversation JSON"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 处理数组格式（conversations-007.json 等）
    if isinstance(data, list):
        conversations = []
        for item in data:
            conv = parse_single_conversation(item)
            if conv:
                conversations.append(conv)
        return conversations
    else:
        # 单个对话
        conv = parse_single_conversation(data)
        return [conv] if conv else []

def parse_single_conversation(data):
    """解析单个对话对象"""
    conversation = {
        'title': data.get('title', 'Untitled'),
        'created_at': None,
        'messages': []
    }
    
    # 提取创建时间
    if 'create_time' in data:
        try:
            conversation['created_at'] = datetime.fromtimestamp(data['create_time']).isoformat()
        except:
            pass
    
    # 解析 mapping 结构
    if 'mapping' in data:
        nodes = []
        for node_id, node_data in data['mapping'].items():
            if node_data.get('message'):
                msg = node_data['message']
                if msg.get('content') and msg['content'].get('parts'):
                    content_parts = msg['content']['parts']
                    # 过滤空内容
                    content = '\n'.join(str(p) for p in content_parts if p)
                    
                    if content.strip():
                        nodes.append({
                            'create_time': msg.get('create_time', 0),
                            'role': msg['author']['role'],
                            'content': content
                        })
        
        # 按时间排序（处理 None 值）
        nodes.sort(key=lambda x: x['create_time'] if x['create_time'] else 0)
        
        # 只保留 user 和 assistant
        for node in nodes:
            if node['role'] in ['user', 'assistant']:
                conversation['messages'].append({
                    'role': node['role'],
                    'content': node['content']
                })
    
    return conversation if conversation['messages'] else None

def convert_to_markdown(conversation, index):
    """转换为 Markdown"""
    md_lines = []
    
    title = conversation.get('title', f'Conversation {index}')
    md_lines.append(f"# {title}")
    md_lines.append("")
    
    # 元数据
    md_lines.append(f"**来源**: GPT Export")
    if conversation.get('created_at'):
        md_lines.append(f"**创建时间**: {conversation['created_at']}")
    md_lines.append(f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"**消息数**: {len(conversation['messages'])}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 消息
    for msg in conversation['messages']:
        role = "USER" if msg['role'] == 'user' else "ASSISTANT"
        md_lines.append(f"## {role}")
        md_lines.append("")
        md_lines.append(msg['content'].strip())
        md_lines.append("")
    
    return '\n'.join(md_lines)

def main():
    if len(sys.argv) < 3:
        print("用法: python quick_gpt_to_md.py <gpt目录> <输出目录>")
        print("示例: python quick_gpt_to_md.py ../gpt ./output/conversations")
        sys.exit(1)
    
    gpt_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    if not gpt_dir.exists():
        print(f"❌ GPT 目录不存在: {gpt_dir}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("GPT JSON 转 Markdown")
    print("=" * 60)
    print(f"输入: {gpt_dir}")
    print(f"输出: {output_dir}")
    print("")
    
    # 查找所有 JSON 文件
    json_files = list(gpt_dir.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith('.')]
    
    print(f"发现 {len(json_files)} 个 JSON 文件")
    print("")
    
    all_conversations = []
    
    for json_file in json_files:
        print(f"处理: {json_file.name}")
        try:
            convs = parse_gpt_json(json_file)
            all_conversations.extend(convs)
            print(f"  ✓ 提取 {len(convs)} 个对话")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    print("")
    print(f"总计: {len(all_conversations)} 个对话")
    print("")
    
    if not all_conversations:
        print("❌ 没有提取到对话")
        return
    
    # 转换并保存
    print("转换为 Markdown...")
    print("")
    
    processed = 0
    for idx, conv in enumerate(all_conversations, 1):
        try:
            title = conv.get('title', f'conversation_{idx}')
            # 清理文件名
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50] if safe_title else f"conversation_{idx}"
            
            output_file = output_dir / f"{safe_title}_{idx}.md"
            
            md_content = convert_to_markdown(conv, idx)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            print(f"  [{idx}/{len(all_conversations)}] {output_file.name}")
            processed += 1
            
        except Exception as e:
            print(f"  [{idx}/{len(all_conversations)}] 失败: {e}")
    
    print("")
    print("=" * 60)
    print(f"✅ 完成: {processed} 个对话")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

if __name__ == '__main__':
    main()
