# scripts/10_05_frontend_sse_demo.py
"""10.05 前端消费 SSE 演示。

【本课要感受的四件事】
1. 同源静态页 /chat + app.js（fetch / Abort / buffer）
2. 半包也能拼出完整 SSE 事件
3. 带 Authorization 拉流，UI 同款路径可见 done 上下文
4. 中途断开（模拟停止生成）

工作目录：必须在 ai-bff/ 下；会临时子进程拉起 ../ai-service 与本 BFF。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m10_05_frontend_sse import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "frontend_sse_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("前端 fetch 读流；对接说明 docs/sse.md")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.05 前端消费 SSE · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 1 · 静态页与对接文档")
    s = suite["static"]
    print(f"  /chat={s['chat_status']} js={s['js_status']} docs={s['docs_ok']}")
    print(f"  fetch={s['js_has_fetch']} abort={s['js_has_abort']} buffer={s['js_has_buffer']}")
    assert s["chat_status"] == 200 and s["js_has_fetch"] and s["js_has_abort"]
    assert s["docs_ok"]
    print("ASSERT: 页面 + JS 能力 + docs/sse.md → PASS")
    note.append("## STEP 1\n")
    note.append(f"- chat={s['chat_status']} fetch/abort/buffer OK；docs OK\n")

    print("\n" + "=" * 52, "STEP 2 · 半包缓冲解析")
    h = suite["half"]
    print(f"  types={h['types']} joined={h['joined']!r}")
    assert h["ok"]
    print("ASSERT: 半包拼出「你好」+ done → PASS")
    note.append("## STEP 2\n")
    note.append(f"- joined=`{h['joined']}` types=`{h['types']}`\n")

    print("\n" + "=" * 52, "STEP 3 · 模拟前端带 Token 拉流")
    e = suite["e2e"]
    print(f"  bff={e['bff_base']} status={e['stream_status']} tenant={e['resolved_tenant']}")
    print(f"  joined={e['joined']!r}")
    print(f"  done={e['done']}")
    assert e["stream_status"] == 200 and "收到" in e["joined"]
    assert e["done"].get("tenant_id") == "tenant-a"
    print("ASSERT: 流式 + 上下文下沉可见 → PASS")
    note.append("## STEP 3\n")
    note.append(f"- joined=`{e['joined']}` done=`{e['done']}`\n")

    print("\n" + "=" * 52, "STEP 4 · 中途停止")
    print(f"  aborted_early={e['aborted_early']}")
    assert e["aborted_early"]
    print("ASSERT: 读若干 chunk 后断开 → PASS")
    note.append("## STEP 4\n")
    note.append("- 模拟 Abort：提前 close stream\n")

    print("\n" + "=" * 52, "STEP 5 · 浏览器打开")
    print("  # 起 ai-service:8091 + ai-bff:8088 后访问：")
    print("  #   cd ../ai-service && .venv/bin/uvicorn app.main:app --port 8091")
    print("  #   cd ../ai-bff && .venv/bin/uvicorn app.main:app --port 8088")
    print("  open http://127.0.0.1:8088/chat")
    note.append("## STEP 5\n")
    note.append("- ai-service:`8091` + BFF:`8088` → 浏览器：`http://127.0.0.1:8088/chat`\n")

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: frontend_sse 验收通过")


if __name__ == "__main__":
    main()
