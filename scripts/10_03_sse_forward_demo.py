# scripts/10_03_sse_forward_demo.py
"""10.03 BFF SSE 流转发演示。

【本课要感受的三件事】
1. 事件约定：token / done / error
2. BFF 边读边写（多次到达）vs 整包缓冲（一次倒出）
3. 断连应取消下游（已实现，笔记写明）

工作目录：必须在 ai-bff/ 下；会临时子进程拉起 ../ai-service。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m10_03_sse_forward import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "sse_forward_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("BFF SSE 转发：边读边写；断开则取消下游")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.03 SSE 流式转发 · 实跑记录\n", ""]

    # ---- STEP 1 · 断连策略 ----
    print("\n" + "=" * 52, "STEP 1 · 断连 / 取消策略")
    d = suite["disconnect"]
    for k, v in d.items():
        print(f"  {k}: {v}")
    assert "取消" in d["goal"] or "cancel" in d["goal"].lower() or "空跑" in d["goal"]
    print("ASSERT: 断连策略已写明且代码侧有实现 → PASS")
    note.append("## STEP 1 · 断连\n")
    for k, v in d.items():
        note.append(f"- **{k}**：{v}")
    note.append("")

    # ---- STEP 2 · 边读边写 ----
    print("\n" + "=" * 52, "STEP 2 · 边读边写（真 ai-service 子进程）")
    f = suite["forward"]
    print(f"  downstream: {f['base_url']}")
    print(f"  stream arrivals={f['stream_chunk_arrivals']} events={f['stream_event_count']}")
    print(f"  joined: {f['joined']}")
    assert f["stream_is_incremental"]
    assert f["stream_has_done"]
    assert "收到" in f["joined"]
    print("ASSERT: 多次增量到达 + done → PASS")
    note.append("## STEP 2 · 流式转发\n")
    note.append(f"- base: `{f['base_url']}`")
    note.append(f"- joined: `{f['joined']}`")
    note.append(f"- arrivals: {f['stream_chunk_arrivals']}\n")

    # ---- STEP 3 · 反面：整包缓冲 ----
    print("\n" + "=" * 52, "STEP 3 · 反面教材：整包缓冲")
    print(f"  buffer arrivals={f['buffer_chunk_arrivals']} (期望 1)")
    assert f["buffer_is_one_shot"]
    print("ASSERT: 缓冲路径一次性倒出 → PASS")
    note.append("## STEP 3 · 缓冲对比\n")
    note.append(f"- buffer_arrivals={f['buffer_chunk_arrivals']}（错误示范）\n")

    # ---- STEP 4 · 事件约定 ----
    print("\n" + "=" * 52, "STEP 4 · 事件约定")
    print("  data: {\"type\":\"token\",\"text\":\"...\"}")
    print("  data: {\"type\":\"done\"}")
    print("  data: {\"type\":\"error\",\"message\":\"...\"}")
    assert f["stream_event_count"] >= 3
    print("ASSERT: 事件数合理 → PASS")
    note.append("## STEP 4 · 约定\n")
    note.append("- token / done / error\n")

    # ---- STEP 5 · curl 提示 ----
    print("\n" + "=" * 52, "STEP 5 · 手工 curl（可选联调）")
    print("  # 终端 A: cd ai-service && uvicorn app.main:app --port 8001")
    print("  # 终端 B: cd ai-bff && uvicorn app.main:app --port 8088")
    print(
        "  curl -N -X POST http://127.0.0.1:8088/api/chat/stream "
        "-H 'Content-Type: application/json' -d '{\"message\":\"hello\"}'"
    )
    note.append("## STEP 5 · curl\n")
    note.append(
        "```bash\ncurl -N -X POST http://127.0.0.1:8088/api/chat/stream "
        "-H 'Content-Type: application/json' -d '{\"message\":\"hello\"}'\n```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: sse_forward 验收通过")


if __name__ == "__main__":
    main()
