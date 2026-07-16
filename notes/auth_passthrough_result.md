# 10.04 鉴权透传 · 实跑记录


## 演示账号

- `Bearer tok-alice` → tenant=`tenant-a` models=`['default', 'fast']`
- `Bearer tok-bob` → tenant=`tenant-b` models=`['default']`

## STEP 1

- 无 Token → `401`

## STEP 2

- 伪造 `tenant-b` 被忽略，下游=`tenant-a`

## STEP 3

- 非法 modelId → `403`

## STEP 4

- echo: `{'tenant_id': 'tenant-a', 'user_id': 'u-alice', 'model_id': 'fast', 'request_id': 'req-e2e-004'}`
- done: `{'type': 'done', 'tenant_id': 'tenant-a', 'user_id': 'u-alice', 'model_id': 'fast', 'request_id': 'req-e2e-004'}`

## STEP 5 · curl

```bash
curl -N -X POST 'http://127.0.0.1:8088/api/chat/stream?tenantId=tenant-b' \
  -H 'Authorization: Bearer tok-alice' -H 'Content-Type: application/json' \
  -d '{"message":"hello","modelId":"default"}'
```
