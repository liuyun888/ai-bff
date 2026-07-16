# app/sse_parse.py
"""课次 10.05 · SSE 文本解析（与 static/chat/app.js 同心态）。

chunk 可能把一行劈成两半，必须先缓冲，再按 \\n\\n 拆事件。
"""

from __future__ import annotations

import json
from typing import Any, Callable


class SseBufferParser:
    """增量喂入文本，回调完整事件 dict。"""

    def __init__(self, on_event: Callable[[dict[str, Any]], None]) -> None:
        self._buf = ""
        self._on_event = on_event

    def push(self, chunk_text: str) -> None:
        """喂入一段解码后的文本（可能是半包）。"""
        self._buf += chunk_text
        parts = self._buf.split("\n\n")
        self._buf = parts.pop() if parts else ""
        for part in parts:
            line = next(
                (ln for ln in part.split("\n") if ln.startswith("data:")),
                None,
            )
            if not line:
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                self._on_event({"type": "error", "message": f"JSON 损坏: {raw}"})
                continue
            if isinstance(evt, dict):
                self._on_event(evt)

    def flush(self) -> None:
        """流结束时再尝试拆一次残留。"""
        if self._buf.strip():
            self.push("\n\n")


def parse_sse_with_half_packets(chunks: list[str]) -> list[dict[str, Any]]:
    """验收用：故意用半包列表喂解析器。"""
    out: list[dict[str, Any]] = []
    parser = SseBufferParser(out.append)
    for c in chunks:
        parser.push(c)
    parser.flush()
    return out
