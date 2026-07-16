# app/lessons/m10_04_auth_passthrough.py
"""课次 10.04 · BFF 鉴权透传：401 / 伪造租户 / 模型白名单 / 端到端到达。"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.auth import (
    auth_cheat_sheet,
    build_downstream_headers,
    verify_user_token,
)
from app.clients.ai_stream import parse_sse_events
from app.config import INTERNAL_TOKEN
from app.main import app

AI_SERVICE_ROOT = Path(__file__).resolve().parents[3] / "ai-service"


def _pick_free_port() -> int:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _start_ai_service() -> tuple[subprocess.Popen[Any], str]:
    """子进程拉起 ai-service，避免污染本进程 app 包。"""
    port = _pick_free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["INTERNAL_TOKEN"] = INTERNAL_TOKEN
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(AI_SERVICE_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    last_err = ""
    for _ in range(80):
        if proc.poll() is not None:
            err = (proc.stderr.read() or b"").decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"ai-service 退出: {err or proc.returncode}")
        try:
            r = httpx.get(f"{base}/health", timeout=0.4)
            if r.status_code == 200:
                return proc, base
        except Exception as exc:  # noqa: BLE001
            last_err = type(exc).__name__
            time.sleep(0.05)
    proc.kill()
    raise RuntimeError(f"ai-service 启动超时 last={last_err}")


def _stop(proc: subprocess.Popen[Any]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def demo_no_user_token() -> dict[str, Any]:
    """无 Authorization → BFF 401。"""
    client = TestClient(app)
    r = client.post("/api/chat/stream", json={"message": "hi"})
    return {"status_code": r.status_code, "body": r.json()}


def demo_forged_tenant_ignored() -> dict[str, Any]:
    """有效 Token + 伪造 tenantId 查询参 → 下游头仍为 JWT 租户。"""
    principal = verify_user_token("Bearer tok-alice")
    headers = build_downstream_headers(
        principal,
        model_id="default",
        ignore_query_tenant="tenant-b",
    )
    return {
        "principal_tenant": principal.tenant_id,
        "forged_query": "tenant-b",
        "downstream_tenant": headers["X-Tenant-Id"],
        "ignored": headers["X-Tenant-Id"] == "tenant-a",
        "has_internal": headers.get("X-Internal-Token") == INTERNAL_TOKEN,
    }


def demo_bad_model() -> dict[str, Any]:
    """tenant-b 不允许 fast → 403（不打下游）。"""
    client = TestClient(app)
    r = client.post(
        "/api/chat/stream",
        json={"message": "hi", "modelId": "fast"},
        headers={"Authorization": "Bearer tok-bob"},
    )
    return {"status_code": r.status_code, "body": r.json()}


def demo_e2e_context_arrives() -> dict[str, Any]:
    """模拟 BFF 出站：盖好的头打到真 ai-service，echo + SSE done 都带租户。"""
    proc, base = _start_ai_service()
    try:
        principal = verify_user_token("Bearer tok-alice")
        headers = build_downstream_headers(
            principal,
            model_id="fast",
            request_id="req-e2e-004",
            ignore_query_tenant="tenant-b",
        )
        echo = httpx.get(f"{base}/v1/context/echo", headers=headers, timeout=5.0)
        with httpx.Client(timeout=30.0) as client:
            with client.stream(
                "POST",
                f"{base}/v1/chat/stream",
                json={"message": "退货"},
                headers=headers,
            ) as resp:
                raw = "".join(resp.iter_text())
                status = resp.status_code
        events = parse_sse_events(raw)
        done = next((e for e in events if e.get("type") == "done"), {})
        return {
            "base_url": base,
            "stream_status": status,
            "done": done,
            "echo_status": echo.status_code,
            "echo": echo.json() if echo.status_code == 200 else {},
        }
    finally:
        _stop(proc)


def demo_suite() -> dict[str, Any]:
    no_tok = demo_no_user_token()
    forged = demo_forged_tenant_ignored()
    bad_model = demo_bad_model()
    e2e = demo_e2e_context_arrives()
    ok = (
        no_tok["status_code"] == 401
        and forged["ignored"] is True
        and forged["has_internal"] is True
        and bad_model["status_code"] == 403
        and e2e["stream_status"] == 200
        and e2e["echo_status"] == 200
        and e2e["done"].get("tenant_id") == "tenant-a"
        and e2e["done"].get("request_id") == "req-e2e-004"
        and e2e["echo"].get("tenant_id") == "tenant-a"
        and e2e["echo"].get("model_id") == "fast"
    )
    return {
        "cheat_sheet": auth_cheat_sheet(),
        "no_token": no_tok,
        "forged": forged,
        "bad_model": bad_model,
        "e2e": e2e,
        "ok": ok,
    }
