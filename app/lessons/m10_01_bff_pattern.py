# app/lessons/m10_01_bff_pattern.py
"""课次 10.01 · BFF 模式：骨架检查 + 三层边界验收。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import AI_SERVICE_BASE_URL, BFF_PORT
from app.layers import (
    LAYERS,
    anti_patterns,
    assert_boundary_safe,
    boundary_ascii,
    boundary_mermaid,
    mcp_vs_bff,
    why_separate,
)

ROOT = Path(__file__).resolve().parents[2]

# 本课要求的骨架文件
EXPECTED_PATHS = [
    "README.md",
    "requirements.txt",
    ".env.example",
    "app/config.py",
    "app/layers.py",
    "app/main.py",
    "scripts/10_01_bff_pattern_demo.py",
]


def check_skeleton() -> dict[str, Any]:
    """检查 ai-bff 目录骨架是否齐全。"""
    rows = []
    for rel in EXPECTED_PATHS:
        p = ROOT / rel
        rows.append({"path": rel, "exists": p.is_file()})
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    return {
        "root": str(ROOT),
        "rows": rows,
        "ok": all(r["exists"] for r in rows),
        "readme_has_duty": "职责" in readme or "鉴权" in readme,
        "readme_has_not_duty": "不职责" in readme or "Embedding" in readme or "Milvus" in readme,
    }


def demo_suite() -> dict[str, Any]:
    """本课一键套件。"""
    mermaid = boundary_mermaid()
    ascii_diagram = boundary_ascii()
    return {
        "layers": LAYERS,
        "why": why_separate(),
        "anti": anti_patterns(),
        "mcp_vs_bff": mcp_vs_bff(),
        "mermaid": mermaid,
        "ascii": ascii_diagram,
        "boundary_check": assert_boundary_safe(ascii_diagram + "\n" + mermaid),
        "config": {
            "AI_SERVICE_BASE_URL": AI_SERVICE_BASE_URL,
            "BFF_PORT": BFF_PORT,
        },
        "skeleton": check_skeleton(),
    }
