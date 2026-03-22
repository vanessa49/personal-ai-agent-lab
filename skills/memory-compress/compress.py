import requests
import sys

def compress_with_7b(history):
    response = requests.post(
        "http://192.168.0.198:11434/api/generate",
        json={
            "model": "qwen2.5:7b-instruct-q4_K_M",  # 明确指定 7B
            "prompt": f"将以下对话压缩为500字摘要，包含：解决的问题、未完成任务、重要决策\n\n{history}",
            "stream": False
        }
    )
    return response.json()["response"]

if __name__ == "__main__":
    history = sys.stdin.read()
    summary = compress_with_7b(history)
    print(summary)
