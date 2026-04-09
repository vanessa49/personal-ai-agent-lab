# config.py
import os

# ============================================================
# 模型配置 (Ollama)
# ============================================================
OLLAMA_BASE_URL = "http://localhost:11434"   # 如果从NAS调用改成笔记本IP
BASE_MODEL_NAME = "qwen2.5:7b"              # baseline
FT_MODEL_NAME   = "qwen2.5:7b-v5-q4"          # 微调后的模型名（改成你实际的名字）

# ============================================================
# Judge后端配置（二选一，优先用Pollinations省钱）
# ============================================================
JUDGE_BACKEND = "pollinations"   # "pollinations" 或 "deepseek"

# Pollinations配置
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")  # 没有也可以用（免费tier）
POLLINATIONS_BASE_URL = "https://gen.pollinations.ai/v1"
POLLINATIONS_MODEL = "gemini-fast"   # Gemini 2.5 Flash Lite，最便宜且质量不错
# 备选: "mistral"(Mistral 24B), "openai-fast"(GPT-5 Nano), "deepseek"

# DeepSeek配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# ============================================================
# Rate limiting（防止一次用完积分）
# ============================================================
JUDGE_DELAY_SECONDS = 2.0     # 每次judge调用之间的间隔
MODEL_DELAY_SECONDS = 0.5     # 每次模型推理之间的间隔

# ============================================================
# 评估参数
# ============================================================
MAX_NEW_TOKENS = 400          # 模型回答最大长度
JUDGE_MAX_TOKENS = 500        # judge输出最大长度
TEMPERATURE = 0.3             # 模型温度（低一点更稳定）

# ============================================================
# 输出配置
# ============================================================
RESULTS_DIR = "results"
SAVE_RAW_RESPONSES = True     # 是否保存原始回答（强烈建议True）
