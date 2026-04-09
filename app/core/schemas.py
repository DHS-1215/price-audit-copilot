from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

"""
定义接口收发数据的“格式说明书”
1.请求参数校验.
2.返回结果约束.
3.自动生成接口文档 /docs.
4.让代码更清晰，少写很多手动判断.
"""
"""1. ask 接口相关"""
RouteType = Literal[
    "analysis",
    "retrieval",
    "explanation",
    "mixed",
    "unknown",
]


# 第四周统一问答入口请求体。
# BaseModel是Pydantic 的核心类，能效验字段类型、请求JSON转成Py对象、自动报错、FastAPI直接拿去生成接口文档。
class AskRequest(BaseModel):
    question: str = Field(..., description='用户问题')
    top_k: int = Field(default=3, ge=1, le=10, description='规则检索返回参数')
    use_vector: bool = Field(default=False, description='是否优先使用向量检索')
    include_trace: bool = Field(default=True, description='是否返回工具调用链路')


# 单次工具调用的简要 trace
class ToolTraceItem(BaseModel):
    step: int = Field(..., description='步骤序号')
    tool_name: str = Field(..., description='工具名')
    status: str = Field(..., description='执行状态，如 success / failed')
    note: str = Field(default='', description='简短说明')


# 第四周统一问答入口响应体
class AskResponse(BaseModel):
    """
    先把主结构立住，后面 routes_ask.py 直接往里填
    """
    route: RouteType = Field(..., description='问题路由类型')
    answer: str = Field(..., description="最终回答")
    tools_used: list[str] = Field(default_factory=list, description="实际调用的工具列表")
    analysis_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="数据分析结果"
    )
    retrieval_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="规则检索结果"
    )
    explanation_result: Optional[dict[str, Any]] = Field(
        default=None,
        description="异常解释结果"
    )
    trace: list[ToolTraceItem] = Field(
        default_factory=list,
        description="工具调用链路"
    )


"""2. extract 接口相关"""


class ExtractRequest(BaseModel):
    # 调用 /extract 接口时，用户需要传一个商品标题进来。
    title: str = Field(..., description='Product title')


# 从商品标题里抽出来的结构化结果长什么样。
class ProductExtractResult(BaseModel):
    brand: Optional[str] = Field(default=None, description="商品品牌")
    product_name: Optional[str] = Field(default=None, description="商品名")
    spec: Optional[str] = Field(default=None, description="规格")
    price: Optional[float] = Field(default=None, description="价格（人民币）")
    currency: str = Field(default="CNY", description="货币单位")
    promo_text: Optional[str] = Field(default=None, description="促销文案")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="抽取置信度"
    )
