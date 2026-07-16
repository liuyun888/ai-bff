# app/clients/ai_stream.py
"""课次 10.03 · BFF 转发 ai-service 的 SSE（边读边写）。

大忌：不要 .read() / .json() 整包缓冲后再返回——会失去打字机效果。
客户端断开时跳出循环，关闭下游 stream，避免空跑。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import Request

from app.config import AI_CONNECT_TIMEOUT, AI_SERVICE_BASE_URL, AI_STREAM_READ_TIMEOUT

CHAT_STREAM_PATH = "/v1/chat/stream"


def stream_timeout() -> httpx.Timeout:
    """流式专用超时：连接短、读空闲可较长。"""
    return httpx.Timeout(
        connect=AI_CONNECT_TIMEOUT,
        read=AI_STREAM_READ_TIMEOUT,
        write=30.0,
        pool=AI_CONNECT_TIMEOUT,
    )


async def iter_upstream_sse(
    message: str,
    *,
    request: Request | None = None,
    base_url: str | None = None,
) -> AsyncIterator[bytes]:
    """向下游开 SSE，边收边 yield 原始字节。

    参数:
        message: 用户消息
        request: 上游（浏览器）请求；断开则停止转发
        base_url: 可覆盖配置，便于演示注入临时端口
    """
    root = (base_url or AI_SERVICE_BASE_URL).rstrip("/")
    url = f"{root}{CHAT_STREAM_PATH}"
    cancelled = False
    async with httpx.AsyncClient(timeout=stream_timeout()) as client:
        async with client.stream(
            "POST",
            url,
            json={"message": message},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if request is not None and await request.is_disconnected():
                    cancelled = True
                    break
                if chunk:
                    yield chunk
    if cancelled and request is not None:
        setattr(request.state, "downstream_cancelled", True)


async def buffer_all_then_yield(
    message: str,
    *,
    base_url: str | None = None,
) -> AsyncIterator[bytes]:
    """反面教材：先把下游读完再一次性吐出（失去流式）。

    仅用于演示对比，生产禁止。
    """
    root = (base_url or AI_SERVICE_BASE_URL).rstrip("/")
    url = f"{root}{CHAT_STREAM_PATH}"
    async with httpx.AsyncClient(timeout=stream_timeout()) as client:
        async with client.stream(
            "POST",
            url,
            json={"message": message},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            # 错误示范：整包攒齐
            blob = await resp.aread()
    yield blob


def parse_sse_events(raw: str) -> list[dict[str, Any]]:
    """把拼接的 SSE 文本拆成事件列表（验收用）。"""
    import json

    events: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        line = block.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            events.append({"type": "raw", "text": payload})
    return events
