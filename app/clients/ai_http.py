# app/clients/ai_http.py
"""课次 10.02 · BFF → ai-service 的 HTTP 客户端。

纪律：
- 连接超时 + 读超时都要显式设置
- 仅对幂等 GET（如 /health）做有限重试；POST 聊天默认不重试
- 错误映射为稳定码，不把下游堆栈甩给前端
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import (
    AI_CONNECT_TIMEOUT,
    AI_READ_TIMEOUT,
    AI_SERVICE_BASE_URL,
    AI_HEALTH_MAX_RETRIES,
)

# 稳定错误码（给前端 / 运维看，不要 Traceback）
ERR_AI_UNAVAILABLE = "AI_UNAVAILABLE"
ERR_AI_TIMEOUT = "AI_TIMEOUT"
ERR_BAD_REQUEST = "BAD_REQUEST"
ERR_AI_BAD_RESPONSE = "AI_BAD_RESPONSE"


def _timeout() -> httpx.Timeout:
    """显式超时：connect + read（可调配置）。"""
    return httpx.Timeout(
        connect=AI_CONNECT_TIMEOUT,
        read=AI_READ_TIMEOUT,
        write=AI_READ_TIMEOUT,
        pool=AI_CONNECT_TIMEOUT,
    )


class AiServiceClient:
    """调 ai-service 的薄客户端。

    参数:
        base_url: 下游根地址；None 则读配置
        transport: 可注入 MockTransport（单测/演示不通场景）
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or AI_SERVICE_BASE_URL).rstrip("/")
        self._transport = transport

    def _client(self) -> httpx.Client:
        kwargs: dict[str, Any] = {"timeout": _timeout(), "base_url": self.base_url}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def get_health(self) -> dict[str, Any]:
        """GET /health；幂等，可有限重试。

        返回:
            统一结构：{ai, code?, detail?, error?}
            ai ∈ up | timeout | down
        """
        last_err: str = ""
        attempts = max(1, AI_HEALTH_MAX_RETRIES)
        for i in range(attempts):
            try:
                with self._client() as client:
                    r = client.get("/health")
                if r.status_code >= 500:
                    last_err = f"http_{r.status_code}"
                    if i + 1 < attempts:
                        time.sleep(0.05 * (i + 1))
                        continue
                    return {
                        "ai": "down",
                        "code": ERR_AI_UNAVAILABLE,
                        "error": last_err,
                    }
                if r.status_code >= 400:
                    return {
                        "ai": "down",
                        "code": ERR_BAD_REQUEST,
                        "error": f"http_{r.status_code}",
                        "detail": _safe_body(r),
                    }
                try:
                    detail = r.json()
                except Exception:  # noqa: BLE001
                    return {
                        "ai": "down",
                        "code": ERR_AI_BAD_RESPONSE,
                        "error": "invalid_json",
                    }
                return {"ai": "up", "code": "OK", "detail": detail}
            except httpx.TimeoutException:
                return {"ai": "timeout", "code": ERR_AI_TIMEOUT, "error": "TimeoutException"}
            except httpx.HTTPError as exc:
                last_err = type(exc).__name__
                if i + 1 < attempts:
                    time.sleep(0.05 * (i + 1))
                    continue
                return {
                    "ai": "down",
                    "code": ERR_AI_UNAVAILABLE,
                    "error": last_err,
                }
        return {"ai": "down", "code": ERR_AI_UNAVAILABLE, "error": last_err or "unknown"}

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        retry: bool = False,
    ) -> dict[str, Any]:
        """通用 JSON POST（聊天等非幂等默认不重试）。

        本课主验收是 health；此方法展示「POST 不盲目重试」纪律。
        """
        if retry:
            raise ValueError("非幂等 POST 禁止 retry=True（避免重复扣费/重复下单）")
        try:
            with self._client() as client:
                r = client.post(path, json=payload)
            if r.status_code >= 500:
                return {
                    "ok": False,
                    "code": ERR_AI_UNAVAILABLE,
                    "error": f"http_{r.status_code}",
                }
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "code": ERR_BAD_REQUEST,
                    "error": f"http_{r.status_code}",
                    "detail": _safe_body(r),
                }
            return {"ok": True, "code": "OK", "detail": _safe_body(r)}
        except httpx.TimeoutException:
            return {"ok": False, "code": ERR_AI_TIMEOUT, "error": "TimeoutException"}
        except httpx.HTTPError as exc:
            return {
                "ok": False,
                "code": ERR_AI_UNAVAILABLE,
                "error": type(exc).__name__,
            }


def check_ai_health(base_url: str | None = None) -> dict[str, Any]:
    """模块级快捷函数：探活下游 ai-service。"""
    return AiServiceClient(base_url).get_health()


def _safe_body(r: httpx.Response) -> Any:
    """尽量 JSON，失败则截断文本（绝不附带本地堆栈）。"""
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        text = (r.text or "")[:300]
        return {"raw": text}


def two_directions() -> list[dict[str, str]]:
    """两个调用方向小抄（口述用）。"""
    return [
        {
            "direction": "BFF → ai-service",
            "example": "聊天、检索、本课 /health",
            "watch": "超时要短于网关总超时",
        },
        {
            "direction": "ai-service → 业务 API",
            "example": "查订单 Tool、库存 API",
            "watch": "鉴权、幂等、熔断（Tool 课已接触）",
        },
    ]
