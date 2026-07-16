# scripts/10_02_http_client_demo.py
"""10.02 服务间 HTTP 调用演示。

【本课要感受的三件事】
1. baseUrl + 显式 connect/read 超时可配置
2. 下游通 → ai=up；不通 → ai=down/timeout + 稳定错误码（无堆栈）
3. 幂等 health 可重试；非幂等 POST 禁止盲目重试

工作目录：必须在 ai-bff/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m10_02_http_client import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "http_client_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("BFF → ai-service：超时显式；错误有码；POST 不盲目重试")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.02 服务间 HTTP 调用 · 实跑记录\n", ""]

    # ---- STEP 1 · 两个方向 ----
    print("\n" + "=" * 52, "STEP 1 · 两个调用方向")
    for d in suite["directions"]:
        print(f"  [{d['direction']}] {d['example']} | 注意: {d['watch']}")
    assert len(suite["directions"]) == 2
    print("ASSERT: 网关→AI / AI→业务 能区分 → PASS")
    note.append("## STEP 1 · 方向\n")
    for d in suite["directions"]:
        note.append(f"- **{d['direction']}**：{d['example']}（{d['watch']}）")
    note.append("")

    # ---- STEP 2 · 配置 ----
    print("\n" + "=" * 52, "STEP 2 · 可配置 baseUrl / 超时")
    cfg = suite["config"]
    for k, v in cfg.items():
        print(f"  {k}={v}")
    assert str(cfg["AI_SERVICE_BASE_URL"]).startswith("http")
    assert float(cfg["AI_CONNECT_TIMEOUT"]) > 0
    assert float(cfg["AI_READ_TIMEOUT"]) > 0
    print("ASSERT: 非硬编码无限超时 → PASS")
    note.append("## STEP 2 · 配置\n")
    note.append(f"- `{cfg}`\n")

    # ---- STEP 3 · 通 ----
    print("\n" + "=" * 52, "STEP 3 · 下游通（临时 mock ai-service）")
    up = suite["up"]
    print(f"  base: {up['base_url']}")
    print(f"  result: {up['result']}")
    assert up["result"]["ai"] == "up"
    assert up["result"].get("detail", {}).get("status") == "ok"
    print("ASSERT: ai=up → PASS")
    note.append("## STEP 3 · up\n")
    note.append(f"- `{up}`\n")

    # ---- STEP 4 · 不通 ----
    print("\n" + "=" * 52, "STEP 4 · 下游不通")
    down = suite["down"]
    print(f"  result: {down['result']}")
    assert down["result"]["ai"] == "down"
    assert down["result"]["code"] == "AI_UNAVAILABLE"
    assert "Traceback" not in str(down["result"])
    print("ASSERT: ai=down + AI_UNAVAILABLE，无堆栈 → PASS")
    note.append("## STEP 4 · down\n")
    note.append(f"- `{down['result']}`\n")

    # ---- STEP 5 · 超时 ----
    print("\n" + "=" * 52, "STEP 5 · 读超时")
    timed = suite["timeout"]["result"]
    print(f"  result: {timed}")
    assert timed["ai"] == "timeout"
    assert timed["code"] == "AI_TIMEOUT"
    print("ASSERT: ai=timeout + AI_TIMEOUT → PASS")
    note.append("## STEP 5 · timeout\n")
    note.append(f"- `{timed}`\n")

    # ---- STEP 6 · POST 不重试 + 真实配置探测 ----
    print("\n" + "=" * 52, "STEP 6 · POST 禁重试 + 配置下游实探")
    post = suite["post_no_retry"]
    live = suite["live_configured"]
    print(f"  post retry blocked: {post}")
    print(f"  live ({cfg['AI_SERVICE_BASE_URL']}): {live}")
    assert post["raised"] is True
    print("ASSERT: POST retry=True 被拒绝 → PASS")
    if live.get("ai") == "up":
        print("  HINT: 真实 ai-service 在线，联调通过")
    else:
        print("  HINT: 真实 ai-service 未起属正常；先跑 mock 验收即可")
        print("        联调: cd ../ai-service && uvicorn app.main:app --port 8001")
    note.append("## STEP 6 · 纪律与实探\n")
    note.append(f"- post: `{post}`")
    note.append(f"- live: `{live}`\n")

    assert suite.get("ok") is True
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: http_client 验收通过")


if __name__ == "__main__":
    main()
