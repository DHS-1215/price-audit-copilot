from typing import Optional
from pydantic import BaseModel, Field

"""
定义接口收发数据的“格式说明书”
1.请求参数校验.
2.返回结果约束.
3.自动生成接口文档 /docs.
4.让代码更清晰，少写很多手动判断.
"""


# BaseModel是Pydantic 的核心类，能效验字段类型、请求JSON转成Py对象、自动报错、FastAPI直接拿去生成接口文档。
class AskRequest(BaseModel):
    # 调用 /ask 接口时，前端传过来的请求体长什么样。
    question: str = Field(..., description="User question")


class AskResponse(BaseModel):
    #  让接口返回结果固定住，不至于今天返回 text，明天返回 msg，后天我都得看懵。
    answer: str = Field(..., description='LLM Answer')


class ExtractRequest(BaseModel):
    # 调用 /extract 接口时，用户需要传一个商品标题进来。
    title: str = Field(..., description='Product title')


class ProductExtractResult(BaseModel):
    # 从商品标题里抽出来的结构化结果长什么样。
    brand: Optional[str] = Field(default=None, description='Brand')  # 商品品牌。
    product_name: Optional[str] = Field(default=None, description='Product name')  # 商品名
    spec: Optional[str] = Field(default=None, description='Specification')  # 规格
    price: Optional[float] = Field(default=None, description='Price in CNY')  # 浮点型价格
    currency: str = Field(default='CNY', description='Currency')  # 货币单位
    promo_text: Optional[str] = Field(default=None, description='Promotion text')  # 促销文案。
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description='Confidence')  # 模型对这次抽取结果的置信度。字段上了个“护栏”，避免乱飞。
