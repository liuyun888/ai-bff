# scripts/11_05_chat_page_wire_demo.py
"""课次 11.05 · BFF /assistant 接到统一助手（需本机双端已起）。

注意：10.05 的 /chat 仍是 mock，本课验收走 /assistant，勿互相覆盖。

前置：
  ai-service :8091
  ai-bff     :8088 且 AI_SERVICE_BASE_URL=http://127.0.0.1:8091

用法（在 ai-bff/ 下）：
  python scripts/11_05_chat_page_wire_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from app.clients.ai_stream import parse_sse_events

BFF = os.getenv("BFF_BASE", "http://127.0.0.1:8088").rstrip("/")


def main() -> None:
    print("=" * 52, "11.05 assistant page wire")
    # 10.05 页未被动：仍打 mock 路径
    chat_js = httpx.get(f"{BFF}/static/chat/app.js", timeout=5.0).text
    assert "/api/chat/stream" in chat_js
    assert "/api/assistant/stream" not in chat_js
    print("ASSERT: /chat 仍指向 mock /api/chat/stream → PASS")

    page = httpx.get(f"{BFF}/assistant", timeout=10.0)
    assert page.status_code == 200
    asst_js = httpx.get(f"{BFF}/static/assistant/app.js", timeout=5.0).text
    assert "/api/assistant/stream" in asst_js
    print("ASSERT: /assistant + app.js 指向 assistant/stream → PASS")

    headers = {
        "Authorization": "Bearer tok-alice",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            "POST",
            f"{BFF}/api/assistant/stream",
            headers=headers,
            json={"message": "防水款还有吗？退货多久？", "modelId": "default"},
        ) as resp:
            assert resp.status_code == 200, resp.text
            assert resp.headers.get("x-resolved-tenant") == "tenant-a"
            raw = "".join(resp.iter_text())

    events = parse_sse_events(raw)
    tokens = [e.get("text", "") for e in events if e.get("type") == "token"]
    done = next((e for e in events if e.get("type") == "done"), {})
    joined = "".join(tokens)
    assert joined and "mock 流" not in joined
    assert done.get("mode") == "assistant"
    assert done.get("tenant_id") == "tenant-a"
    print("ASSERT: BFF 助手流 mode=assistant 非 mock → PASS")
    print("  reply[:100]=", joined[:100])
    print("  done.mode=", done.get("mode"), "elapsed_ms=", done.get("elapsed_ms"))
    print("ALL PASS · 打开", f"{BFF}/assistant", "聊真助手；", f"{BFF}/chat", "仍是 10.05 mock")


if __name__ == "__main__":
    main()
