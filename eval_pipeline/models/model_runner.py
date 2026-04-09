# models/model_runner.py
import requests
import time
import json
from config import (
    OLLAMA_BASE_URL, MAX_NEW_TOKENS,
    TEMPERATURE, MODEL_DELAY_SECONDS
)


class OllamaRunner:
    """
    调用本地Ollama模型。
    支持普通对话和带context的多轮对话（trajectory测试用）。
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.base_url = OLLAMA_BASE_URL
        self._verify_connection()

    def _verify_connection(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if self.model_name not in models:
                print(f"⚠️  警告: {self.model_name} 不在Ollama模型列表中")
                print(f"   可用模型: {models}")
            else:
                print(f"✓ {self.model_name} 已就绪")
        except Exception as e:
            print(f"❌ 无法连接Ollama ({self.base_url}): {e}")
            raise

    def generate(self, prompt: str, context: list = None) -> str:
        """
        生成回答。
        
        Args:
            prompt: 用户输入
            context: 多轮对话历史，格式：[{"role": "user/assistant", "content": "..."}]
        
        Returns:
            模型回答字符串
        """
        messages = []

        # 添加系统提示
        messages.append({
            "role": "system",
            "content": (
                "You are a thoughtful AI assistant. "
                "When facing complex or ambiguous questions, "
                "think through the problem step by step rather than jumping to conclusions. "
                "It's okay to revise your thinking as you go."
            )
        })

        # 添加对话历史（trajectory测试用）
        if context:
            messages.extend(context)

        # 添加当前问题
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "options": {
                        "temperature": TEMPERATURE,
                        "num_predict": MAX_NEW_TOKENS,
                    },
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            time.sleep(MODEL_DELAY_SECONDS)
            return result["message"]["content"].strip()

        except requests.exceptions.Timeout:
            return "[ERROR: 模型推理超时]"
        except Exception as e:
            return f"[ERROR: {str(e)}]"
