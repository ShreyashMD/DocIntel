from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from docintel.server import auth as _auth
from docintel.server import db as _db
from docintel.server.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    org_name:  str
    org_slug:  str
    full_name: str
    email:     str
    password:  str

    @field_validator("org_slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]{2,40}$", v):
            raise ValueError("Slug must be 2-40 lowercase letters, digits, or hyphens.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    email:    str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class InviteRequest(BaseModel):
    email: str
    role:  str = "user"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("org_admin", "manager", "user", "viewer"):
            raise ValueError("Invalid role.")
        return v


class AcceptInviteRequest(BaseModel):
    token:     str
    full_name: str
    password:  str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          dict


class UserResponse(BaseModel):
    id:         str
    email:      str
    full_name:  str
    org_id:     str | None
    role:       str
    active:     bool
    created_at: str


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _secret(request: Request) -> str:
    return request.app.state.secret_key


def _user_to_dict(u: dict) -> dict:
    return {
        "id":         str(u["id"]),
        "email":      u["email"],
        "full_name":  u["full_name"],
        "org_id":     str(u["org_id"]) if u.get("org_id") else None,
        "role":       u["role"],
        "active":     u["active"],
        "created_at": str(u.get("created_at", "")),
    }


def _make_tokens(user: dict, secret: str) -> TokenResponse:
    access = _auth.create_access_token(
        str(user["id"]),
        str(user["org_id"]) if user.get("org_id") else None,
        user["role"],
        secret,
    )
    refresh = _auth.create_refresh_token(str(user["id"]), secret)
    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_to_dict(user))


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request):
    """Create a new organisation and its first admin user."""
    with _db.get_conn() as conn:
        if _db.get_org_by_slug(conn, body.org_slug):
            raise HTTPException(400, "Organisation slug already taken.")
        if _db.get_user_by_email(conn, body.email):
            raise HTTPException(400, "Email already registered.")

        org  = _db.create_org(conn, body.org_name, body.org_slug)
        user = _db.create_user(
            conn,
            email=body.email,
            password_hash=_auth.hash_password(body.password),
            full_name=body.full_name,
            org_id=str(org["id"]),
            role="org_admin",
        )
    return _make_tokens(user, _secret(request))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    with _db.get_conn() as conn:
        user = _db.get_user_by_email(conn, body.email)
        if not user or not user["active"]:
            raise HTTPException(401, "Invalid credentials.")
        if not _auth.verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials.")
        _db.touch_last_login(conn, str(user["id"]))
    return _make_tokens(user, _secret(request))


@router.post("/refresh")
def refresh(body: RefreshRequest, request: Request):
    try:
        claims = _auth.decode_token(body.refresh_token, _secret(request))
    except Exception:
        raise HTTPException(401, "Invalid or expired refresh token.")
    if claims.get("type") != "refresh":
        raise HTTPException(401, "Wrong token type.")
    with _db.get_conn() as conn:
        user = _db.get_user(conn, claims["sub"])
    if not user or not user["active"]:
        raise HTTPException(401, "User not found or inactive.")
    access = _auth.create_access_token(
        str(user["id"]),
        str(user["org_id"]) if user.get("org_id") else None,
        user["role"],
        _secret(request),
    )
    return {"access_token": access, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(request: Request, current: CurrentUser = Depends(get_current_user)):
    with _db.get_conn() as conn:
        user = _db.get_user(conn, current.user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    return _user_to_dict(user)


@router.post("/invite", status_code=201)
def invite(body: InviteRequest, request: Request,
           current: CurrentUser = Depends(get_current_user)):
    """Org admin sends an invitation link to a new member."""
    if current.role not in ("org_admin", "superadmin"):
        raise HTTPException(403, "Only org admins can send invitations.")
    if current.org_id is None:
        raise HTTPException(400, "Super admin must specify an org via /superadmin/orgs/{id}/invite.")

    token      = _auth.generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    with _db.get_conn() as conn:
        if _db.get_user_by_email(conn, body.email):
            raise HTTPException(400, "Email already has an account.")
        _db.create_invitation(
            conn,
            email=body.email,
            org_id=current.org_id,
            role=body.role,
            token=token,
            invited_by=current.user_id,
            expires_at=expires_at,
        )

    return {"invite_token": token}


@router.post("/accept-invite", response_model=TokenResponse, status_code=201)
def accept_invite(body: AcceptInviteRequest, request: Request):
    with _db.get_conn() as conn:
        inv = _db.get_invitation_by_token(conn, body.token)
        if not inv:
            raise HTTPException(400, "Invalid invitation token.")
        if inv["accepted_at"] is not None:
            raise HTTPException(400, "Invitation already used.")
        now = datetime.now(timezone.utc)
        expires = inv["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(400, "Invitation has expired.")
        if _db.get_user_by_email(conn, inv["email"]):
            raise HTTPException(400, "Email already registered.")

        user = _db.create_user(
            conn,
            email=inv["email"],
            password_hash=_auth.hash_password(body.password),
            full_name=body.full_name,
            org_id=str(inv["org_id"]),
            role=inv["role"],
        )
        _db.accept_invitation(conn, body.token)

    return _make_tokens(user, _secret(request))
