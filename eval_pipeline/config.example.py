# config.example.py
# -------------------------------------------------------------------
# Public template for the behavioral-evaluation harness.
# Copy to `config.py` and fill in via environment variables.
# DO NOT hard-code API keys in the committed file.
#
#   cp config.example.py config.py        # (config.py is .gitignored)
#   export NVIDIA_API_KEY=...             # only needed for LLM-judge
#   export GEMINI_API_KEY=...             # optional judge backend
#   export POLLINATIONS_API_KEY=...       # optional judge backend
# -------------------------------------------------------------------
import os
import time
import requests

# ===================================================================
# Local model serving (Ollama)
# ===================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "qwen2.5:7b-instruct-q4_K_M")
FT_MODEL_NAME   = os.getenv("FT_MODEL_NAME",   "qwen2.5:7b-trajectory")  # your fine-tuned model

# ===================================================================
# LLM-judge backend (OPTIONAL: only used by judge-based scoring,
# not by the embedding-similarity / controllability metrics).
# All keys come from the environment; defaults are empty on purpose.
# ===================================================================
JUDGE_BACKEND = os.getenv("JUDGE_BACKEND", "pollinations")  # "gemini" | "pollinations" | "deepseek"

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL    = "gemini-2.5-flash"

POLLINATIONS_API_KEY  = os.getenv("POLLINATIONS_API_KEY", "")
POLLINATIONS_BASE_URL = "https://gen.pollinations.ai/v1"
POLLINATIONS_MODEL    = "openai"

DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL    = "deepseek-chat"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

# ===================================================================
# Evaluation parameters
# ===================================================================
MAX_NEW_TOKENS      = 400    # max generation length
JUDGE_MAX_TOKENS    = 500
TEMPERATURE         = 0.0    # deterministic decoding for reproducibility
MODEL_DELAY_SECONDS = 0.0
JUDGE_DELAY_SECONDS = 2.0
RESULTS_DIR         = "results"
SAVE_RAW_RESPONSES  = True


# ===================================================================
# Minimal LLM helper (used only by optional judge-based scoring).
# Returns None if no backend key is configured.
# ===================================================================
def call_llm(prompt: str, system: str = "", timeout: int = 60) -> str:
    """Optional: call a hosted LLM as a judge. No-op if keys are unset."""
    if POLLINATIONS_API_KEY or JUDGE_BACKEND == "pollinations":
        try:
            messages = ([{"role": "system", "content": system}] if system else []) + \
                       [{"role": "user", "content": prompt}]
            r = requests.post(
                f"{POLLINATIONS_BASE_URL}/chat/completions",
                headers={"Content-Type": "application/json",
                         **({"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {})},
                json={"model": POLLINATIONS_MODEL, "messages": messages,
                      "temperature": 0.3, "max_tokens": JUDGE_MAX_TOKENS},
                timeout=timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            time.sleep(1)
    raise RuntimeError("No LLM-judge backend configured (set *_API_KEY env vars).")
