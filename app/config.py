# app/config.py
"""课次 10.01～10.04 · BFF 可调配置。

改 AI_SERVICE_BASE_URL → 指向另一套 ai-service；
改超时/重试 → 影响下游探活手感（越小越容易 timeout）；
改 AI_STREAM_READ_TIMEOUT → 流式「多久没新字节」就断（不是整段对话总时长）；
改 INTERNAL_TOKEN → 必须与 ai-service 一致，否则下游全 401。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

# 可调：下游 AI 引擎根 URL（不要带尾斜杠）
# 注意：本专栏 ai-service 默认端口常为 8001（见 APP_PORT）
AI_SERVICE_BASE_URL = os.getenv(
    "AI_SERVICE_BASE_URL", "http://127.0.0.1:8001"
).rstrip("/")

# 可调：BFF 端口；与 ai-service 错开
BFF_PORT = int(os.getenv("BFF_PORT", "8088"))

APP_NAME = os.getenv("BFF_APP_NAME", "ai-bff")

# ---- 10.02 HTTP 客户端 ----
# 可调：连接超时（秒）
AI_CONNECT_TIMEOUT = float(os.getenv("AI_CONNECT_TIMEOUT", "2.0"))
# 可调：读超时（秒）
AI_READ_TIMEOUT = float(os.getenv("AI_READ_TIMEOUT", "3.0"))
# 可调：health 最大尝试次数（含首次）；仅幂等 GET
AI_HEALTH_MAX_RETRIES = int(os.getenv("AI_HEALTH_MAX_RETRIES", "2"))

# ---- 10.03 SSE ----
# 可调：流式读空闲超时（秒）；总对话可很长，但「多久没新字节」要封顶
AI_STREAM_READ_TIMEOUT = float(os.getenv("AI_STREAM_READ_TIMEOUT", "120.0"))

# ---- 10.04 鉴权透传 ----
# 可调：与 ai-service 共享的内部密钥（仅服务端）
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "dev-internal-token")

# 演示 Bearer → 用户/租户（生产换成 JWT 验签）
# 格式：token:user_id:tenant_id，多条用逗号分隔
_DEMO_RAW = os.getenv(
    "DEMO_BEARER_USERS",
    "tok-alice:u-alice:tenant-a,tok-bob:u-bob:tenant-b",
)


def _parse_demo_users(raw: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split(":")
        if len(bits) != 3:
            continue
        tok, uid, tid = bits[0].strip(), bits[1].strip(), bits[2].strip()
        if tok and uid and tid:
            out[tok] = {"user_id": uid, "tenant_id": tid}
    return out


DEMO_BEARER_USERS = _parse_demo_users(_DEMO_RAW)

# 租户 → 允许的 modelId（逗号分隔列表写在环境变量里可选；此处给教学默认）
ALLOWED_MODELS_BY_TENANT: dict[str, set[str]] = {
    "tenant-a": {"default", "fast"},
    "tenant-b": {"default"},
}
