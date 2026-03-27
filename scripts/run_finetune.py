#!/usr/bin/env python3
"""
微调一键启动脚本（在笔记本/GPU 机器上运行）

功能：
1. 从 NAS 复制训练数据
2. 检查 LLaMA-Factory 环境
3. 启动 QLoRA 微调
4. 完成后把模型推回 NAS

用法：
  python run_finetune.py --nas-ip 192.168.0.200 --nas-user vanessa --version v1
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


def run(cmd, cwd=None, check=True):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"命令失败，退出码: {result.returncode}")
        sys.exit(1)
    return result.returncode


def check_gpu():
    """检查 GPU 可用性"""
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
    """安装 LLaMA-Factory（如果还没装）"""
    if LLAMAFACTORY_DIR.exists():
        print(f"✓ LLaMA-Factory 已存在: {LLAMAFACTORY_DIR}")
        return

    print("安装 LLaMA-Factory...")
    LOCAL_TRAIN_DIR.mkdir(parents=True, exist_ok=True)
    run(f'git clone https://github.com/hiyouga/LLaMA-Factory.git "{LLAMAFACTORY_DIR}"')
    run(f'pip install -e ".[torch,metrics]"', cwd=LLAMAFACTORY_DIR)
    print("✓ LLaMA-Factory 安装完成")


def copy_data_from_nas(nas_ip, nas_user, version):
    """从 NAS 复制训练数据到本地"""
    local_data_dir = LOCAL_TRAIN_DIR / 'finetune'
    local_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n从 NAS 复制训练数据...")
    nas_path = f"{nas_user}@{nas_ip}:{NAS_BASE}/training/finetune/"
    run(f'scp -r "{nas_path}" "{local_data_dir}/"')

    # 把 dataset_info.json 合并到 LLaMA-Factory/data/
    src_info = local_data_dir / 'dataset_info.json'
    dst_info = LLAMAFACTORY_DIR / 'data' / 'dataset_info.json'

    if src_info.exists() and dst_info.exists():
        # 合并而不是覆盖
        existing = json.loads(dst_info.read_text(encoding='utf-8'))
        new_info  = json.loads(src_info.read_text(encoding='utf-8'))
        existing.update(new_info)
        dst_info.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"✓ dataset_info.json 已合并")
    elif src_info.exists():
        shutil.copy(src_info, dst_info)
        print(f"✓ dataset_info.json 已复制")

    # 复制 dataset.json 到 LLaMA-Factory/data/
    src_data = local_data_dir / 'dataset.json'
    dst_data = LLAMAFACTORY_DIR / 'data' / 'dataset.json'
    if src_data.exists():
        shutil.copy(src_data, dst_data)
        print(f"✓ dataset.json 已复制 ({src_data.stat().st_size // 1024} KB)")

    # 复制训练配置
    src_yaml = local_data_dir / 'lora_train.yaml'
    if not src_yaml.exists():
        # fallback：从项目 config 目录找
        src_yaml = Path(__file__).parent.parent / 'config' / 'lora_train.yaml'
    if src_yaml.exists():
        dst_yaml = LOCAL_TRAIN_DIR / 'lora_train.yaml'
        shutil.copy(src_yaml, dst_yaml)
        # 精确替换 output_dir 里的版本号，避免误替换其他字段
        content = dst_yaml.read_text(encoding='utf-8')
        content = content.replace('output_dir: C:/ai-training/output/lora_v1',
                                  f'output_dir: C:/ai-training/output/lora_{version}')
        dst_yaml.write_text(content, encoding='utf-8')
        print(f"✓ 训练配置已复制，版本: {version}")

    return local_data_dir


def run_training(version):
    """启动 QLoRA 微调"""
    yaml_path = LOCAL_TRAIN_DIR / 'lora_train.yaml'
    output_dir = LOCAL_TRAIN_DIR / 'output' / f'lora_{version}'
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n开始 QLoRA 微调...")
    print(f"输出目录: {output_dir}")
    print(f"预计时间: 1-3 小时（取决于样本数量和 GPU）\n")

    start = datetime.now()
    # LLaMA-Factory 新版本用 llamafactory-cli，旧版本用 src/train.py，自动兼容
    train_cmd = (
        f'llamafactory-cli train "{yaml_path}"'
        if (LLAMAFACTORY_DIR / 'llamafactory').exists() or
           (LLAMAFACTORY_DIR / 'src' / 'llamafactory').exists()
        else f'python src/train.py --config "{yaml_path}"'
    )
    ret = run(train_cmd, cwd=LLAMAFACTORY_DIR, check=False)
    elapsed = (datetime.now() - start).seconds // 60

    if ret != 0:
        print(f"\n✗ 训练失败，请检查日志")
        print(f"常见问题：")
        print(f"  OOM → 降低 lora_rank 到 8，或 per_device_train_batch_size 到 1")
        print(f"  模型下载失败 → 手动下载到 C:/ai-training/models/")
        sys.exit(1)

    print(f"\n✓ 训练完成，耗时 {elapsed} 分钟")
    return output_dir


def push_model_to_nas(output_dir, nas_ip, nas_user, version):
    """把训练好的模型推回 NAS"""
    nas_model_dir = f"{nas_user}@{nas_ip}:{NAS_BASE}/training/models/lora_{version}"
    print(f"\n推送模型到 NAS: {nas_model_dir}")
    run(f'scp -r "{output_dir}/" "{nas_model_dir}/"')

    # 更新软链接 current → 新版本
    link_cmd = (
        f'ssh {nas_user}@{nas_ip} '
        f'"ln -sfn {NAS_BASE}/training/models/lora_{version} '
        f'{NAS_BASE}/training/models/current"'
    )
    run(link_cmd, check=False)
    print(f"✓ 软链接 current → lora_{version}")


def reset_routing_stats(nas_ip, nas_user, version):
    """微调后重置 routing_stats.json（备份旧的）"""
    backup_cmd = (
        f'ssh {nas_user}@{nas_ip} '
        f'"cp {NAS_BASE}/routing_stats.json '
        f'{NAS_BASE}/routing_stats_before_lora_{version}.json '
        f'&& echo {{}} > {NAS_BASE}/routing_stats.json"'
    )
    run(backup_cmd, check=False)
    print(f"✓ routing_stats.json 已重置（备份为 routing_stats_before_lora_{version}.json）")


def main():
    parser = argparse.ArgumentParser(description='QLoRA 微调一键脚本')
    parser.add_argument('--nas-ip',   default='192.168.0.200', help='NAS IP 地址')
    parser.add_argument('--nas-user', default='vanessa',       help='NAS 用户名')
    parser.add_argument('--version',  default='v1',            help='模型版本号，如 v1 v2')
    parser.add_argument('--skip-copy',  action='store_true', help='跳过从 NAS 复制数据')
    parser.add_argument('--skip-push',  action='store_true', help='跳过推送模型到 NAS')
    parser.add_argument('--data-only',  action='store_true', help='只准备数据，不训练')
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"QLoRA 微调流程  版本: lora_{args.version}")
    print(f"{'='*60}\n")

    # 1. 检查 GPU
    check_gpu()

    # 2. 安装 LLaMA-Factory
    setup_llamafactory()

    # 3. 从 NAS 复制数据
    if not args.skip_copy:
        copy_data_from_nas(args.nas_ip, args.nas_user, args.version)
    else:
        print("跳过数据复制")

    if args.data_only:
        print("\n--data-only 模式，退出")
        return

    # 4. 训练
    output_dir = run_training(args.version)

    # 5. 推送模型到 NAS
    if not args.skip_push:
        push_model_to_nas(output_dir, args.nas_ip, args.nas_user, args.version)
        reset_routing_stats(args.nas_ip, args.nas_user, args.version)
    else:
        print(f"\n模型保存在本地: {output_dir}")
        print(f"手动推送命令：")
        print(f"  scp -r \"{output_dir}/\" {args.nas_user}@{args.nas_ip}:{NAS_BASE}/training/models/lora_{args.version}/")

    print(f"""
{'='*60}
微调完成！

下一步 AB 测试：
  1. 编辑 openclaw.json，切换模型：
     "model": {{"primary": "ollama/qwen2.5:7b-lora-{args.version}"}}

  2. 用一段时间，感觉更好 → 保留
     感觉变差 → 回滚：
     ssh {args.nas_user}@{args.nas_ip}
     ln -sfn {NAS_BASE}/training/models/lora_v_上一版本 {NAS_BASE}/training/models/current

  3. 下一轮增量训练时，版本号 +1：
     python run_finetune.py --version v2
{'='*60}
""")


if __name__ == '__main__':
    main()
