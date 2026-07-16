# app/main.py
"""课次 10.01～10.03 · ai-bff 入口。

10.01：BFF 自身可启动。
10.02：/health 聚合探测下游。
10.03：/api/chat/stream 转发 SSE（边读边写）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.clients.ai_http import check_ai_health
from app.clients.ai_stream import iter_upstream_sse
from app.config import AI_SERVICE_BASE_URL, APP_NAME, BFF_PORT

app = FastAPI(title=APP_NAME, description="BFF：鉴权与转发，不做 RAG/Agent")


class ChatStreamIn(BaseModel):
    """前端 → BFF 的流式聊天入参。"""

    message: str = Field(default="", description="用户输入")


@app.get("/health")
def health() -> dict[str, object]:
    """BFF 探活：自身 ok + 下游 ai 汇总。"""
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
    """把 ai-service 的 SSE 边读边写转给前端。

    客户端断开时，iter_upstream_sse 会停止读取并关闭下游连接。
    """

    async def gen() -> Any:
        async for chunk in iter_upstream_sse(body.message, request=request):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
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
