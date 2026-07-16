# app/clients/ai_stream.py
"""课次 10.03～10.04 · BFF 转发 ai-service 的 SSE（边读边写）。

大忌：不要 .read() / .json() 整包缓冲后再返回——会失去打字机效果。
10.04：必须带下游标准头（内部令牌 + 租户等）；无头时仅补 INTERNAL_TOKEN 不够，
      正式路径应由 auth.build_downstream_headers 生成完整头。
客户端断开时跳出循环，关闭下游 stream，避免空跑。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import Request

from app.config import (
    AI_CONNECT_TIMEOUT,
    AI_SERVICE_BASE_URL,
    AI_STREAM_READ_TIMEOUT,
    INTERNAL_TOKEN,
)

# 10.03 教学 mock 流（验收「收到…mock」）
CHAT_STREAM_PATH = "/v1/chat/stream"
# 11.05 统一助手真流（/chat 页正式入口）
ASSISTANT_STREAM_PATH = "/v1/assistant/stream"


def stream_timeout() -> httpx.Timeout:
    """流式专用超时：连接短、读空闲可较长。"""
    return httpx.Timeout(
        connect=AI_CONNECT_TIMEOUT,
        read=AI_STREAM_READ_TIMEOUT,
        write=30.0,
        pool=AI_CONNECT_TIMEOUT,
    )


def _merge_headers(extra: dict[str, str] | None) -> dict[str, str]:
    """默认带 Accept + 内部令牌；extra 可覆盖（正式路径应带齐租户头）。"""
    base = {
        "Accept": "text/event-stream",
        "X-Internal-Token": INTERNAL_TOKEN,
    }
    if extra:
        base.update(extra)
    return base


async def iter_upstream_sse(
    message: str,
    *,
    request: Request | None = None,
    base_url: str | None = None,
    downstream_headers: dict[str, str] | None = None,
    path: str | None = None,
    session_id: str = "",
) -> AsyncIterator[bytes]:
    """向下游开 SSE，边收边 yield 原始字节。

    参数:
        message: 用户消息
        request: 上游（浏览器）请求；断开则停止转发
        base_url: 可覆盖配置，便于演示注入临时端口
        downstream_headers: 10.04 内部头（租户/用户/模型/request_id）
        path: 下游路径；默认 CHAT_STREAM_PATH（mock）；助手用 ASSISTANT_STREAM_PATH
        session_id: 11.05 会话 id（仅助手流有用）
    """
    root = (base_url or AI_SERVICE_BASE_URL).rstrip("/")
    url = f"{root}{(path or CHAT_STREAM_PATH)}"
    cancelled = False
    headers = _merge_headers(downstream_headers)
    body: dict[str, Any] = {"message": message}
    if session_id:
        body["session_id"] = session_id
    async with httpx.AsyncClient(timeout=stream_timeout()) as client:
        async with client.stream(
            "POST",
            url,
            json=body,
            headers=headers,
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
    downstream_headers: dict[str, str] | None = None,
) -> AsyncIterator[bytes]:
    """反面教材：先把下游读完再一次性吐出（失去流式）。

    仅用于演示对比，生产禁止。
    """
    root = (base_url or AI_SERVICE_BASE_URL).rstrip("/")
    url = f"{root}{CHAT_STREAM_PATH}"
    headers = _merge_headers(downstream_headers)
    async with httpx.AsyncClient(timeout=stream_timeout()) as client:
        async with client.stream(
            "POST",
            url,
            json={"message": message},
            headers=headers,
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
