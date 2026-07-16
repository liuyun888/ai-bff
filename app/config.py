# app/config.py
"""课次 10.01～10.02 · BFF 可调配置。

改 AI_SERVICE_BASE_URL → 指向另一套 ai-service；
改超时/重试 → 影响下游探活手感（越小越容易 timeout）。
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
