# scripts/10_01_bff_pattern_demo.py
"""10.01 BFF 模式演示。

【本课要感受的三件事】
1. 三层职责能分开说：前端 / ai-bff / ai-service
2. ai-bff 骨架 + README + 可配 AI_SERVICE_BASE_URL / BFF_PORT
3. 边界图上没有「前端直连向量库」；密钥不下发前端

工作目录：必须在 ai-bff/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m10_01_bff_pattern import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "bff_pattern_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("BFF = 前端柜台；ai-service = 引擎房；密钥不进浏览器")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = [
        "# 10.01 BFF 模式 · 实跑记录\n",
        "",
        "## 边界图（Mermaid）\n",
        "```mermaid",
        suite["mermaid"].rstrip(),
        "```",
        "",
        "## ASCII\n",
        "```",
        suite["ascii"].rstrip(),
        "```",
        "",
    ]

    # ---- STEP 1 · 骨架 ----
    print("\n" + "=" * 52, "STEP 1 · ai-bff 骨架")
    sk = suite["skeleton"]
    for row in sk["rows"]:
        print(f"  [{'OK' if row['exists'] else 'MISS'}] {row['path']}")
    assert sk["ok"], sk
    assert sk["readme_has_duty"] and sk["readme_has_not_duty"]
    print("ASSERT: 目录与 README 职责齐全 → PASS")
    note.append("## STEP 1 · 骨架\n")
    for row in sk["rows"]:
        note.append(f"- `{row['path']}` exists={row['exists']}")
    note.append("")

    # ---- STEP 2 · 三层 ----
    print("\n" + "=" * 52, "STEP 2 · 三层职责")
    names = []
    for L in suite["layers"]:
        print(f"  [{L['name']}] 该做: {L['duty']}")
        print(f"           不该: {L['not']}")
        names.append(L["name"])
    assert names == ["前端", "ai-bff", "ai-service"]
    print("ASSERT: 三层名称与职责可区分 → PASS")
    note.append("## STEP 2 · 三层\n")
    note.append("| 层 | 职责 | 不该做 |")
    note.append("|----|------|--------|")
    for L in suite["layers"]:
        note.append(f"| {L['name']} | {L['duty']} | {L['not']} |")
    note.append("")

    # ---- STEP 3 · 为何分离 ----
    print("\n" + "=" * 52, "STEP 3 · 为何分离")
    for w in suite["why"]:
        print(f"  - {w['point']}: {w['detail']}")
    assert len(suite["why"]) >= 4
    print("ASSERT: 安全/多端/演进/观测 → PASS")
    note.append("## STEP 3 · 为何分离\n")
    for w in suite["why"]:
        note.append(f"- **{w['point']}**：{w['detail']}")
    note.append("")

    # ---- STEP 4 · 边界安全 ----
    print("\n" + "=" * 52, "STEP 4 · 边界图无越界")
    print(suite["ascii"])
    bc = suite["boundary_check"]
    print(f"  check={bc}")
    assert bc["ok"] and bc["has_bff"] and bc["has_ai_service"]
    print("ASSERT: 无「前端直连向量库」→ PASS")
    note.append("## STEP 4 · 边界检查\n")
    note.append(f"- `{bc}`\n")

    # ---- STEP 5 · 配置项 ----
    print("\n" + "=" * 52, "STEP 5 · 预留配置")
    cfg = suite["config"]
    print(f"  AI_SERVICE_BASE_URL={cfg['AI_SERVICE_BASE_URL']}")
    print(f"  BFF_PORT={cfg['BFF_PORT']}")
    assert cfg["AI_SERVICE_BASE_URL"].startswith("http")
    assert isinstance(cfg["BFF_PORT"], int) and cfg["BFF_PORT"] > 0
    print("ASSERT: baseUrl 与端口可配置 → PASS")
    note.append("## STEP 5 · 配置\n")
    note.append(f"- AI_SERVICE_BASE_URL=`{cfg['AI_SERVICE_BASE_URL']}`")
    note.append(f"- BFF_PORT=`{cfg['BFF_PORT']}`\n")

    # ---- STEP 6 · 反模式 + MCP ----
    print("\n" + "=" * 52, "STEP 6 · 反模式与 MCP 对照")
    for a in suite["anti"]:
        print(f"  ✗ {a['bad']} → 错在[{a['layer_fault']}]；{a['fix']}")
    mv = suite["mcp_vs_bff"]
    print(f"  MCP: {mv['MCP']}")
    print(f"  BFF: {mv['BFF']}")
    print(f"  rule: {mv['rule']}")
    assert any("密钥" in a["bad"] or "OPENAI" in a["bad"] for a in suite["anti"])
    assert "不互相" in mv["rule"] or "调试" in mv["rule"]
    print("ASSERT: 能指出越界层；MCP≠BFF → PASS")
    note.append("## STEP 6 · 反模式\n")
    for a in suite["anti"]:
        note.append(f"- {a['bad']}（{a['layer_fault']}）→ {a['fix']}")
    note.append(f"- {mv['rule']}\n")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: bff_pattern 验收通过")
    print("HINT: 可选启动 BFF → .venv/bin/uvicorn app.main:app --port", cfg["BFF_PORT"])


if __name__ == "__main__":
    main()
