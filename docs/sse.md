# docs/sse.md
# 前端对接 SSE（课次 10.05）

面向 Web / App / 小程序任选一端落地。事件约定与鉴权与 `ai-bff` 现网一致。

## 接口

| 项 | 值 |
|----|-----|
| URL | `POST /api/chat/stream` |
| Content-Type | `application/json` |
| Authorization | `Bearer <token>`（必填） |
| Body | `{"message":"...","modelId":"default"}` |
| 响应 | `text/event-stream` |

演示 Token：

| Token | 租户 | 允许 modelId |
|-------|------|----------------|
| `tok-alice` | tenant-a | default, fast |
| `tok-bob` | tenant-b | default |

## 事件格式

```text
data: {"type":"token","text":"你"}

data: {"type":"token","text":"好"}

data: {"type":"done","tenant_id":"...","user_id":"...","model_id":"...","request_id":"..."}

data: {"type":"error","message":"..."}
```

- 按 `\n\n` 拆事件；chunk 可能劈开一行 → **必须自建 buffer**
- 优先 **fetch + ReadableStream**（可带头、可 POST）；不要用 EventSource 硬扛 Token

## Web 示例页

本仓库已挂静态页（与 API **同源**，免 CORS 折腾）：

```bash
# 终端 A
cd ../ai-service && .venv/bin/uvicorn app.main:app --port 8001
# 终端 B
cd ../ai-bff && .venv/bin/uvicorn app.main:app --port 8088
# 浏览器
open http://127.0.0.1:8088/chat
```

源码：`static/chat/`（`app.js` 含 AbortController）。

## 停止生成

前端：`AbortController.abort()` → 请求断开 → BFF/ai-service 侧应停止继续写（见 10.03）。

## 小程序 / App

| 端 | 建议 |
|----|------|
| 微信小程序 | 若无法真流式，对接说明里写「降级一次返回」；有分片回调则按同样事件解析 |
| iOS | URLSession 流式读 body |
| Android | OkHttp 流式读 |

原则：**事件 JSON 约定不变**；变的是传输层是否支持边读边画。

## 验收脚本

```bash
cd ai-bff
.venv/bin/python scripts/10_05_frontend_sse_demo.py
```
