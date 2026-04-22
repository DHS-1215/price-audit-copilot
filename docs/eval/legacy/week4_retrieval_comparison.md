# 第四周检索模式对比记录

## 一、对比目的

第四周统一 ask 入口已经支持两种规则检索模式：

- baseline：基于第三周规则型、可解释的检索器
- faiss：基于第三周向量检索器的语义检索

本次对比的目标不是做严格评测，而是记录：

1. 两种检索模式是否都已经接入统一 ask 入口
2. 同一个问题下，两种模式的返回风格有什么差异
3. 当前阶段更适合默认使用哪一种模式

---

## 二、对比问题

### 对比样例 1
**问题：**
如果标题不完整，规则上该怎么处理？

---

## 三、baseline 模式结果

### 输入
```json
{
  "question": "如果标题不完整，规则上该怎么处理？",
  "use_vector": false
}

结果摘要
route = retrieval
retrieval_result.mode = baseline
topic = 规格归一与规格风险规则
最相关证据命中 FAQ 中“如果标题不完整，规则上该怎么处理？”章节
同时命中 spec_normalization_rules 相关规则文档
当前观察

baseline 模式下，这类规则型问题的主题判断更贴近业务规则方向，能较稳定地把问题归到“规格归一与规格风险规则”这一类。

## 四、FAISS 模式结果

输入
{
  "question": "如果标题不完整，规则上该怎么处理？",
  "use_vector": true
}
结果摘要
route = retrieval
retrieval_result.mode = faiss
topic = FAQ
最相关证据命中 FAQ 中“如果标题不完整，规则上该怎么处理？”章节
同时返回 spec_normalization_rules 相关规则片段
当前观察

FAISS 模式下，这类自然语言问句更容易把 FAQ 放在第一位，说明语义检索能够较自然地命中问答式规则说明。

五、当前对比结论
1. 接入状态

baseline 和 faiss 两种检索模式都已成功接入第四周统一 ask 入口。

2. 当前表现差异
baseline 更偏“规则型、可控型、业务路由明确”的检索风格
faiss 更偏“自然语言、FAQ 问法、语义相似”的检索风格
3. 当前建议

第四周当前阶段建议：

默认模式使用 baseline
将 faiss 作为增强模式保留
后续如果继续优化，可再考虑 hybrid（混合检索）
六、当前阶段为什么不直接默认混合检索

因为第四周当前重点是：

先把统一 ask 入口做稳
让 analysis / retrieval / explanation / mixed 主链清楚
让日志、验收、输出结构都先站住

在这个阶段，先保留 baseline / faiss 可切换，比直接上混合检索更利于调试、验收和说明。

七、后续优化方向
为 faiss 模式补充更清晰的 topic 推断逻辑
为 faiss 模式补充更适合展示的 score / score_reasons
后续可尝试 hybrid：
baseline 负责规则型、可解释召回
faiss 负责语义召回补充
再做轻量去重与重排