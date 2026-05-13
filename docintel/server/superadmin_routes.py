from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from docintel.server import auth as _auth
from docintel.server import db as _db
from docintel.server.deps import CurrentUser, require_superadmin

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name:       str
    slug:       str
    admin_email: str
    admin_name:  str
    admin_password: str


class UpdateOrgRequest(BaseModel):
    name:   Optional[str]  = None
    plan:   Optional[str]  = None
    active: Optional[bool] = None


class OrgInviteRequest(BaseModel):
    email: str
    role:  str = "org_admin"


# ─── Orgs ──────────────────────────────────────────────────────────────────────

@router.get("/orgs")
def list_orgs(request: Request,
              _: CurrentUser = Depends(require_superadmin)):
    with _db.get_conn() as conn:
        orgs = _db.list_orgs(conn)
    return [_safe_org(o) for o in orgs]


@router.post("/orgs", status_code=201)
def create_org(body: CreateOrgRequest, request: Request,
               _: CurrentUser = Depends(require_superadmin)):
    with _db.get_conn() as conn:
        if _db.get_org_by_slug(conn, body.slug):
            raise HTTPException(400, "Slug already taken.")
        if _db.get_user_by_email(conn, body.admin_email):
            raise HTTPException(400, "Email already registered.")
        org  = _db.create_org(conn, body.name, body.slug)
        user = _db.create_user(
            conn,
            email=body.admin_email,
            password_hash=_auth.hash_password(body.admin_password),
            full_name=body.admin_name,
            org_id=str(org["id"]),
            role="org_admin",
        )
    return {"org": _safe_org(org), "admin": _safe_user(user)}


@router.patch("/orgs/{org_id}")
def update_org(org_id: str, body: UpdateOrgRequest,
               request: Request,
               _: CurrentUser = Depends(require_superadmin)):
    fields: dict = {k: v for k, v in body.model_dump().items() if v is not None}
    with _db.get_conn() as conn:
        updated = _db.update_org(conn, org_id, **fields)
    if not updated:
        raise HTTPException(404, "Organisation not found.")
    return _safe_org(updated)


@router.delete("/orgs/{org_id}", status_code=204)
def delete_org(org_id: str, request: Request,
               _: CurrentUser = Depends(require_superadmin)):
    with _db.get_conn() as conn:
        if not _db.get_org(conn, org_id):
            raise HTTPException(404, "Organisation not found.")
        _db.delete_org(conn, org_id)

    registry = getattr(request.app.state, "pipeline_registry", None)
    if registry:
        registry.invalidate(org_id)


@router.post("/orgs/{org_id}/invite", status_code=201)
def invite_to_org(org_id: str, body: OrgInviteRequest,
                  request: Request,
                  current: CurrentUser = Depends(require_superadmin)):
    token      = _auth.generate_invite_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    with _db.get_conn() as conn:
        if not _db.get_org(conn, org_id):
            raise HTTPException(404, "Organisation not found.")
        if _db.get_user_by_email(conn, body.email):
            raise HTTPException(400, "Email already registered.")
        _db.create_invitation(
            conn,
            email=body.email,
            org_id=org_id,
            role=body.role,
            token=token,
            invited_by=current.user_id,
            expires_at=expires_at,
        )

    return {"invite_token": token}


# ─── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_all_users(request: Request,
                   _: CurrentUser = Depends(require_superadmin)):
    with _db.get_conn() as conn:
        users = _db.list_all_users(conn)
    return [_safe_user(u) for u in users]


# ─── Platform Stats ────────────────────────────────────────────────────────────

@router.get("/stats")
def platform_stats(request: Request,
                   _: CurrentUser = Depends(require_superadmin)):
    from docintel.metrics import get_metrics
    with _db.get_conn() as conn:
        db_stats = _db.platform_stats(conn)
    return {**db_stats, "runtime_metrics": get_metrics()}


# ─── Super admin bootstrap ─────────────────────────────────────────────────────

@router.post("/bootstrap", status_code=201)
def bootstrap(body: dict, request: Request):
    """Create the first superadmin if none exists. Disabled after first use."""
    with _db.get_conn() as conn:
        from docintel.server.db import _pool
        cur = _pool  # just checking pool exists; use get_conn for real query
    # Re-enter with proper connection
    with _db.get_conn() as conn:
        import psycopg2.extras
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role='superadmin'")
        count = cur.fetchone()[0]
        if count > 0:
            raise HTTPException(403, "Super admin already exists.")
        email    = body.get("email")
        password = body.get("password")
        name     = body.get("full_name", "Super Admin")
        if not email or not password:
            raise HTTPException(400, "email and password required.")
        _db.create_user(conn, email=email,
                        password_hash=_auth.hash_password(password),
                        full_name=name, org_id=None, role="superadmin")
    return {"message": "Super admin created."}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _safe_org(o: dict) -> dict:
    return {
        "id":         str(o["id"]),
        "name":       o["name"],
        "slug":       o["slug"],
        "plan":       o.get("plan"),
        "active":     o["active"],
        "created_at": str(o.get("created_at", "")),
    }


def _safe_user(u: dict) -> dict:
    return {
        "id":         str(u["id"]),
        "email":      u["email"],
        "full_name":  u["full_name"],
        "org_id":     str(u["org_id"]) if u.get("org_id") else None,
        "role":       u["role"],
        "active":     u["active"],
        "created_at": str(u.get("created_at", "")),
    }
