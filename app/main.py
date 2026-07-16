# app/main.py
"""课次 10.01～10.02 · ai-bff 入口。

10.01：BFF 自身可启动。
10.02：/health 聚合探测下游 ai-service（超时/降级，不抛裸堆栈）。
"""

from __future__ import annotations

from fastapi import FastAPI

from app.clients.ai_http import check_ai_health
from app.config import AI_SERVICE_BASE_URL, APP_NAME, BFF_PORT

app = FastAPI(title=APP_NAME, description="BFF：鉴权与转发，不做 RAG/Agent")


@app.get("/health")
def health() -> dict[str, object]:
    """BFF 探活：自身 ok + 下游 ai 汇总。

    下游挂了也不返回 500 空白，而是 ai=down/timeout + 稳定 code。
    """
    ai = check_ai_health()
    # BFF 进程活着 → status 仍 ok；用 ai 字段表达下游
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
