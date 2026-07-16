# app/auth.py
"""课次 10.04 · BFF 鉴权：用户凭证止于网关，再盖内部头给 ai-service。

教学环境用「演示 Bearer 表」代替真 JWT 验签，心智相同：
  Authorization: Bearer <token> → 解析出 user_id / tenant_id
生产请换成 PyJWT / JWKS，原则不变。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from app.config import (
    ALLOWED_MODELS_BY_TENANT,
    DEMO_BEARER_USERS,
    INTERNAL_TOKEN,
)


@dataclass(frozen=True)
class Principal:
    """已通过 BFF 鉴权的主体。"""

    user_id: str
    tenant_id: str
    token: str


def parse_bearer(authorization: str | None) -> str:
    """从 Authorization 抽出 Bearer token；格式不对则 401。"""
    if not authorization or not authorization.strip():
        raise HTTPException(status_code=401, detail="missing authorization")
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="invalid authorization")
    return parts[1].strip()


def verify_user_token(authorization: str | None) -> Principal:
    """验用户凭证（演示表）；失败 401。

    参数:
        authorization: 原始 Authorization 头
    返回:
        Principal（含租户，以后以它为准，不信查询参）
    """
    raw = parse_bearer(authorization)
    profile = DEMO_BEARER_USERS.get(raw)
    if profile is None:
        raise HTTPException(status_code=401, detail="invalid token")
    return Principal(
        user_id=str(profile["user_id"]),
        tenant_id=str(profile["tenant_id"]),
        token=raw,
    )


def authenticate_request(request: Request) -> Principal:
    """从入站 Request 取 Authorization 并验签。"""
    return verify_user_token(request.headers.get("authorization"))


def assert_model_allowed(tenant_id: str, model_id: str) -> str:
    """租户模型白名单；不在列表则 403。"""
    mid = (model_id or "default").strip() or "default"
    allowed = ALLOWED_MODELS_BY_TENANT.get(tenant_id) or set()
    if mid not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"model not allowed: {mid}",
        )
    return mid


def build_downstream_headers(
    principal: Principal,
    *,
    model_id: str = "default",
    request_id: str | None = None,
    ignore_query_tenant: str | None = None,
) -> dict[str, str]:
    """盖下游标准头。ignore_query_tenant 仅用于演示「伪造查询参被忽略」。

    注意：租户永远来自 principal，不来自查询参数。
    """
    mid = assert_model_allowed(principal.tenant_id, model_id)
    rid = (request_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
    # 故意不使用 ignore_query_tenant，证明伪造无效
    _ = ignore_query_tenant
    return {
        "Accept": "text/event-stream",
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": principal.tenant_id,
        "X-User-Id": principal.user_id,
        "X-Model-Id": mid,
        "X-Request-Id": rid,
    }


def auth_cheat_sheet() -> list[dict[str, Any]]:
    """演示账号小抄（写进笔记）。"""
    rows: list[dict[str, Any]] = []
    for tok, profile in DEMO_BEARER_USERS.items():
        rows.append(
            {
                "authorization": f"Bearer {tok}",
                "user_id": profile["user_id"],
                "tenant_id": profile["tenant_id"],
                "models": sorted(ALLOWED_MODELS_BY_TENANT.get(profile["tenant_id"], set())),
            }
        )
    return rows
