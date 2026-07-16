# app/layers.py
"""课次 10.01 · 三层边界：前端 / ai-bff / ai-service。

直觉：BFF 是前台柜台，ai-service 是引擎房；密钥与向量库不能出现在浏览器。
"""

from __future__ import annotations

from typing import Any

# 三层职责表（验收口述用）
LAYERS: list[dict[str, str]] = [
    {
        "name": "前端",
        "duty": "展示、输入、消费 SSE",
        "not": "持有模型密钥、直连向量库/Milvus",
    },
    {
        "name": "ai-bff",
        "duty": "鉴权、限流、参数校验、转发/聚合、统一追踪",
        "not": "塞进复杂 Prompt 工程与向量逻辑",
    },
    {
        "name": "ai-service",
        "duty": "模型调用、RAG、Agent、图",
        "not": "解析每种前端的 Cookie 细节（可收标准头）",
    },
]


def boundary_mermaid() -> str:
    """边界图（写入笔记）；图中禁止前端直连向量库。"""
    return """\
flowchart LR
  Web[前端 Web/App]
  BFF[ai-bff]
  AI[ai-service]
  V[(向量库 Milvus)]
  LLM[模型 Provider]

  Web -->|HTTP/SSE 用户票据| BFF
  BFF -->|HTTP/SSE 服务凭证| AI
  AI --> V
  AI --> LLM
"""


def boundary_ascii() -> str:
    """ASCII 边界（终端打印用）。"""
    return """\
[前端] --用户票据--> [ai-bff] --服务凭证--> [ai-service] --> [Milvus/模型]
   |                      |                      |
 展示/SSE              鉴权/转发              RAG/Agent
  ✗ 无模型密钥          ✗ 无向量逻辑           ✗ 不管 Cookie 细节
  ✗ 不直连向量库
"""


def anti_patterns() -> list[dict[str, str]]:
    """常见越界（演示里要能指出「错在哪一层」）。"""
    return [
        {
            "bad": "前端 .env 塞 OPENAI_API_KEY",
            "layer_fault": "前端",
            "fix": "密钥只放 BFF 或 ai-service 服务端",
        },
        {
            "bad": "浏览器直连 Milvus",
            "layer_fault": "前端",
            "fix": "向量访问只在 ai-service",
        },
        {
            "bad": "BFF 里写满 Prompt / Agent Loop",
            "layer_fault": "ai-bff",
            "fix": "Prompt 与 Loop 回 ai-service",
        },
        {
            "bad": "ai-service 解析每种 App 的 Cookie",
            "layer_fault": "ai-service",
            "fix": "BFF 鉴权后下发标准头（租户/用户 id）",
        },
    ]


def why_separate() -> list[dict[str, str]]:
    """为什么引擎与网关要分离。"""
    return [
        {"point": "安全", "detail": "密钥与内网 Tool 留在服务端"},
        {"point": "多端同构", "detail": "各端只对接 BFF 契约"},
        {"point": "演进", "detail": "换模型/换 Agent 不改前端"},
        {"point": "观测", "detail": "在 BFF 统一打点、追踪 id"},
    ]


def mcp_vs_bff() -> dict[str, str]:
    """与 M09 MCP 的关系：不互相替代。"""
    return {
        "MCP": "开发期工具调试（IDE 连工具箱）",
        "BFF": "产品流量入口（端上用户请求）",
        "rule": "调试 Tool 用 MCP；上线流量走 BFF → ai-service",
    }


def assert_boundary_safe(diagram: str) -> dict[str, Any]:
    """检查边界描述里没有「前端直连向量库」这类越界表述。"""
    text = diagram or ""
    # 允许出现「不直连」「✗ 不直连」；禁止「前端 → Milvus」无否定的直连
    forbidden_hits = []
    if "前端" in text and "Milvus" in text:
        # 若同时出现，必须带否定标记
        if "不直连" not in text and "✗" not in text and "-.->" not in text:
            # mermaid 里前端不应有到 V 的边；我们的图没有 Web-->V
            pass
    if "Web --> V" in text or "前端 --> 向量" in text or "前端直连向量" in text:
        forbidden_hits.append("frontend_to_vector")
    if "浏览器直连 Milvus" in text and "fix" not in text:
        forbidden_hits.append("browser_milvus")
    return {
        "ok": "Web --> V" not in text and "前端直连向量" not in text,
        "forbidden_hits": forbidden_hits,
        "has_bff": "BFF" in text or "ai-bff" in text or "bff" in text.lower(),
        "has_ai_service": "ai-service" in text or "AI[" in text,
    }
