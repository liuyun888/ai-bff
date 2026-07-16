# ai-bff

**Backend for Frontend**：给前端（Web / App / 小程序）做适配的业务网关。

## 仓库地址

| 平台 | 地址 |
|------|------|
| Gitee（origin） | `git@gitee.com:liuyunkai666/ai-bff.git` |
| GitHub | `git@github.com:liuyun888/ai-bff.git` |

本地首次关联远程（与 `ai-service` 约定一致：`origin` = Gitee，`github` = GitHub）：

```bash
cd ai-bff
git remote add origin git@gitee.com:liuyunkai666/ai-bff.git
git remote add github git@github.com:liuyun888/ai-bff.git
git push -u origin main
git push -u github main
```

## 职责（本层该做）

- 鉴权、限流、参数校验
- 转发 / 聚合到 `ai-service`
- SSE 透传（10.03）与鉴权上下文下沉（10.04）
- 前端演示页与对接说明（10.05）
- 统一打点、追踪 id

## 不职责（别塞进来）

- Embedding、Milvus、向量检索
- Prompt 工程、Agent Loop、复杂 RAG
- 直接持有并下发**模型密钥**给前端

## 上下游

```text
前端(/chat)  →  ai-bff  →  ai-service
                  ↑
             本仓库（可配置 AI_SERVICE_BASE_URL）
```

| 配置 | 含义 | 默认示例 |
|------|------|----------|
| `AI_SERVICE_BASE_URL` | 下游 AI 引擎根地址 | `http://127.0.0.1:8001` |
| `BFF_PORT` | BFF 监听端口 | `8088` |
| `INTERNAL_TOKEN` | 与 ai-service 共享的内部密钥 | `dev-internal-token` |
| `AI_STREAM_READ_TIMEOUT` | SSE 读空闲超时（秒） | `120.0` |

本地配置：复制 `.env.example` 为 `.env`（`.env` 已进 `.gitignore`，勿提交密钥）。

## 前端消费 SSE（10.05）

- 演示页：起服务后打开 `http://127.0.0.1:8088/chat`
- 对接说明：[`docs/sse.md`](docs/sse.md)
- 验收：`python scripts/10_05_frontend_sse_demo.py`

## 与 MCP 的关系

- **MCP**：开发期工具调试（IDE 连工具箱）
- **BFF**：产品流量入口（端上用户请求）

二者不互相替代。

## 本模块验收脚本

```bash
cd ai-bff
.venv/bin/python scripts/10_01_bff_pattern_demo.py
.venv/bin/python scripts/10_02_http_client_demo.py
.venv/bin/python scripts/10_03_sse_forward_demo.py
.venv/bin/python scripts/10_04_auth_passthrough_demo.py
.venv/bin/python scripts/10_05_frontend_sse_demo.py
```

联调：先起 `ai-service`（端口 8001），再 `uvicorn app.main:app --port 8088`。
