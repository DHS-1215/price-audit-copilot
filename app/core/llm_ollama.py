import os
import requests

"""
把问题发到：
http://localhost:11434/api/chat
然后把 Ollama 返回的内容拿出来。
"""

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def ask_llm(question: str) -> str:
    payload = {
        'model': OLLAMA_MODEL,
        'messages': [
            {
                'role': 'system',
                'content': 'You are an AI assistant for an e-commerce price audit project. Answer clearly and briefly.'
            },
            {
                'role': 'user',
                'content': question
            }
        ],
        'stream': False,
        'options': {
            'temperature': 0
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    print("OLLAMA RAW RESPONSE:", data)

    content = data["message"]["content"]

    if content is None:
        raise ValueError(f"Ollama returned None content: {data}")

    return content