# app/clients/__init__.py
"""下游 HTTP 客户端（BFF → ai-service）。"""

from app.clients.ai_http import AiServiceClient, check_ai_health

__all__ = ["AiServiceClient", "check_ai_health"]
