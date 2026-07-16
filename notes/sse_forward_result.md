# 10.03 SSE 流式转发 · 实跑记录


## STEP 1 · 断连

- **ai_service**：iter_chat_tokens 检查 request.is_disconnected → 停止 yield
- **bff**：iter_upstream_sse 检查上游 disconnect → break → 关闭 httpx stream
- **goal**：客户端断开后取消下游，避免模型空跑烧钱
- **status**：已实现（mock 间隔可观察；真模型需把 cancel 传到 Provider）

## STEP 2 · 流式转发

- base: `http://127.0.0.1:64583`
- joined: `收到：退货要几天（mock 流）`
- arrivals: 17

## STEP 3 · 缓冲对比

- buffer_arrivals=1（错误示范）

## STEP 4 · 约定

- token / done / error

## STEP 5 · curl

```bash
curl -N -X POST http://127.0.0.1:8088/api/chat/stream -H 'Content-Type: application/json' -d '{"message":"hello"}'
```
