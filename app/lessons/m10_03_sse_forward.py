# app/lessons/m10_03_sse_forward.py
"""课次 10.03 · BFF SSE 转发：边读边写 vs 整包缓冲；断连取消说明。"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.clients.ai_stream import (
    buffer_all_then_yield,
    iter_upstream_sse,
    parse_sse_events,
)
from app.config import INTERNAL_TOKEN

AI_SERVICE_ROOT = Path(__file__).resolve().parents[3] / "ai-service"

# 10.04 起下游要内部头；本课只验流式，用固定演示上下文
_DEMO_DOWNSTREAM_HEADERS = {
    "Accept": "text/event-stream",
    "X-Internal-Token": INTERNAL_TOKEN,
    "X-Tenant-Id": "demo",
    "X-User-Id": "demo-user",
    "X-Model-Id": "default",
    "X-Request-Id": "req-m10-03-fwd",
}


def _pick_free_port() -> int:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _start_ai_service_ephemeral() -> tuple[subprocess.Popen[Any], str]:
    """子进程拉起真实 ai-service（含 /v1/chat/stream），避免污染本进程的 app 包。"""
    import os

    port = _pick_free_port()
    base = f"http://127.0.0.1:{port}"
    python = sys.executable
    env = os.environ.copy()
    env["INTERNAL_TOKEN"] = INTERNAL_TOKEN
    proc = subprocess.Popen(
        [
            python,
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
    # 等 /health
    last_err = ""
    for _ in range(80):
        if proc.poll() is not None:
            err = (proc.stderr.read() or b"").decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"ai-service 子进程退出: {err or proc.returncode}")
        try:
            r = httpx.get(f"{base}/health", timeout=0.4)
            if r.status_code == 200:
                return proc, base
        except Exception as exc:  # noqa: BLE001
            last_err = type(exc).__name__
            time.sleep(0.05)
    proc.kill()
    raise RuntimeError(f"ai-service 启动超时 last={last_err}")


def _stop_proc(proc: subprocess.Popen[Any]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


async def _collect_stream(agen) -> tuple[str, list[float]]:
    """收集字节流，记录每次收到数据的相对时间（证明是否增量）。"""
    chunks: list[bytes] = []
    stamps: list[float] = []
    t0 = time.perf_counter()
    async for chunk in agen:
        chunks.append(chunk)
        stamps.append(time.perf_counter() - t0)
    return b"".join(chunks).decode("utf-8", errors="replace"), stamps


def demo_forward_vs_buffer(message: str = "退货要几天") -> dict[str, Any]:
    """对比：边读边写 vs 整包缓冲。"""
    proc, base = _start_ai_service_ephemeral()
    try:

        async def run() -> dict[str, Any]:
            streamed_raw, stream_stamps = await _collect_stream(
                iter_upstream_sse(
                    message,
                    base_url=base,
                    downstream_headers=_DEMO_DOWNSTREAM_HEADERS,
                )
            )
            buffered_raw, buffer_stamps = await _collect_stream(
                buffer_all_then_yield(
                    message,
                    base_url=base,
                    downstream_headers=_DEMO_DOWNSTREAM_HEADERS,
                )
            )
            return {
                "streamed_raw": streamed_raw,
                "stream_stamps": stream_stamps,
                "buffered_raw": buffered_raw,
                "buffer_stamps": buffer_stamps,
            }

        out = asyncio.run(run())
        s_events = parse_sse_events(out["streamed_raw"])
        b_events = parse_sse_events(out["buffered_raw"])
        return {
            "base_url": base,
            "stream_event_count": len(s_events),
            "buffer_event_count": len(b_events),
            "stream_chunk_arrivals": len(out["stream_stamps"]),
            "buffer_chunk_arrivals": len(out["buffer_stamps"]),
            "stream_has_done": any(e.get("type") == "done" for e in s_events),
            "same_final_text": (
                "".join(e.get("text", "") for e in s_events if e.get("type") == "token")
                == "".join(
                    e.get("text", "") for e in b_events if e.get("type") == "token"
                )
            ),
            "stream_is_incremental": len(out["stream_stamps"]) > 1,
            "buffer_is_one_shot": len(out["buffer_stamps"]) == 1,
            "joined": "".join(
                e.get("text", "") for e in s_events if e.get("type") == "token"
            ),
        }
    finally:
        _stop_proc(proc)


def disconnect_policy() -> dict[str, str]:
    """断连策略（验收笔记必写）。"""
    return {
        "ai_service": "iter_chat_tokens 检查 request.is_disconnected → 停止 yield",
        "bff": "iter_upstream_sse 检查上游 disconnect → break → 关闭 httpx stream",
        "goal": "客户端断开后取消下游，避免模型空跑烧钱",
        "status": "已实现（mock 间隔可观察；真模型需把 cancel 传到 Provider）",
    }


def demo_suite() -> dict[str, Any]:
    forward = demo_forward_vs_buffer()
    return {
        "forward": forward,
        "disconnect": disconnect_policy(),
        "ok": (
            forward["stream_has_done"]
            and forward["stream_is_incremental"]
            and forward["buffer_is_one_shot"]
            and forward["stream_event_count"] >= 3
            and "收到" in forward["joined"]
        ),
    }
