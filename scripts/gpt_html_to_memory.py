#!/usr/bin/env python3
"""
GPT chat.html / conversations-NNN.json → memory/*.md

chat.html  → 只取主路径（current_node 链），去重用 conversation_id
JSON 切片  → 主路径 + 所有非主路径分支，每条分支独立保存

增量导入：
  索引 key = conversation_id（主路径）或 conv_id::branch_leaf_id（分支）
  同 key 消息数相同 → 跳过；消息数增多 → 覆盖
  索引文件放在 output_dir 上级，不受文件移动影响
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

IMPORT_INDEX_FILE = 'imported_conversations.json'


# ── 文件读取 ──────────────────────────────────────────────

def extract_json_data(html_path):
    """从 chat.html 提取 var jsonData 数组"""
    print(f"读取: {html_path}  ({Path(html_path).stat().st_size/1024/1024:.1f} MB)")
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    marker = 'var jsonData = '
    start = content.find(marker)
    if start == -1:
        raise ValueError("未找到 var jsonData")
    raw = content[content.index('[', start):]
    del content
    print("解析 JSON...")
    data, _ = json.JSONDecoder().raw_decode(raw)
    del raw
    print(f"共 {len(data)} 个对话")
    return data


def extract_from_json(json_path):
    """直接读取 conversations-NNN.json，过滤非对话格式"""
    print(f"读取: {json_path}  ({Path(json_path).stat().st_size/1024/1024:.1f} MB)")
    data = json.loads(Path(json_path).read_text(encoding='utf-8'))
    if not isinstance(data, list):
        print(f"  跳过: 不是列表格式（{type(data).__name__}）")
        return []
    conversations = [c for c in data if isinstance(c, dict) and 'mapping' in c]
    if not conversations:
        print(f"  跳过: 没有包含 mapping 的对话条目")
        return []
    print(f"共 {len(conversations)} 个对话")
    return conversations


# ── 路径提取 ──────────────────────────────────────────────

def _path_from_leaf(mapping, leaf_id):
    """从叶节点往上追溯父链，返回 [根, ..., 叶] 的节点 ID 列表"""
    path = []
    nid = leaf_id
    visited = set()
    while nid and nid not in visited:
        visited.add(nid)
        path.append(nid)
        nid = mapping.get(nid, {}).get('parent')
    path.reverse()
    return path


def _messages_from_path(mapping, path_ids):
    """从节点 ID 列表提取 user/assistant 消息"""
    messages = []
    for nid in path_ids:
        msg = mapping.get(nid, {}).get('message')
        if not msg:
            continue
        role = msg.get('author', {}).get('role', '')
        if role not in ('user', 'assistant'):
            continue
        parts = msg.get('content', {}).get('parts', [])
        text = '\n'.join(p for p in parts if isinstance(p, str)).strip()
        if text:
            messages.append({'role': role, 'content': text,
                             'create_time': msg.get('create_time') or 0})
    return messages


def extract_main_path(conv):
    """提取主路径消息（current_node 链）"""
    mapping = conv.get('mapping', {})
    current = conv.get('current_node')
    if current and current in mapping:
        return _messages_from_path(mapping, _path_from_leaf(mapping, current))
    # fallback：按时间排序
    msgs = []
    for node in mapping.values():
        msg = node.get('message')
        if not msg:
            continue
        role = msg.get('author', {}).get('role', '')
        if role not in ('user', 'assistant'):
            continue
        parts = msg.get('content', {}).get('parts', [])
        text = '\n'.join(p for p in parts if isinstance(p, str)).strip()
        if text:
            msgs.append({'role': role, 'content': text,
                         'create_time': msg.get('create_time') or 0})
    msgs.sort(key=lambda m: m['create_time'])
    return msgs


def extract_all_branches(conv):
    """
    提取所有非主路径的分支，每条分支返回 (leaf_id, messages)。

    策略：找所有叶节点（无 children），排除 current_node，
    每个叶节点代表一条独立的探索路径。
    """
    mapping = conv.get('mapping', {})
    current = conv.get('current_node')

    # 所有叶节点
    leaves = [nid for nid, node in mapping.items()
              if not node.get('children') and nid != current]

    branches = []
    for leaf_id in leaves:
        path = _path_from_leaf(mapping, leaf_id)
        msgs = _messages_from_path(mapping, path)
        if msgs:
            branches.append((leaf_id, msgs))
    return branches


# ── Markdown 生成 ─────────────────────────────────────────

def to_markdown(conv, messages, branch_label=None):
    title = conv.get('title') or 'Untitled'
    conv_id = conv.get('conversation_id') or conv.get('id', '')
    create_time = conv.get('create_time', '')
    try:
        create_time_str = datetime.fromtimestamp(float(create_time)).strftime('%Y-%m-%d %H:%M')
    except Exception:
        create_time_str = str(create_time) or 'unknown'

    display_title = f"{title}（分支）" if branch_label else title

    lines = [
        f"# {display_title}", "",
        f"**来源**: GPT Export",
        f"**conversation_id**: `{conv_id}`",
    ]
    if branch_label:
        lines.append(f"**branch_leaf**: `{branch_label}`")
    lines += [
        f"**创建时间**: {create_time_str}",
        f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**消息数**: {len(messages)}",
        "", "---", "",
    ]
    for msg in messages:
        lines.append("## USER" if msg['role'] == 'user' else "## ASSISTANT")
        lines += ["", msg['content'], ""]
    return '\n'.join(lines)


# ── 索引 ──────────────────────────────────────────────────

def load_index(output_dir):
    index_path = output_dir.parent / IMPORT_INDEX_FILE
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding='utf-8')), index_path
        except Exception:
            pass
    return {}, index_path


def save_index(index, index_path):
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')


# ── 写文件（带去重） ──────────────────────────────────────

def write_conversation(output_dir, index, conv, messages, index_key,
                       filename_base, branch_label=None):
    """
    写一条对话（主路径或分支）到 Markdown，更新索引。
    返回 'new' / 'updated' / 'skipped'
    """
    new_count = len(messages)
    if index_key in index:
        if new_count <= index[index_key]['msg_count']:
            return 'skipped'
        # 消息增多，覆盖旧文件
        old_file = output_dir / index[index_key].get('filename', '')
        if old_file.exists():
            old_file.unlink()
        action = 'updated'
    else:
        action = 'new'

    safe = re.sub(r'[^\w\u4e00-\u9fa5 \-]', '_', filename_base).strip()[:60] or 'conversation'
    filename = f"{safe}.md"
    out_file = output_dir / filename

    md = to_markdown(conv, messages, branch_label)
    out_file.write_text(md, encoding='utf-8')

    index[index_key] = {
        'msg_count': new_count,
        'title': conv.get('title', ''),
        'filename': filename,
        'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return action


# ── 主流程 ────────────────────────────────────────────────

def process_conversations(conversations, output_dir, index, extract_branches=False):
    stats = {'new': 0, 'updated': 0, 'skipped': 0, 'empty': 0, 'branches': 0}
    total = len(conversations)

    for idx, conv in enumerate(conversations, 1):
        conv_id = conv.get('conversation_id') or conv.get('id', '')
        title = conv.get('title') or f'conversation_{idx}'
        safe_title = re.sub(r'[^\w\u4e00-\u9fa5 \-]', '_', title).strip()[:50] or f'conv_{idx}'
        id8 = conv_id[:8] if conv_id else str(idx)

        try:
            # 主路径
            messages = extract_main_path(conv)
            if not messages:
                stats['empty'] += 1
            else:
                result = write_conversation(
                    output_dir, index, conv, messages,
                    index_key=conv_id,
                    filename_base=f"{safe_title}_{id8}",
                )
                stats[result] += 1

            # 分支（仅 JSON 模式）
            if extract_branches:
                for leaf_id, branch_msgs in extract_all_branches(conv):
                    branch_key = f"{conv_id}::{leaf_id}"
                    leaf8 = leaf_id[:8]
                    result = write_conversation(
                        output_dir, index, conv, branch_msgs,
                        index_key=branch_key,
                        filename_base=f"{safe_title}_{id8}_branch_{leaf8}",
                        branch_label=leaf_id,
                    )
                    if result in ('new', 'updated'):
                        stats['branches'] += 1

        except Exception as e:
            stats['empty'] += 1
            print(f"\n  [{idx}] 失败: {e}")

        if idx % 50 == 0 or idx == total:
            print(f"  [{idx}/{total}] 新:{stats['new']} 更新:{stats['updated']} "
                  f"跳过:{stats['skipped']} 分支:{stats['branches']}", end='\r')

    return stats


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '/ai-agent/seeds/gpt'
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/ai-agent/memory/conversations')

    if not Path(src).exists() and str(output_dir) == '/ai-agent/memory/conversations':
        # 本地测试 fallback
        output_dir = Path(src).parent.parent / 'gpt_conversations'

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {output_dir}")

    index, index_path = load_index(output_dir)
    print(f"已有索引: {len(index)} 条（{index_path}）")
    print()

    # 支持传单个文件或整个目录
    src_path = Path(src)
    if src_path.is_file():
        files = [src_path]
    elif src_path.is_dir():
        # 遍历目录下所有 .html 和 .json 文件，按文件名排序
        files = sorted(
            [f for f in src_path.iterdir()
             if f.suffix in ('.html', '.json') and f.is_file()]
        )
        if not files:
            print(f"未找到 .html 或 .json 文件: {src_path}")
            return
        print(f"发现 {len(files)} 个文件:")
        for f in files:
            print(f"  {f.name}  ({f.stat().st_size/1024/1024:.1f} MB)")
        print()
    else:
        print(f"路径不存在: {src}")
        return

    total_stats = {'new': 0, 'updated': 0, 'skipped': 0, 'empty': 0, 'branches': 0}

    for file in files:
        print(f"{'='*60}")
        is_json = file.suffix == '.json'
        conversations = extract_from_json(file) if is_json else extract_json_data(file)

        mode = "主路径 + 分支" if is_json else "主路径"
        print(f"处理模式: {mode}，共 {len(conversations)} 个对话\n")

        stats = process_conversations(conversations, output_dir, index, extract_branches=is_json)
        for k in total_stats:
            total_stats[k] += stats.get(k, 0)

        print(f"\n  本文件: 新增{stats['new']} 更新{stats['updated']} 跳过{stats['skipped']} 分支{stats['branches']}")

    save_index(index, index_path)

    print(f"\n{'='*60}")
    print(f"全部完成")
    print(f"新增主路径: {total_stats['new']}")
    print(f"更新主路径: {total_stats['updated']}")
    print(f"跳过(重复): {total_stats['skipped']}")
    print(f"新增分支:   {total_stats['branches']}")
    print(f"空/错:      {total_stats['empty']}")
    print(f"索引:       {index_path}（共 {len(index)} 条）")
    print(f"输出:       {output_dir}")
    print(f"\n下一步:")
    print(f"  node /ai-agent/scripts/cognitive_chunking.js /ai-agent/memory/conversations /ai-agent/training/cognitive")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
