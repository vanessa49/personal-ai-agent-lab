#!/usr/bin/env python3
"""
微调一键启动脚本（在笔记本/GPU 机器上运行）

功能：
1. 从 NAS 复制训练数据
2. 检查 LLaMA-Factory 环境
3. 启动 QLoRA 微调（支持自动分批）
4. 完成后把模型推回 NAS，自动清理旧版本只保留 N 个

用法：
  # 单批（默认 1000 条）
  python run_finetune.py --nas-ip 192.168.0.200 --nas-user vanessa --version v1

  # 自动分批跑完全部数据（每批 1000 条，每批结束后自动清理，只保留最近 2 个版本）
  python run_finetune.py --nas-ip 192.168.0.200 --nas-user vanessa --version v1 --auto-batch

  # 自定义批大小和保留版本数
  python run_finetune.py --version v1 --auto-batch --batch-size 2000 --keep-versions 3
"""
import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ── 路径配置 ──────────────────────────────────────────────────
LOCAL_TRAIN_DIR  = Path('C:/ai-training')
LLAMAFACTORY_DIR = Path('C:/ai-training/LLaMA-Factory')
NAS_BASE         = '/share/CACHEDEV1_DATA/docker/ai-agent'
OUTPUT_BASE      = LOCAL_TRAIN_DIR / 'output'

# llamafactory-cli 所在的虚拟环境（3.12 + CUDA）
_VENV_SCRIPTS = Path('C:/ai-training/env/Scripts')


def run(cmd, cwd=None, check=True):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"命令失败，退出码: {result.returncode}")
        sys.exit(1)
    return result.returncode


def check_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"✓ GPU: {name}  ({vram:.1f} GB VRAM)")
            if vram < 6:
                print("⚠️  显存不足 6GB，QLoRA 可能 OOM，建议降低 lora_rank 或 batch_size")
            return True
        else:
            print("✗ 未检测到 CUDA GPU")
            return False
    except ImportError:
        print("⚠️  未安装 torch，跳过 GPU 检查")
        return True


def setup_llamafactory():
    if LLAMAFACTORY_DIR.exists():
        print(f"✓ LLaMA-Factory 已存在: {LLAMAFACTORY_DIR}")
        return
    print("安装 LLaMA-Factory...")
    LOCAL_TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    run(f'git clone https://github.com/hiyouga/LLaMA-Factory.git "{LLAMAFACTORY_DIR}"')
    run(f'pip install -e ".[torch,metrics]"', cwd=LLAMAFACTORY_DIR)
    print("✓ LLaMA-Factory 安装完成")


def copy_data_from_nas(nas_ip, nas_user, version):
    local_data_dir = LOCAL_TRAIN_DIR / 'finetune'
    local_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n从 NAS 复制训练数据...")
    nas_path = f"{nas_user}@{nas_ip}:{NAS_BASE}/training/finetune/*"
    run(f'scp -r "{nas_path}" "{local_data_dir}/"')

    src_info = local_data_dir / 'dataset_info.json'
    dst_info = LLAMAFACTORY_DIR / 'data' / 'dataset_info.json'
    if src_info.exists() and dst_info.exists():
        existing = json.loads(dst_info.read_text(encoding='utf-8'))
        new_info  = json.loads(src_info.read_text(encoding='utf-8'))
        existing.update(new_info)
        dst_info.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"✓ dataset_info.json 已合并")
    elif src_info.exists():
        shutil.copy(src_info, dst_info)
        print(f"✓ dataset_info.json 已复制")

    src_data = local_data_dir / 'dataset.json'
    dst_data = LLAMAFACTORY_DIR / 'data' / 'dataset.json'
    if src_data.exists():
        shutil.copy(src_data, dst_data)
        print(f"✓ dataset.json 已复制 ({src_data.stat().st_size // 1024} KB)")

    # 复制训练配置
    src_yaml = local_data_dir / 'lora_train.yaml'
    if not src_yaml.exists():
        src_yaml = Path(__file__).parent.parent / 'config' / 'lora_train.yaml'

    return local_data_dir, src_yaml


def get_dataset_dir(src_yaml):
    """从 yaml 读取 dataset_dir，决定切片文件写到哪里"""
    import re
    content = src_yaml.read_text(encoding='utf-8')
    m = re.search(r'^dataset_dir:\s*(.+)', content, re.MULTILINE)
    if m:
        return Path(m.group(1).strip())
    return LLAMAFACTORY_DIR / 'data'


def write_batch_dataset(all_data, skip, batch_size, version, dataset_dir):
    """把当前批次的数据切片写成独立 json，注册到对应目录的 dataset_info.json"""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    slice_data = all_data[skip: skip + batch_size]
    slice_name = f'personal_cognitive_{version}'
    slice_path = dataset_dir / f'dataset_{version}.json'

    slice_path.write_text(
        json.dumps(slice_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # 更新同目录下的 dataset_info.json
    info_path = dataset_dir / 'dataset_info.json'
    info = json.loads(info_path.read_text(encoding='utf-8')) if info_path.exists() else {}
    info[slice_name] = {
        "file_name": f"dataset_{version}.json",
        "formatting": "alpaca",
        "columns": {
            "prompt":   "instruction",
            "query":    "input",
            "response": "output",
            "system":   "system",
            "weight":   "weight"
        }
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"✓ 数据切片: [{skip:,} ~ {skip + len(slice_data):,}]  共 {len(slice_data)} 条 → {slice_path}")
    return slice_name, slice_path


def build_yaml(src_yaml, version, dataset_name, resume_from=None):
    """生成本批次的 yaml"""
    import re
    dst_yaml = LOCAL_TRAIN_DIR / f'lora_train_{version}.yaml'
    content = src_yaml.read_text(encoding='utf-8')
    output_dir = OUTPUT_BASE / f'lora_{version}'

    # 替换 output_dir
    content = re.sub(r'output_dir:.*', f'output_dir: {output_dir.as_posix()}', content)

    # 替换 dataset 名称
    content = re.sub(r'^dataset:.*', f'dataset: {dataset_name}', content, flags=re.MULTILINE)

    # 移除 max_samples 和 skip_samples（用切片代替，避免版本兼容问题）
    content = re.sub(r'^max_samples:.*\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^skip_samples:.*\n?', '', content, flags=re.MULTILINE)

    # 增量训练：从上一批 adapter 继续
    if resume_from:
        adapter_path = resume_from.as_posix()
        if re.search(r'^adapter_name_or_path:', content, re.MULTILINE):
            content = re.sub(r'^adapter_name_or_path:.*', f'adapter_name_or_path: {adapter_path}', content, flags=re.MULTILINE)
        else:
            content += f'adapter_name_or_path: {adapter_path}\n'

    dst_yaml.write_text(content, encoding='utf-8')
    return dst_yaml, output_dir


def run_one_batch(yaml_path, output_dir):
    """跑单批训练，返回是否成功"""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n输出目录: {output_dir}\n")

    # 用 sys.executable 确保使用当前激活环境的 Python，不依赖 PATH
    train_cmd = f'"{sys.executable}" -m llamafactory.cli train "{yaml_path}"'
    ret = run(train_cmd, cwd=LLAMAFACTORY_DIR, check=False)
    return ret == 0


def cleanup_old_versions(keep=2):
    """只保留最近 keep 个 lora_* 版本，其余删除"""
    if not OUTPUT_BASE.exists():
        return
    versions = sorted(
        [d for d in OUTPUT_BASE.iterdir() if d.is_dir() and d.name.startswith('lora_')],
        key=lambda d: d.stat().st_mtime
    )
    to_delete = versions[:-keep] if len(versions) > keep else []
    for old in to_delete:
        print(f"🗑  删除旧版本: {old.name}")
        shutil.rmtree(old)
    if to_delete:
        print(f"✓ 已清理 {len(to_delete)} 个旧版本，保留最近 {keep} 个")


def push_model_to_nas(output_dir, nas_ip, nas_user, version):
    nas_model_dir = f"{nas_user}@{nas_ip}:{NAS_BASE}/training/models/lora_{version}"
    print(f"\n推送模型到 NAS: {nas_model_dir}")
    run(f'scp -r "{output_dir}/" "{nas_model_dir}/"')
    link_cmd = (
        f'ssh {nas_user}@{nas_ip} '
        f'"ln -sfn {NAS_BASE}/training/models/lora_{version} '
        f'{NAS_BASE}/training/models/current"'
    )
    run(link_cmd, check=False)
    print(f"✓ 软链接 current → lora_{version}")


def reset_routing_stats(nas_ip, nas_user, version):
    backup_cmd = (
        f'ssh {nas_user}@{nas_ip} '
        f'"cp {NAS_BASE}/routing_stats.json '
        f'{NAS_BASE}/routing_stats_before_lora_{version}.json '
        f'&& echo {{}} > {NAS_BASE}/routing_stats.json"'
    )
    run(backup_cmd, check=False)
    print(f"✓ routing_stats.json 已重置（备份为 routing_stats_before_lora_{version}.json）")


def find_dataset(local_data_dir=None):
    """按优先级查找 dataset.json，返回 (path, data)"""
    candidates = [
        *([ local_data_dir / 'dataset.json' ] if local_data_dir else []),
        LOCAL_TRAIN_DIR / 'finetune' / 'dataset.json',
        LLAMAFACTORY_DIR / 'data' / 'dataset.json',
    ]
    for p in candidates:
        if p.exists():
            print(f"✓ 使用数据集: {p}  ({p.stat().st_size // 1024 // 1024} MB)")
            return p, json.loads(p.read_text(encoding='utf-8'))
    print("✗ 找不到 dataset.json，搜索路径：")
    for p in candidates:
        print(f"  {p}")
    return None, None


def main():
    parser = argparse.ArgumentParser(description='QLoRA 微调一键脚本')
    parser.add_argument('--nas-ip',        default='192.168.0.200')
    parser.add_argument('--nas-user',      default='vanessa')
    parser.add_argument('--version',       default='v1',   help='起始版本号，如 v1')
    parser.add_argument('--skip-copy',     action='store_true', help='跳过从 NAS 复制数据')
    parser.add_argument('--skip-push',     action='store_true', help='跳过推送模型到 NAS')
    parser.add_argument('--data-only',     action='store_true', help='只准备数据，不训练')
    parser.add_argument('--auto-batch',    action='store_true', help='自动分批跑完全部数据')
    parser.add_argument('--batch-size',    type=int, default=1000, help='每批样本数（默认 1000）')
    parser.add_argument('--keep-versions', type=int, default=2,    help='本地保留最近几个版本（默认 2）')
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"QLoRA 微调流程  版本: lora_{args.version}")
    print(f"{'='*60}\n")

    check_gpu()
    setup_llamafactory()

    if not args.skip_copy:
        local_data_dir, src_yaml = copy_data_from_nas(args.nas_ip, args.nas_user, args.version)
    else:
        print("跳过数据复制")
        local_data_dir = None
        src_yaml = Path(__file__).parent.parent / 'config' / 'lora_train.yaml'

    if args.data_only:
        print("\n--data-only 模式，退出")
        return

    if not args.auto_batch:
        # ── 单批模式 ──────────────────────────────────────────
        _, all_data = find_dataset(local_data_dir)
        if all_data is None:
            print("✗ 找不到 dataset.json，请先运行数据准备或去掉 --skip-copy")
            sys.exit(1)
        dataset_name, _ = write_batch_dataset(all_data, 0, args.batch_size, args.version, get_dataset_dir(src_yaml))
        yaml_path, output_dir = build_yaml(src_yaml, args.version, dataset_name)
        start = datetime.now()
        ok = run_one_batch(yaml_path, output_dir)
        elapsed = (datetime.now() - start).seconds // 60
        yaml_path.unlink(missing_ok=True)
        if not ok:
            print(f"\n✗ 训练失败，请检查日志")
            sys.exit(1)
        print(f"\n✓ 训练完成，耗时 {elapsed} 分钟")
        cleanup_old_versions(args.keep_versions)
        final_output = output_dir
    else:
        # ── 自动分批模式 ──────────────────────────────────────
        _, all_data = find_dataset(local_data_dir)
        if all_data is None:
            print("✗ 找不到 dataset.json，请先运行数据准备或去掉 --skip-copy")
            sys.exit(1)

        total = len(all_data)
        num_batches = (total + args.batch_size - 1) // args.batch_size
        print(f"\n数据总量: {total:,} 条")
        print(f"批大小:   {args.batch_size} 条/批")
        print(f"总批数:   {num_batches} 批\n")

        # 解析起始版本号，支持 v1 / v2 / v10 格式
        base_ver = args.version.lstrip('v')
        try:
            ver_num = int(base_ver)
        except ValueError:
            ver_num = 1

        # 一次性加载全部数据到内存，按批切片（避免 skip_samples 兼容问题）
        # 每条记录是独立的认知节点样本（instruction/input/output），按 index 切分安全
        dataset_dir = get_dataset_dir(src_yaml)
        resume_from = None
        final_output = None

        for i in range(num_batches):
            batch_ver = f"v{ver_num + i}"
            skip = i * args.batch_size
            print(f"\n{'─'*60}")
            print(f"批次 {i+1}/{num_batches}  版本: lora_{batch_ver}  skip={skip:,}  size={args.batch_size}")
            print(f"{'─'*60}")

            dataset_name, slice_path = write_batch_dataset(all_data, skip, args.batch_size, batch_ver, dataset_dir)
            yaml_path, output_dir = build_yaml(src_yaml, batch_ver, dataset_name, resume_from)

            start = datetime.now()
            ok = run_one_batch(yaml_path, output_dir)
            elapsed = (datetime.now() - start).seconds // 60

            # 清理本批临时文件
            yaml_path.unlink(missing_ok=True)
            slice_path.unlink(missing_ok=True)

            if not ok:
                print(f"\n✗ 批次 {i+1} 训练失败，已停止")
                print(f"  可从此批重新开始：--version {batch_ver} --skip-copy")
                sys.exit(1)

            print(f"✓ 批次 {i+1} 完成，耗时 {elapsed} 分钟")
            resume_from = output_dir
            final_output = output_dir
            cleanup_old_versions(args.keep_versions)

        print(f"\n{'='*60}")
        print(f"✓ 全部 {num_batches} 批训练完成！最终模型: {final_output}")

    # 推送最终版本到 NAS
    if final_output is None:
        print("⚠️  没有产出模型，跳过推送")
        return
    final_version = final_output.name.replace('lora_', '')
    if not args.skip_push and final_output:
        push_model_to_nas(final_output, args.nas_ip, args.nas_user, final_version)
        reset_routing_stats(args.nas_ip, args.nas_user, final_version)
    else:
        print(f"\n模型保存在本地: {final_output}")
        print(f"手动推送：scp -r \"{final_output}/\" {args.nas_user}@{args.nas_ip}:{NAS_BASE}/training/models/lora_{final_version}/")

    print(f"""
{'='*60}
微调完成！最终版本: lora_{final_version}

回滚方式（本地保留最近 {args.keep_versions} 个版本）：
  llamafactory-cli train <上一版本的 yaml>

下一轮增量训练：
  python run_finetune.py --version v{int(final_version.lstrip('v'))+1}
{'='*60}
""")


if __name__ == '__main__':
    main()
