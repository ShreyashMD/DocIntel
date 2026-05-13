from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docintel.server import auth as _auth

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    org_id:  str | None
    role:    str
    email:   str = ""
    full_name: str = ""


def _secret(request: Request) -> str:
    return request.app.state.secret_key


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        claims = _auth.decode_token(creds.credentials, _secret(request))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")
    return CurrentUser(
        user_id=claims["sub"],
        org_id=claims.get("org"),
        role=claims["role"],
    )


def require_org_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in ("org_admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Org admin access required.")
    return user


def require_superadmin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Super admin access required.")
    return user


def require_manager(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in ("manager", "org_admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Manager access required.")
    return user


def get_current_user_or_token_param(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token: Optional[str] = Query(None),
) -> CurrentUser:
    """Like get_current_user but also accepts ?token= for browser file opens."""
    raw = creds.credentials if creds else token
    if not raw:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        claims = _auth.decode_token(raw, _secret(request))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")
    return CurrentUser(
        user_id=claims["sub"],
        org_id=claims.get("org"),
        role=claims["role"],
    )
