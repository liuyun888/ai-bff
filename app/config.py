# app/config.py
"""课次 10.01 · BFF 可调配置。

改 AI_SERVICE_BASE_URL → 指向另一套 ai-service；改 BFF_PORT → 换监听口。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 ai-bff/.env（若不存在则用默认值）
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

# 可调：下游 AI 引擎根 URL（不要带尾斜杠）
AI_SERVICE_BASE_URL = os.getenv("AI_SERVICE_BASE_URL", "http://127.0.0.1:8000").rstrip(
    "/"
)

# 可调：BFF 端口；与 ai-service（常见 8000/8001）错开
BFF_PORT = int(os.getenv("BFF_PORT", "8088"))

APP_NAME = os.getenv("BFF_APP_NAME", "ai-bff")
