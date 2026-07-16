# app/lessons/m10_02_http_client.py
"""课次 10.02 · 服务间 HTTP：通 / 不通 / 超时 / 非幂等不重试。"""

from __future__ import annotations

import json
import threading
from typing import Any
from wsgiref.simple_server import make_server

import httpx

from app.clients.ai_http import (
    ERR_AI_TIMEOUT,
    ERR_AI_UNAVAILABLE,
    AiServiceClient,
    two_directions,
)
from app.config import (
    AI_CONNECT_TIMEOUT,
    AI_HEALTH_MAX_RETRIES,
    AI_READ_TIMEOUT,
    AI_SERVICE_BASE_URL,
)


def _json_app(status: int, body: dict[str, Any]):
    """极简 WSGI：固定返回一段 JSON（给临时 mock ai-service 用）。"""

    payload = json.dumps(body).encode("utf-8")

    def app(environ, start_response):  # noqa: ANN001
        path = environ.get("PATH_INFO") or ""
        if path != "/health":
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"not found"]
        start_response(
            f"{status} OK" if status == 200 else f"{status} Error",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

    return app


class _EphemeralServer:
    """后台线程起一个仅 /health 的小服务，演示 ai=up。"""

    def __init__(self, body: dict[str, Any] | None = None) -> None:
        self.body = body or {"status": "ok", "app": "mock-ai-service"}
        self.httpd = make_server("127.0.0.1", 0, _json_app(200, self.body))
        self.port = int(self.httpd.server_address[1])
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> str:
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        self.httpd.shutdown()


def demo_up() -> dict[str, Any]:
    """下游活着 → ai=up。"""
    srv = _EphemeralServer()
    base = srv.start()
    try:
        out = AiServiceClient(base).get_health()
        return {"base_url": base, "result": out}
    finally:
        srv.stop()


def demo_down() -> dict[str, Any]:
    """下游连接失败 → ai=down + AI_UNAVAILABLE（稳定码，无堆栈）。"""

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        raise httpx.ConnectError("connection refused (demo)")

    transport = httpx.MockTransport(handler)
    out = AiServiceClient("http://ai.down.local", transport=transport).get_health()
    return {"base_url": "http://ai.down.local", "result": out}


def demo_timeout() -> dict[str, Any]:
    """读超时：下游故意睡太久，客户端短 read timeout → AI_TIMEOUT。"""

    def slow_app(environ, start_response):  # noqa: ANN001, ARG001
        import time

        time.sleep(1.2)
        body = b'{"status":"ok"}'
        start_response(
            "200 OK",
            [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
        )
        return [body]

    httpd = make_server("127.0.0.1", 0, slow_app)
    port = int(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"

    class _Short(AiServiceClient):
        """演示用：把读超时压到 0.25s，必定撞上慢接口。"""

        def _client(self) -> httpx.Client:
            return httpx.Client(
                timeout=httpx.Timeout(connect=0.5, read=0.25, write=0.25, pool=0.5),
                base_url=self.base_url,
            )

    try:
        out = _Short(base).get_health()
        return {"base_url": base, "result": out}
    finally:
        httpd.shutdown()


def demo_post_no_retry() -> dict[str, Any]:
    """非幂等 POST 禁止 retry=True。"""
    client = AiServiceClient("http://127.0.0.1:1")
    try:
        client.post_json("/v1/chat", {"q": "hi"}, retry=True)
        raised = False
        err = ""
    except ValueError as exc:
        raised = True
        err = str(exc)
    return {"raised": raised, "error": err}


def demo_suite() -> dict[str, Any]:
    """本课一键套件。"""
    up = demo_up()
    down = demo_down()
    timed = demo_timeout()
    post = demo_post_no_retry()
    # 可选：若配置的真实 ai-service 在线，额外记一笔
    live = AiServiceClient(AI_SERVICE_BASE_URL).get_health()
    return {
        "directions": two_directions(),
        "config": {
            "AI_SERVICE_BASE_URL": AI_SERVICE_BASE_URL,
            "AI_CONNECT_TIMEOUT": AI_CONNECT_TIMEOUT,
            "AI_READ_TIMEOUT": AI_READ_TIMEOUT,
            "AI_HEALTH_MAX_RETRIES": AI_HEALTH_MAX_RETRIES,
        },
        "up": up,
        "down": down,
        "timeout": timed,
        "post_no_retry": post,
        "live_configured": live,
        "ok": (
            up["result"].get("ai") == "up"
            and down["result"].get("ai") == "down"
            and down["result"].get("code") == ERR_AI_UNAVAILABLE
            and timed["result"].get("ai") == "timeout"
            and timed["result"].get("code") == ERR_AI_TIMEOUT
            and post["raised"] is True
            and "Traceback" not in str(down["result"])
        ),
    }
