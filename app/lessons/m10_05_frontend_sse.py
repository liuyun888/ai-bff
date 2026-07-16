# app/lessons/m10_05_frontend_sse.py
"""课次 10.05 · 前端消费 SSE：静态页、半包解析、模拟 fetch 拉流与中止。"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.clients.ai_stream import parse_sse_events
from app.config import INTERNAL_TOKEN
from app.main import app
from app.sse_parse import parse_sse_with_half_packets

AI_SERVICE_ROOT = Path(__file__).resolve().parents[3] / "ai-service"
STATIC_CHAT = Path(__file__).resolve().parents[2] / "static" / "chat"
DOCS_SSE = Path(__file__).resolve().parents[2] / "docs" / "sse.md"


def _pick_free_port() -> int:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _start_proc(cwd: Path, port: int, extra_env: dict[str, str] | None = None) -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env["INTERNAL_TOKEN"] = INTERNAL_TOKEN
    if extra_env:
        env.update(extra_env)
    return subprocess.Popen(
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
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )


def _wait_health(base: str, proc: subprocess.Popen[Any]) -> None:
    last = ""
    for _ in range(80):
        if proc.poll() is not None:
            err = (proc.stderr.read() or b"").decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"进程退出: {err or proc.returncode}")
        try:
            if httpx.get(f"{base}/health", timeout=0.4).status_code == 200:
                return
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
            time.sleep(0.05)
    proc.kill()
    raise RuntimeError(f"health 超时 last={last}")


def _stop(proc: subprocess.Popen[Any]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def demo_static_and_docs() -> dict[str, Any]:
    """静态页可访问；对接文档与 JS 关键能力存在。"""
    client = TestClient(app)
    page = client.get("/chat")
    js = client.get("/static/chat/app.js")
    css = client.get("/static/chat/style.css")
    js_text = js.text if js.status_code == 200 else ""
    doc_text = DOCS_SSE.read_text(encoding="utf-8") if DOCS_SSE.is_file() else ""
    return {
        "chat_status": page.status_code,
        "js_status": js.status_code,
        "css_status": css.status_code,
        "js_has_fetch": "fetch(" in js_text and "/api/chat/stream" in js_text,
        "js_has_abort": "AbortController" in js_text,
        "js_has_buffer": "\\n\\n" in js_text or "\n\n" in js_text or 'split("\\n\\n")' in js_text or 'split("\n\n")' in js_text,
        "docs_ok": "text/event-stream" in doc_text and "Authorization" in doc_text,
        "files_on_disk": (STATIC_CHAT / "index.html").is_file() and (STATIC_CHAT / "app.js").is_file(),
    }


def demo_half_packet_parse() -> dict[str, Any]:
    """故意劈开 data 行，证明 buffer 能拼回完整事件。"""
    # 完整两事件被切成怪异碎片
    chunks = [
        'data: {"type":"tok',
        'en","text":"你"}\n\ndata: {"type":"token","text":"好"}\n',
        '\ndata: {"type":"done","tenant_id":"tenant-a","request_id":"r1"}\n\n',
    ]
    events = parse_sse_with_half_packets(chunks)
    types = [e.get("type") for e in events]
    texts = [e.get("text", "") for e in events if e.get("type") == "token"]
    return {
        "types": types,
        "joined": "".join(texts),
        "has_done": "done" in types,
        "ok": "".join(texts) == "你好" and types[-1] == "done",
    }


def demo_frontend_like_stream() -> dict[str, Any]:
    """子进程双端：模拟浏览器带 Authorization 拉流；再演示中途断开。"""
    ai_port = _pick_free_port()
    bff_port = _pick_free_port()
    ai_base = f"http://127.0.0.1:{ai_port}"
    bff_base = f"http://127.0.0.1:{bff_port}"
    ai_root = AI_SERVICE_ROOT
    bff_root = Path(__file__).resolve().parents[2]

    proc_ai = _start_proc(ai_root, ai_port)
    proc_bff = None
    try:
        _wait_health(ai_base, proc_ai)
        proc_bff = _start_proc(
            bff_root,
            bff_port,
            extra_env={"AI_SERVICE_BASE_URL": ai_base, "BFF_PORT": str(bff_port)},
        )
        _wait_health(bff_base, proc_bff)

        # 完整拉流（前端同款头）
        headers = {
            "Authorization": "Bearer tok-alice",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        with httpx.Client(timeout=30.0) as client:
            with client.stream(
                "POST",
                f"{bff_base}/api/chat/stream",
                headers=headers,
                json={"message": "退货", "modelId": "default"},
            ) as resp:
                stream_status = resp.status_code
                raw = "".join(resp.iter_text())
                resolved = resp.headers.get("x-resolved-tenant")

        events = parse_sse_events(raw)
        tokens = [e.get("text", "") for e in events if e.get("type") == "token"]
        done = next((e for e in events if e.get("type") == "done"), {})

        # 中途 abort：读几块就 close（等价 AbortController）
        aborted_early = False
        with httpx.Client(timeout=30.0) as client:
            with client.stream(
                "POST",
                f"{bff_base}/api/chat/stream",
                headers=headers,
                json={"message": "很长的一段话用来观察中止", "modelId": "default"},
            ) as resp:
                n = 0
                for _ in resp.iter_bytes():
                    n += 1
                    if n >= 2:
                        aborted_early = True
                        break

        chat_html = httpx.get(f"{bff_base}/chat", timeout=5.0)

        return {
            "bff_base": bff_base,
            "stream_status": stream_status,
            "resolved_tenant": resolved,
            "joined": "".join(tokens),
            "done": done,
            "aborted_early": aborted_early,
            "chat_page": chat_html.status_code,
        }
    finally:
        if proc_bff is not None:
            _stop(proc_bff)
        _stop(proc_ai)


def demo_suite() -> dict[str, Any]:
    static = demo_static_and_docs()
    half = demo_half_packet_parse()
    e2e = demo_frontend_like_stream()
    ok = (
        static["chat_status"] == 200
        and static["js_status"] == 200
        and static["js_has_fetch"]
        and static["js_has_abort"]
        and static["js_has_buffer"]
        and static["docs_ok"]
        and half["ok"]
        and e2e["stream_status"] == 200
        and e2e["resolved_tenant"] == "tenant-a"
        and "收到" in e2e["joined"]
        and e2e["done"].get("tenant_id") == "tenant-a"
        and e2e["aborted_early"]
        and e2e["chat_page"] == 200
    )
    return {"static": static, "half": half, "e2e": e2e, "ok": ok}
