# 日志字段规范（3号窗口正式版）

## 1. 文档目的

本文档用于统一项目日志字段口径，确保后续 4~8 号窗口接入 logger 时，输出格式一致、关键链路可追踪、问题可定位。

3 号窗口当前重点不是把所有日志都落库，而是先统一：

- 日志格式
- 日志上下文字段
- 请求级链路字段
- 后续 ask / model / review 留痕的衔接方向

## 2. 日志分层原则

### 2.1 当前日志分为两层

#### A. 运行日志

用于控制台 / 文件日志输出，记录系统运行过程。

典型内容：

- 请求进入
- 请求结束
- 异常栈
- 模块关键节点打点

#### B. 业务留痕日志

用于后续数据库落点，当前由 2 号窗口已预留表结构：

- ask_log
- model_call_log
- review_record

3 号窗口当前只定义其衔接方向，不主写完整落库逻辑。

## 3. 当前正式日志格式

当前 logger 统一格式为：

```text
%(asctime)s | %(levelname)s | %(name)s | trace_id=%(trace_id)s | %(request_method)s %(request_path)s | %(message)s
```

日志字段含义如下：

| 字段             | 含义               |
|----------------|------------------|
| asctime        | 日志时间             |
| levelname      | 日志级别             |
| name           | logger 名称，一般为模块名 |
| trace_id       | 链路追踪 ID          |
| request_method | HTTP 方法          |
| request_path   | 请求路径             |
| message        | 日志正文             |

## 4. 当前上下文字段来源

### 4.1 trace_id

来源：

- 请求头 `X-Trace-Id`，若存在则继承
- 若不存在，由服务端生成

### 4.2 request_method

来源：

- 当前请求的方法，如 GET / POST

### 4.3 request_path

来源：

- 当前请求路径，如 `/ask`、`/extract`

这些字段由 middleware + ContextVar 维护，并由 `RequestContextFilter` 自动注入日志记录。

## 5. 当前日志级别建议

| 级别        | 用法                 |
|-----------|--------------------|
| INFO      | 正常链路打点、请求进入/结束     |
| WARNING   | 可预期业务异常、校验失败       |
| ERROR     | 已知失败但不一定带完整堆栈      |
| EXCEPTION | 未捕获异常或需要记录完整异常栈时使用 |

## 6. 当前日志使用规范

### 6.1 模块 logger 获取方式

统一使用：

```python
logger = get_logger(__name__)
```

### 6.2 不建议正式代码继续大量使用 print

临时调试可以用，正式链路统一用 logger。

### 6.3 日志正文尽量包含可定位信息

例如：

- code
- path
- cost_ms
- 异常 detail
- 关键业务标识（后续窗口逐步补充）

## 7. 当前已确定的请求链打点

### 7.1 请求进入

middleware 中记录：

- 请求进入
- trace_id
- 请求方法
- 请求路径

### 7.2 请求结束

middleware 中记录：

- 请求结束
- 耗时 cost_ms

### 7.3 异常日志

handlers 中记录：

- AppException
- RequestValidationError
- 未捕获异常

## 8. 后续与数据库日志表的关系

### 8.1 ask_log

用于承接问答主请求级别留痕。

### 8.2 model_call_log

用于承接模型调用明细级别留痕。

### 8.3 review_record

用于承接复核动作审计留痕。

3 号窗口当前日志设计必须与上述对象兼容，但不在本阶段主写完整持久化逻辑。

## 9. 当前约束

### 9.1 不允许每个模块自定义一套日志格式

统一走 `setup_logging()` 初始化。

### 9.2 不允许关键链路没有 trace_id

后续 ask / model / review 相关模块必须尽量继承当前 trace 口径。

### 9.3 不允许日志和接口文档长期脱节

日志字段若新增关键字段，应同步补本文档。

## 10. 一句话总结

日志不是为了“看着热闹”，而是为了后续任何接口、服务、检索、模型调用出了问题都能追。