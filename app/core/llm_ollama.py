import json
import os
import requests
from app.core.schemas import ProductExtractResult

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


# 把商品标题丢给本地模型，让模型按照我定义好的ProductExtractResult结构返回json，然后再用Pydantic 校验后变成 Python 对象。（结构化抽取）
# Pydantic 模型 = 给数据立规矩的类。
def extract_product(title: str) -> ProductExtractResult:
    # 把 Pydantic 模型 ProductExtractResult 转成 JSON Schema。
    if hasattr(ProductExtractResult, 'model_json_schema'):
        schema = ProductExtractResult.model_json_schema()
    else:
        schema = ProductExtractResult.schema()

    payload = {
        'model': OLLAMA_MODEL,
        'messages': [
            # 系统提示词，相当于给模型定规矩。
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
                'role': 'user',
                'content': f"请抽取这条商品标题中的字段:{title}"
            }
        ],
        'stream': False,  # 不要流式返回，一次性给我完整结果。（因为工作中需要的是一个完整 JSON，不是边生成边展示。）
        'format': schema,  # 要求模型按照我给的 schema（规则） 输出。
        'options': {
            'temperature': 0  # 参数设0，尽量稳定，少随机发挥。
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()  # 如报错，先确认接口请求本身是成功的。

    data = response.json()  # 此处羊驼返回的是个JSON
    content = data['message']['content']  # 取出我需要的模型输出文本

    # 防止模型啥也没回。方便后续我排查问题！！！
    if not content:
        raise ValueError(f'Ollama returned empty content: {data}')

    # 把字符串 JSON 解析成 Python 字典。
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f'Model did not return valid JSON: {content})') from e

    # 兜底处理 currency
    conf = parsed.get('confidence', 0.0)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.0
    parsed['confidence'] = max(0.0, min(1.0, conf))

    # 兜底处理 currency
    if not parsed.get('currency') or parsed.get('currency') == "?":
        parsed['currency'] = 'CNY'

    # 把解析出来的字典，塞回ProductExtractResult，让pydantic效验。
    return ProductExtractResult(**parsed)
