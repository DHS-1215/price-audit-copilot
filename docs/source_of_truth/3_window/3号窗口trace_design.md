# Trace 设计说明（3号窗口正式版）

## 1. 文档目的

本文档用于正式定义项目 trace_id 设计口径，确保后续 ask / model / review / retrieval / rule 等链路都能围绕统一 trace_id
进行串联。

3 号窗口当前目标不是上复杂分布式追踪系统，而是先把“请求级追踪”这件事做稳。

## 2. 设计目标

当前 trace_id 设计要满足以下目标：

1. 每次请求都有唯一 trace_id
2. 请求头可透传 trace_id
3. 系统内部日志可自动带 trace_id
4. 接口响应可回传 trace_id
5. 后续 ask_log / model_call_log / review_record 可挂接同一 trace_id

## 3. 当前正式口径

### 3.1 请求头名称

统一使用：

```text
X-Trace-Id
```

当前也允许通过配置项 `TRACE_HEADER_NAME` 调整，但默认正式口径仍为 `X-Trace-Id`。

### 3.2 trace_id 生成规则

当前由服务端使用 `uuid.uuid4().hex` 生成。

### 3.3 trace_id 继承规则

请求进入时：

1. 优先读取请求头中的 `X-Trace-Id`
2. 若请求头没有，则由服务端生成新 trace_id
3. 写入 `request.state.trace_id`
4. 写入 `ContextVar`
5. 响应头回写 `X-Trace-Id`

## 4. 当前链路位置

### 4.1 middleware

负责：

- 解析 trace_id
- 注入请求上下文
- 记录请求进入/结束日志
- 在响应头写回 trace_id

### 4.2 context

负责：

- 保存当前请求 trace_id
- 保存 request_method
- 保存 request_path

### 4.3 logger

负责：

- 从上下文中读取 trace_id
- 自动打入日志格式

### 4.4 handlers

负责：

- 在错误响应中带回 trace_id
- 让异常响应与运行日志能对上

## 5. 当前为什么只做到请求级 trace

当前项目还处于 3 号窗口阶段，重点是先统一基础设施口径，而不是提前引入复杂 tracing 平台。

当前请求级 trace 已经足够支撑：

- 接口排错
- ask 主链追踪
- model 调用衔接
- review 动作审计预留

后续如果有必要，可以继续扩展 span / child-call 粒度，但不是当前窗口主目标。

## 6. 与后续窗口的关系

### 6.1 对 4 号窗口

规则引擎服务应尽量复用当前 trace_id，避免判定过程日志成为孤岛。

### 6.2 对 5 号窗口

检索与解释链路日志应继承当前 trace_id。

### 6.3 对 6 号窗口

`/ask` 与增强链路的 ask_log、model_call_log 必须围绕 trace_id 串联。

### 6.4 对 7 号窗口

review_record 等动作留痕应尽量保留 trace_id 关联能力。

## 7. 当前约束

### 7.1 不允许后续模块另起一套 trace 字段名

正式口径统一为 `trace_id`。

### 7.2 不允许后续模块跳过现有 trace 传播方式

后续模块应优先从上下文中读取 trace_id，而不是自己重新造。

### 7.3 不允许只打日志不带 trace

关键链路日志必须尽量带 trace_id。

## 8. 当前已知边界

当前 trace 设计仍然是“请求级主键”，不是完整 APM 系统。  
这不是缺陷，而是当前阶段的合理边界。

## 9. 一句话总结

trace_id 是后续 ask / model / review / retrieval / rule 这些链路能不能真正串起来的主线。