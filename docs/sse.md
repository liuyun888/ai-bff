# docs/sse.md
# 前端对接 SSE（课次 10.05 / 11.05）

面向 Web / App / 小程序任选一端落地。事件约定与鉴权与 `ai-bff` 现网一致。

## 两页对照（勿互相覆盖）

| 页面 | 课次 | API | 下游 | 说明 |
|------|------|-----|------|------|
| `GET /chat` · `static/chat/` | 10.05 | `POST /api/chat/stream` | `/v1/chat/stream` | mock「收到…」教学页，**按正文复现请用此页** |
| `GET /assistant` · `static/assistant/` | 11.05 | `POST /api/assistant/stream` | `/v1/assistant/stream` | 统一助手（库存/客服/工单/知识库） |

## 接口明细

### 正式助手（11.05）

| 项 | 值 |
|----|-----|
| URL | `POST /api/assistant/stream` |
| Content-Type | `application/json` |
| Authorization | `Bearer <token>`（必填） |
| Body | `{"message":"...","modelId":"default"}` |
| 响应 | `text/event-stream` |

### 教学 mock（10.05）

| 项 | 值 |
|----|-----|
| URL | `POST /api/chat/stream` |
| 下游 | 「收到…（mock 流）」 |

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
- 优先 **fetch + ReadableStream**；不要用 EventSource 硬扛 Token
- 11.05 的 `done` 还可含 `mode` / `action` / `guard_triggered` / `case_id`

## 本地打开

```bash
# 终端 A：ai-service
cd ../ai-service && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
# 终端 B：ai-bff
cd ../ai-bff && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8088

open http://127.0.0.1:8088/chat        # 10.05 mock
open http://127.0.0.1:8088/assistant   # 11.05 真助手
```

## 停止生成

前端：`AbortController.abort()` → 请求断开 → BFF/ai-service 侧应停止继续写（见 10.03）。

## 小程序 / App

| 端 | 建议 |
|----|------|
| 小程序 | 用支持流式的 request；自建 SSE buffer |
| App | OkHttp / URLSession 读 chunk；事件解析与 Web 一致 |

鉴权透传见 10.04；统一编排见 11.05。
