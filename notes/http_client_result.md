# 10.02 服务间 HTTP 调用 · 实跑记录


## STEP 1 · 方向

- **BFF → ai-service**：聊天、检索、本课 /health（超时要短于网关总超时）
- **ai-service → 业务 API**：查订单 Tool、库存 API（鉴权、幂等、熔断（Tool 课已接触））

## STEP 2 · 配置

- `{'AI_SERVICE_BASE_URL': 'http://127.0.0.1:8001', 'AI_CONNECT_TIMEOUT': 2.0, 'AI_READ_TIMEOUT': 3.0, 'AI_HEALTH_MAX_RETRIES': 2}`

## STEP 3 · up

- `{'base_url': 'http://127.0.0.1:60917', 'result': {'ai': 'up', 'code': 'OK', 'detail': {'status': 'ok', 'app': 'mock-ai-service'}}}`

## STEP 4 · down

- `{'ai': 'down', 'code': 'AI_UNAVAILABLE', 'error': 'ConnectError'}`

## STEP 5 · timeout

- `{'ai': 'timeout', 'code': 'AI_TIMEOUT', 'error': 'TimeoutException'}`

## STEP 6 · 纪律与实探

- post: `{'raised': True, 'error': '非幂等 POST 禁止 retry=True（避免重复扣费/重复下单）'}`
- live: `{'ai': 'down', 'code': 'AI_UNAVAILABLE', 'error': 'http_502'}`
