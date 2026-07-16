# 10.05 前端消费 SSE · 实跑记录


## STEP 1

- chat=200 fetch/abort/buffer OK；docs OK

## STEP 2

- joined=`你好` types=`['token', 'token', 'done']`

## STEP 3

- joined=`收到：退货（mock 流）` done=`{'type': 'done', 'tenant_id': 'tenant-a', 'user_id': 'u-alice', 'model_id': 'default', 'request_id': 'req-2615a8160b8c'}`

## STEP 4

- 模拟 Abort：提前 close stream

## STEP 5

- 浏览器：`http://127.0.0.1:8088/chat`
