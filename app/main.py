# app/main.py
"""课次 10.01 · ai-bff 最小入口。

本课只暴露 BFF 自身探活，证明网关进程能起来。
转发 ai-service /health、聊天、SSE → 留给 10.02 / 10.03。
"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import AI_SERVICE_BASE_URL, APP_NAME, BFF_PORT

app = FastAPI(title=APP_NAME, description="BFF：鉴权与转发，不做 RAG/Agent")


@app.get("/health")
def health() -> dict[str, object]:
    """BFF 自身探活（还不探测下游；10.02 再聚合 ai-service）。"""
    return {
        "status": "ok",
        "app": APP_NAME,
        "role": "bff",
        "downstream": AI_SERVICE_BASE_URL,
        "note": "下游探活见 10.02",
    }


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
