import json
import os
import requests
from app.core.schemas import ProductExtractResult

"""
把问题发到：
http://localhost:11434/api/chat
然后把 Ollama 返回的内容拿出来。
"""

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def ask_llm(question: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI assistant for an e-commerce price audit project. Answer clearly and briefly."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0
        }
    }

    response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    print("OLLAMA RAW RESPONSE:", data)

    content = data["message"]["content"]

    if content is None:
        raise ValueError(f"Ollama returned None content: {data}")

    return content


def extract_product(title: str) -> ProductExtractResult:
    if hasattr(ProductExtractResult, "model_json_schema"):
        schema = ProductExtractResult.model_json_schema()
    else:
        schema = ProductExtractResult.schema()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个电商商品标题结构化抽取助手。"
                    "请从输入的商品标题中抽取以下字段："
                    "brand, product_name, spec, price, currency, promo_text, confidence。"
                    "必须只返回符合给定 schema 的 JSON。"
                    "如果字段无法确定，返回 null。"
                    "currency 默认填 CNY。"
                    "confidence 必须是 0 到 1 之间的小数。"
                    "不要输出问号占位符，不要输出额外解释。"
                )
            },
            {
                "role": "user",
                "content": f"请抽取这条商品标题中的字段:{title}"
            }
        ],
        "stream": False,
        "format": schema,
        "options": {
            "temperature": 0
        }
    }

    response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]

    if not content:
        raise ValueError(f"Ollama returned empty content: {data}")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {content}") from e

    conf = parsed.get("confidence", 0.0)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.0
    parsed["confidence"] = max(0.0, min(1.0, conf))

    if not parsed.get("currency") or parsed.get("currency") == "?":
        parsed["currency"] = "CNY"

    return ProductExtractResult(**parsed)