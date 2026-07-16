# app/main.py
"""课次 10.01～10.04 · ai-bff 入口。

10.01：BFF 自身可启动。
10.02：/health 聚合探测下游。
10.03：/api/chat/stream 转发 SSE（边读边写）。
10.04：入站验用户 Bearer；出站盖内部头（租户/模型/内部令牌）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import authenticate_request, build_downstream_headers
from app.clients.ai_http import check_ai_health
from app.clients.ai_stream import iter_upstream_sse
from app.config import AI_SERVICE_BASE_URL, APP_NAME, BFF_PORT

app = FastAPI(title=APP_NAME, description="BFF：鉴权与转发，不做 RAG/Agent")


class ChatStreamIn(BaseModel):
    """前端 → BFF 的流式聊天入参。"""

    message: str = Field(default="", description="用户输入")
    # 前端可建议模型；BFF 按租户白名单裁剪
    model_id: str = Field(default="default", alias="modelId", description="偏好模型")

    model_config = {"populate_by_name": True}


@app.get("/health")
def health() -> dict[str, object]:
    """BFF 探活：自身 ok + 下游 ai 汇总（无需用户鉴权）。"""
    ai = check_ai_health()
    overall = "ok" if ai.get("ai") == "up" else "degraded"
    return {
        "status": overall,
        "app": APP_NAME,
        "role": "bff",
        "downstream": AI_SERVICE_BASE_URL,
        "ai": ai.get("ai"),
        "code": ai.get("code"),
        "detail": ai.get("detail"),
        "error": ai.get("error"),
    }


@app.post("/api/chat/stream")
async def chat_stream(body: ChatStreamIn, request: Request) -> StreamingResponse:
    """鉴权 → 盖内部头 → 边读边写转发 SSE。

    查询参数 tenantId 即使伪造也会被忽略，租户只认 Authorization 解析结果。
    """
    principal = authenticate_request(request)
    forged = request.query_params.get("tenantId")
    headers = build_downstream_headers(
        principal,
        model_id=body.model_id,
        ignore_query_tenant=forged,
    )

    async def gen() -> Any:
        async for chunk in iter_upstream_sse(
            body.message,
            request=request,
            downstream_headers=headers,
        ):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            # 便于联调看到 BFF 实际采用的租户（不是伪造查询参）
            "X-Resolved-Tenant": principal.tenant_id,
        },
    )


@app.get("/meta/layers")
def meta_layers() -> dict[str, object]:
    """给前端/运维看的边界说明（演示用，生产可关掉）。"""
    from app.layers import LAYERS, mcp_vs_bff, why_separate

    return {
        "layers": LAYERS,
        "why_separate": why_separate(),
        "mcp_vs_bff": mcp_vs_bff(),
    }


def run() -> None:
    """本地启动：uvicorn app.main:app --port $BFF_PORT。"""
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=BFF_PORT, reload=False)


if __name__ == "__main__":
    run()
