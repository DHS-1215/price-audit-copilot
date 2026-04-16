# 第六周正式评测结果

## 记录规则

每条记录保留 5 项：

1. 问题
2. 预期答案 / 核心要点
3. 实际输出
4. 是否通过
5. 错误原因（若失败）

---

## 评测结果汇总

- 总用例数：30
- 已完成评测：30
- 通过：9
- 部分通过：11
- 不通过：10

### 主要通过类型
- analysis 主链中的基础统计类问题整体较稳定
- retrieval 主链能够命中核心规则文档
- mixed 主链已可完成“数据分析 + 规则检索 + 汇报生成”的基本闭环

### 主要失败/偏差类型
- 一部分本应走 analysis 的问题被路由到 unknown 或退回 ask_llm
- 一部分本应走 retrieval 的问题被误打到 analysis 总览
- mixed 链路虽然能跑通，但对“品牌 / 规格 / 平台 / both 条件”这类定向筛选问题，结果收束还不够稳定
- 某些 retrieval 命中正确，但 answer 解释深度不够，只说明命中了哪个章节，没有把规则口径讲透

### 当前最主要的 3 个问题
1. 路由器对 analysis / retrieval 的边界识别还不够稳
2. 条件筛选类问题容易退化成 overview 总览
3. 检索命中后，answer 层有时解释不够充分

### 第六周评测结论

本轮评测说明，系统已经具备基础可用性：
- 容器化部署可运行
- analysis / retrieval / mixed 三类链路均已跑通
- 对典型业务问题能够返回结构化分析结果、规则依据和简短汇报

同时，评测也暴露出当前版本的主要短板：
- 对宽泛分析问题和条件筛选问题的路由稳定性不足
- 对规则解释类问题，部分回答仍停留在“指出文档章节”层面，解释深度不够
- mixed 问题在多条件约束下，分析结果有时会退化为 overview，而不是精准命中目标子集

下一步优化重点：
- 加强 route_query 对 analysis / retrieval 的判别规则
- 补强 analysis_tools 对品牌、规格、平台、规则来源等条件过滤的支持
- 优化 retrieval 后的回答组织，让 answer 不止“命中文档”，还要真正解释规则口径

---

## A01

- 问题：近7天哪个平台异常低价最多？
- 预期要点：
    - route = analysis
    - 返回低价最多的平台
    - analysis_result.ok = true
- 实际输出：
    - "route": "analysis"
- 是否通过：
    - 通过
- 错误原因：
    - 无

## A02

- 问题：当前低价样本有哪些？
- 预期要点：
    - route = analysis
    - 返回疑似异常低价样本列表
    - analysis_result.row_count > 0
- 实际输出：
    - route = unknown
    - tools_used = ["ask_llm"]
    - analysis_result = null
    - answer 未直接返回低价样本列表，而是要求补充更具体的商品类别或品牌信息
- 是否通过：
    - 不通过
- 错误原因：
    - 问题表述较泛，但在当前业务系统语境下，系统应默认基于当前数据集返回疑似异常低价样本，而不是退回通用模型追问；实际路由到
      unknown，说明 analysis 路由覆盖不足。

## A03

- 问题：哪个品牌跨平台价差最大？
- 预期要点：
    - route = analysis
    - 返回跨平台价差最大的品牌
    - analysis_result.ok = true
- 实际输出：
    - "route": "analysis"
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - answer 当前跨平台价差最大的品牌是 鸿茅，规格为 500ml，价差金额 576.00。
- 是否通过：
    - 通过
- 错误原因：
    - 无

## A04

- 问题：哪些商品规格识别有风险？
- 预期要点：
    - route = analysis
    - 返回规格识别风险样本
    - analysis_result.row_count >= 0
- 实际输出：
    - route = unknown
    - tools_used = ["ask_llm"]
    - analysis_result = null
    - answer 返回了一段通用性的规格识别风险说明，包括信息不完整、格式不统一、单位转换问题、描述模糊和新规格出现等内容
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于 analysis 类，系统应基于当前数据集直接返回规格识别风险样本；实际未命中
      analysis，退回通用模型回答，未返回任何风险样本或结构化分析结果

## A05

- 问题：鸿茅 500ml 的低价样本有几条？
- 预期要点：
    - route = analysis
    - 按品牌和规格过滤低价样本
    - 返回数量或样本列表
- 实际输出：
    - route = unknown
    - tools_used = ["ask_llm"]
    - analysis_result = null
    - answer 返回“鸿茅药酒500ml的低价样本共有3条”，内容层面给出了数量结论
- 是否通过：
    - 部分通过
- 错误原因：
    - 问题本质上属于 analysis 类，但系统未命中分析路由，实际走了通用模型回答；虽然结果返回了数量，但没有通过 analysis_tools
      给出结构化分析结果，链路不符合预期

## A06

- 问题：显式阈值命中的低价样本有哪些？
- 预期要点：
    - route = analysis
    - 筛出显式阈值命中的样本
    - 低价规则来源包含 explicit_rule 或 both
- 实际输出：
    - route = unknown
    - tools_used = ["ask_llm"]
    - analysis_result = null
    - answer 未直接返回显式阈值命中的样本，而是要求补充具体阈值条件或相关数据信息
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于 analysis 类的条件筛选问题，系统应基于当前数据和既有低价规则直接筛出 explicit_rule / both 样本；实际却未命中
      analysis，退回通用模型追问，说明分析路由覆盖不足

## A07

- 问题：同时命中显式阈值和统计规则的样本有哪些？
- 预期要点：
    - route = analysis
    - 筛出低价规则来源为 both 的样本
    - analysis_result.ok = true
- 实际输出：
    - route = analysis
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - answer 返回了当前异常总览，包括总记录数、低价样本数、跨平台价差异常数和规格识别风险数
    - analysis_result 未按 both 条件筛出样本列表
- 是否通过：
    - 不通过
- 错误原因：
    - 系统虽然命中了 analysis 路由，但未按“同时命中显式阈值和统计规则”这一条件做定向筛选，结果退化成了 overview 总览，未返回
      both 样本

## A08

- 问题：淘宝平台的低价样本有多少？
- 预期要点：
    - route = analysis
    - 按平台过滤为淘宝
    - 返回数量
- 实际输出：
    - route = analysis
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - analysis_result 返回了疑似异常低价样本前 10 条，其中按表格统计，淘宝平台样本有 2 条
    - 但 answer 未直接总结“淘宝平台低价样本有 2 条”，而是泛化为低价样本总览
- 是否通过：
    - 部分通过
- 错误原因：
    - 系统命中了正确的 analysis 路由，且结果中可统计出淘宝样本数量，但最终回答没有直接按问题要求返回平台数量，输出收束不够准确

## A09

- 问题：拼多多平台的低价样本有多少？
- 预期要点：
    - route = analysis
    - 按平台过滤为拼多多
    - 返回数量
- 实际输出：
    - route = analysis
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - analysis_result 返回了疑似异常低价样本前 10 条，其中按表格统计，拼多多样本有 7 条
    - 但 answer 未直接总结“拼多多平台低价样本有 7 条”，而是泛化为低价样本总览
- 是否通过：
    - 部分通过
- 错误原因：
    - 系统命中了正确的 analysis 路由，且结果中可统计出拼多多样本数量，但最终回答没有直接按问题要求返回平台数量，输出收束不够准确

## A10

- 问题：低价规则来源为 both 的样本请列出来。
- 预期要点：
    - route = analysis
    - 返回低价规则来源为 both 的样本
    - table 中包含低价规则来源字段
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 命中了《疑似异常低价判定规则说明》的“低价规则来源字段说明”与“如果命中 both”相关章节
    - 但未返回任何样本列表，analysis_result = null
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于 analysis 类的条件筛选问题，但系统被“低价规则来源”“both”等关键词带偏，误路由到了
      retrieval；结果只解释了规则字段，没有列出 both 样本

---

## R01

- 问题：如果标题不完整，规则上该怎么处理？
- 预期要点：
    - route = retrieval
    - 命中 FAQ 或规格归一相关规则文档
    - retrieval_result.ok = true
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 该问题当前主要命中“规格归一与规格风险规则”相关规则。最相关证据来自《电商价格异常审核 Copilot - 第三周
      FAQ》的《15. 如果标题不完整，规则上该怎么处理？》章节。
- 是否通过：
    - 通过
- 错误原因：
    - 无

## R02

- 问题：低价异常规则是怎么定义的？
- 预期要点：
    - route = retrieval
    - 命中低价异常规则文档
    - 返回规则证据片段
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 该问题当前主要命中“低价异常规则”相关规则。最相关证据来自《疑似异常低价判定规则说明》的《1. 文档目的》章节。
- 是否通过：
    - 通过
- 错误原因：
    - 无

## R03

- 问题：跨平台价差异常是怎么判的？
- 预期要点：
    - route = retrieval
    - 命中跨平台价差规则文档
    - retrieval_result.ok = true
- 实际输出：
    - route = analysis
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - answer 返回了当前异常总览，包括任一异常数、疑似异常低价数、跨平台价差异常数和规格识别风险数
    - retrieval_result = null，未返回规则检索结果
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于规则检索 / 规则解释类问题，但系统误路由到了 analysis；回答内容变成了全局异常概览，没有解释跨平台价差异常的判定口径

## R04

- 问题：规格归一一般怎么处理？
- 预期要点：
    - route = retrieval
    - 命中规格归一规则文档
    - 返回规格归一相关依据
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 命中了《规格归一与规格风险识别规则说明》相关文档，并返回了规格归一与规格风险相关证据
    - 但 answer 主要是在说明命中了哪个规则文档和章节，没有进一步展开“规格归一一般怎么处理”的具体规则口径
- 是否通过：
    - 部分通过
- 错误原因：
    - 检索路由和证据命中正确，但回答内容偏浅，只指出了相关规则文档，未完整解释规格归一的处理方式

## R05

- 问题：人工复核时应该先看什么？
- 预期要点：
    - route = retrieval
    - 命中人工复核流程文档
    - answer 给出复核顺序或重点
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - answer 命中“人工复核流程说明”相关规则，并返回复核重点，但同时额外加入了当前异常样本概览
- 是否通过：
    - 不通过（或部分通过）
- 错误原因：
    - 路由结果偏离预期，本应走 retrieval，但实际走成了 mixed；虽然规则命中正确，但返回内容混入了分析概览，纯规则检索纯度不够

## R06

- 问题：低价规则来源字段是什么意思？
- 预期要点：
    - route = retrieval
    - 命中低价规则来源字段说明
    - answer 提到 explicit_rule / stat_rule / both 之一
    - 返回规则证据片段
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 成功命中《疑似异常低价判定规则说明》的《5. 低价规则来源字段说明》章节，并返回相关规则证据
    - 但 answer 只说明命中了相关章节，没有进一步解释 explicit_rule / stat_rule / both 的具体含义
- 是否通过：
    - 部分通过
- 错误原因：
    - 检索路由和证据命中都正确，但回答内容偏浅，只指出了相关规则章节，未完成对“低价规则来源字段”含义的直接解释

## R07

- 问题：统计规则和显式阈值规则有什么区别？
- 预期要点：
    - route = retrieval
    - 命中低价判定双轨规则文档
    - answer 比较两种规则差异
- 实际输出：
    - route = analysis
    - tools_used = ["analysis_tools"]
    - analysis_result.ok = true
    - answer 返回了当前异常概览，包括总记录数、低价数、跨平台价差异常数和规格风险数
    - retrieval_result = null，未返回规则检索结果
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于规则解释 / 检索类问题，但系统误路由到了 analysis；回答内容变成了全局异常概览，没有解释统计规则与显式阈值规则的差异

## R08

- 问题：FAQ 里是怎么说明标题不完整这个问题的？
- 预期要点：
    - route = retrieval
    - 优先命中 faq 文档
    - answer 明确提到 FAQ 或对应规则章节
- 实际输出：
    - route = unknown
    - tools_used = ["ask_llm"]
    - retrieval_result = null
    - answer 返回了一段通用化解释，说明标题不完整可能缺少品牌名、型号或关键特性等信息
- 是否通过：
    - 不通过
- 错误原因：
    - 问题本质上属于 FAQ / 规则检索类问题，但系统未命中 retrieval，实际走了通用模型回答；回答没有基于 FAQ
      文档或规则章节，且内容偏通用电商文案逻辑，不够贴合当前项目的业务规则语境

## R09

- 问题：规格风险识别主要依据什么？
- 预期要点：
    - route = retrieval
    - 命中规格风险识别规则
    - answer 说明风险识别口径
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 命中了《规格归一与规格风险识别规则说明》相关文档，并返回了规格风险识别相关证据
    - 但 answer 主要是在说明命中了哪个规则文档和章节，没有进一步展开“规格风险识别主要依据什么”的具体判断口径
- 是否通过：
    - 部分通过
- 错误原因：
    - 检索路由和证据命中正确，但回答内容偏浅，只指出了相关规则文档，未完整解释规格风险识别的依据与判断口径

## R10

- 问题：复核低价样本时需要重点关注哪些价格口径？
- 预期要点：
    - route = retrieval
    - 命中人工复核或低价规则文档
    - answer 提到券后价、补贴价、活动价、组合装等口径之一
- 实际输出：
    - route = retrieval
    - tools_used = ["retrieval_tools"]
    - retrieval_result.ok = true
    - answer 该问题当前主要命中“低价异常规则”相关规则。最相关证据来自《疑似异常低价判定规则说明》的《1. 文档目的》章节。
- 是否通过：
    - 通过
- 错误原因：
    - 无

---

## M01

- 问题：先找出低价商品，再按规则给我写一段简短汇报。
- 预期要点：
    - route = mixed
    - 先有低价样本分析结果
    - 再有规则依据
    - 最终 answer 为业务汇报风格
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - answer 先总结疑似异常低价样本数量，再引用低价异常规则依据，最后给出复核建议，整体为简短业务汇报风格。
- 是否通过：
    - 通过
- 错误原因：
    - 无

## M02

- 问题：近7天哪个平台异常低价最多？再解释一下为什么会这样判。
- 预期要点：
    - route = mixed
    - 先返回平台分析结果
    - 再补规则说明
    - 最终结论既有事实又有依据
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回异常低价数量最多的平台为拼多多，共 7 条
    - answer 在给出平台结论后，进一步补充了低价异常规则依据，并给出价格口径、活动口径、规格口径等复核建议
- 是否通过：
    - 通过
- 错误原因：
    - 无（备注：规则检索第一条证据排序仍有优化空间，当前首条命中 FAQ 中跨平台价差相关章节，不是最贴合“低价异常判定”问题的首证据）

## M03

- 问题：先找出鸿茅 500ml 的低价样本，再说明规则依据。
- 预期要点：
    - route = mixed
    - analysis_result 中有鸿茅 500ml 样本
    - retrieval_result 命中低价规则文档
    - answer 同时包含样本事实和规则依据
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回了疑似异常低价样本前 10 条，其中包含鸿茅 500ml 相关样本
    - retrieval_result 命中“低价异常规则”相关文档，并返回规则依据
    - 但 answer 未明确聚焦“鸿茅 500ml”的筛选结果，而是泛化为全部低价样本概览
- 是否通过：
    - 部分通过
- 错误原因：
    - mixed 链路和规则检索都正确，但分析阶段没有严格按“鸿茅 500ml”做定向汇总输出，结果粒度偏宽

## M04

- 问题：先列出同时命中 both 的样本，再给我一段复核建议。
- 预期要点：
    - route = mixed
    - 筛出 low_price_rule_source = both 的样本
    - 再结合规则给复核建议
    - 最终 answer 是审核建议风格
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - retrieval_result 命中“人工复核流程说明”相关规则，并给出复核依据
    - 但 analysis_result 返回的是全局异常概览，没有先筛出同时命中 both 的样本列表
- 是否通过：
    - 部分通过
- 错误原因：
    - mixed 路由和规则检索都正确，但分析阶段没有按“both 样本”这个条件进行定向筛选，导致结果变成 overview，总结粒度偏宽

## M05

- 问题：先看规格识别风险样本，再按规则写一个复核提醒。
- 预期要点：
    - route = mixed
    - analysis_result 返回规格风险样本
    - retrieval_result 返回规格风险处理规则
    - answer 为复核提醒风格
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回了 1 条规格识别风险样本，显示“规格列=250ml，标题规格=500ml”
    - retrieval_result 命中了《人工复核流程说明》的《5. 规格识别风险复核步骤》章节
    - 但 answer 主要在说明样本数量和规则来源，没有进一步展开成明确的复核提醒话术
- 是否通过：
    - 部分通过
- 错误原因：
    - mixed 路由、样本分析和规则检索都正确，但最终 answer 的提醒性不够强，没有明确给出“先核对标题规格与规格列是否一致、优先确认真实规格口径”等具体复核动作

## M06

- 问题：先找出跨平台价差最大的品牌，再解释规则口径。
- 预期要点：
    - route = mixed
    - 先有品牌与价差结论
    - 再有跨平台价差规则依据
    - 最终 answer 可读性强
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回当前跨平台价差最大的品牌为鸿茅，规格为 500ml，价差金额 576.00，价差比例约 0.824
    - retrieval_result 命中了《跨平台价差异常判定规则说明》相关文档，并返回跨平台价差规则依据
    - answer 在给出品牌结论后，进一步补充了规则口径和复核建议，整体表达清晰
- 是否通过：
    - 通过
- 错误原因：
    - 无

## M07

- 问题：先看淘宝平台的低价样本，再总结是否需要人工复核。
- 预期要点：
    - route = mixed
    - analysis_result 返回淘宝低价样本
    - retrieval_result 命中人工复核规则
    - answer 明确给出是否需要优先复核的判断
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回了疑似异常低价样本前 10 条，其中包含淘宝平台样本，但未单独按淘宝平台做结果收束
    - retrieval_result 命中了低价异常规则与人工复核相关文档
    - answer 给出了复核建议，但没有明确输出“淘宝平台样本是否需要优先人工复核”的判断
- 是否通过：
    - 部分通过
- 错误原因：
    - mixed 路由、规则检索和总体分析都正确，但分析结果没有严格聚焦淘宝平台，最终 answer 也未直接回答“是否需要优先人工复核”这一判断问题

## M08

- 问题：先输出当前低价前10条，再按规则给我一段业务汇报。
- 预期要点：
    - route = mixed
    - analysis_result.row_count > 0
    - retrieval_result 提供低价规则依据
    - answer 形成简短业务汇报
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - retrieval_result 返回了低价异常规则相关依据
    - 但 analysis_result 返回的是 overview 总览，没有先输出当前低价前10条样本
    - answer 也随之变成异常总览 + 规则依据，而不是基于前10条低价样本形成的业务汇报
- 是否通过：
    - 不通过
- 错误原因：
    - mixed 路由和规则检索正确，但分析阶段没有完成“先输出当前低价前10条”这一核心任务，结果退化成 overview，总结对象与问题要求不一致

## M09

- 问题：先回答标题不完整时该怎么处理，再结合低价样本给复核建议。
- 预期要点：
    - route = mixed
    - 先有标题不完整处理规则
    - 再关联到低价样本复核
    - 最终 answer 是综合性建议
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - retrieval_result 命中了 FAQ 中“如果标题不完整，规则上该怎么处理？”相关章节
    - analysis_result 返回了当前疑似异常低价样本前 10 条
    - 但 answer 没有先明确说明“标题不完整时如何处理”，而是泛化为低价样本概览、低价规则依据和复核建议
- 是否通过：
    - 部分通过
- 错误原因：
    - mixed 路由、FAQ 检索和低价样本分析都正确，但最终回答没有完整按“先答标题不完整处理规则，再结合低价样本给复核建议”的顺序组织输出，结果焦点偏向低价总览

## M10

- 问题：请先统计当前疑似异常低价样本数量，再按规则总结最该优先复核什么。
- 预期要点：
    - route = mixed
    - analysis_result 给出疑似低价数量
    - retrieval_result 给出低价规则或复核规则依据
    - answer 明确优先复核项
- 实际输出：
    - route = mixed
    - tools_used = ["analysis_tools", "retrieval_tools", "report_tools"]
    - analysis_result.ok = true，retrieval_result.ok = true
    - analysis_result 返回当前共识别出 10 条疑似异常低价样本
    - answer 规则依据方面，当前主要命中“低价异常规则”相关内容，主要参考《疑似异常低价判定规则说明》的《1. 文档目的》章节。
      建议后续优先复核低价样本的价格口径、活动口径及规格口径，确认是否存在券后价、补贴价或组合装等特殊情况。
- 是否通过：
    - 通过
- 错误原因：
    - 无
