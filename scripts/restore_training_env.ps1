# 一键恢复训练环境
# 用法：在任意 PowerShell 里运行：.\scripts\restore_training_env.ps1

$ENV_DIR = "C:\ai-training\env"
$LLAMA_DIR = "C:\ai-training\LLaMA-Factory"
$WHEEL_DIR = "Z:\ai-wheelhouse\cu121-py312"

Write-Host "=============================="
Write-Host "恢复训练环境"
Write-Host "=============================="

# 激活环境
& "$ENV_DIR\Scripts\Activate.ps1"

# 检查 torch
$torchOk = & "$ENV_DIR\Scripts\python.exe" -c "import torch; print(torch.cuda.is_available())" 2>&1
if ($torchOk -eq "True") {
    Write-Host "✓ torch + CUDA 已就绪"
} else {
    Write-Host "安装 torch CUDA..."
    # 优先用本地 whl（不需要联网）
    if (Test-Path "$WHEEL_DIR\torch-2.5.1+cu121-cp312-cp312-win_amd64.whl") {
        & "$ENV_DIR\Scripts\pip.exe" install "$WHEEL_DIR\torch-2.5.1+cu121-cp312-cp312-win_amd64.whl" "$WHEEL_DIR\torchvision-0.20.1+cu121-cp312-cp312-win_amd64.whl" "$WHEEL_DIR\torchaudio-2.5.1+cu121-cp312-cp312-win_amd64.whl"
    } else {
        Write-Host "本地 whl 不存在，从网络下载..."
        & "$ENV_DIR\Scripts\pip.exe" install torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
        # 下完保存到 NAS
        if (Test-Path $WHEEL_DIR) {
            & "$ENV_DIR\Scripts\pip.exe" download torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121 -d $WHEEL_DIR
            Write-Host "✓ whl 已保存到 $WHEEL_DIR"
        }
    }
}

# 检查 llamafactory
$lfOk = & "$ENV_DIR\Scripts\python.exe" -c "import llamafactory" 2>&1
if ($lfOk -match "Error") {
    Write-Host "安装 LLaMA-Factory..."
    & "$ENV_DIR\Scripts\pip.exe" install -e $LLAMA_DIR --no-deps --ignore-requires-python
}

# 最终验证
Write-Host ""
Write-Host "验证环境..."
& "$ENV_DIR\Scripts\python.exe" -c "import torch; print('torch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"
& "$ENV_DIR\Scripts\python.exe" -m llamafactory.cli version

Write-Host ""
Write-Host "✓ 环境就绪，可以开始训练"
Write-Host "  激活命令：C:\ai-training\env\Scripts\Activate.ps1"
