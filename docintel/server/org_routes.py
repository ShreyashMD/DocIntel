from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from docintel.server import auth as _auth
from docintel.server import db as _db
from docintel.server.deps import CurrentUser, get_current_user, require_org_admin

router = APIRouter(prefix="/admin", tags=["org-admin"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class OrgSettingsUpdate(BaseModel):
    llm_provider:       Optional[str] = None
    embedding_provider: Optional[str] = None
    ollama_url:         Optional[str] = None
    pipeline_mode:      Optional[str] = None
    # Per-provider keys — any combination can be saved independently
    openai_api_key:     Optional[str] = None
    gemini_api_key:     Optional[str] = None
    anthropic_api_key:  Optional[str] = None
    nvidia_api_key:     Optional[str] = None
    # Legacy single-key fields (kept for backward compat)
    llm_api_key:        Optional[str] = None
    embedding_api_key:  Optional[str] = None


class UserRoleUpdate(BaseModel):
    role:   Optional[str] = None
    active: Optional[bool] = None


# ─── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(request: Request,
               current: CurrentUser = Depends(require_org_admin)):
    with _db.get_conn() as conn:
        users = _db.list_users_by_org(conn, current.org_id)
        invites = _db.list_invitations_by_org(conn, current.org_id)
    return {
        "users": [_safe_user(u) for u in users],
        "pending_invites": [_safe_invite(i) for i in invites if i["accepted_at"] is None],
    }


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserRoleUpdate,
                request: Request,
                current: CurrentUser = Depends(require_org_admin)):
    fields: dict = {}
    if body.role is not None:
        if body.role not in ("org_admin", "manager", "user", "viewer"):
            raise HTTPException(400, "Invalid role.")
        fields["role"] = body.role
    if body.active is not None:
        fields["active"] = body.active

    with _db.get_conn() as conn:
        user = _db.get_user(conn, user_id)
        if not user or str(user.get("org_id")) != current.org_id:
            raise HTTPException(404, "User not found in your organisation.")
        if user_id == current.user_id:
            raise HTTPException(400, "Cannot modify your own account here.")
        updated = _db.update_user(conn, user_id, **fields)
    return _safe_user(updated)


@router.delete("/users/{user_id}", status_code=204)
def deactivate_user(user_id: str,
                    request: Request,
                    current: CurrentUser = Depends(require_org_admin)):
    with _db.get_conn() as conn:
        user = _db.get_user(conn, user_id)
        if not user or str(user.get("org_id")) != current.org_id:
            raise HTTPException(404, "User not found in your organisation.")
        _db.update_user(conn, user_id, active=False)


# ─── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings")
def get_settings(request: Request,
                 current: CurrentUser = Depends(require_org_admin)):
    with _db.get_conn() as conn:
        org = _db.get_org(conn, current.org_id)
    if not org:
        raise HTTPException(404, "Organisation not found.")
    return _safe_org(org)


@router.patch("/settings")
def update_settings(body: OrgSettingsUpdate,
                    request: Request,
                    current: CurrentUser = Depends(require_org_admin)):
    secret = request.app.state.secret_key
    fields: dict = {}

    if body.llm_provider is not None:
        if body.llm_provider not in ("gemini", "openai", "anthropic", "ollama", "nvidia"):
            raise HTTPException(400, "Invalid llm_provider.")
        fields["llm_provider"] = body.llm_provider

    if body.embedding_provider is not None:
        fields["embedding_provider"] = body.embedding_provider

    if body.ollama_url is not None:
        fields["ollama_url"] = body.ollama_url

    if body.pipeline_mode is not None:
        if body.pipeline_mode not in ("single", "writer_reviewer"):
            raise HTTPException(400, "Invalid pipeline_mode. Must be 'single' or 'writer_reviewer'.")
        fields["pipeline_mode"] = body.pipeline_mode

    # Per-provider keys
    if body.openai_api_key is not None:
        fields["openai_api_key_enc"] = _auth.encrypt_api_key(body.openai_api_key, secret)
    if body.gemini_api_key is not None:
        fields["gemini_api_key_enc"] = _auth.encrypt_api_key(body.gemini_api_key, secret)
    if body.anthropic_api_key is not None:
        fields["anthropic_api_key_enc"] = _auth.encrypt_api_key(body.anthropic_api_key, secret)
    if body.nvidia_api_key is not None:
        fields["nvidia_api_key_enc"] = _auth.encrypt_api_key(body.nvidia_api_key, secret)

    # Legacy single-key fields (backward compat)
    if body.llm_api_key is not None:
        fields["llm_api_key_enc"] = _auth.encrypt_api_key(body.llm_api_key, secret)
    if body.embedding_api_key is not None:
        fields["embedding_api_key_enc"] = _auth.encrypt_api_key(body.embedding_api_key, secret)

    with _db.get_conn() as conn:
        updated = _db.update_org(conn, current.org_id, **fields)

    registry = getattr(request.app.state, "pipeline_registry", None)
    if registry:
        registry.invalidate(current.org_id)

    return _safe_org(updated)


# ─── API key validation ────────────────────────────────────────────────────────

@router.post("/settings/validate")
def validate_api_key(request: Request,
                     current: CurrentUser = Depends(require_org_admin)):
    """Test whether the org's saved LLM API key for the active provider is functional."""
    secret = request.app.state.secret_key
    with _db.get_conn() as conn:
        org = _db.get_org(conn, current.org_id)
    if not org:
        raise HTTPException(404, "Organisation not found.")

    provider = org.get("llm_provider", "gemini")
    base_cfg  = request.app.state.config

    # Resolve the key: provider-specific column → legacy generic column → server base config
    def _get_key(enc_col: str, base_key):
        enc = org.get(enc_col) or org.get("llm_api_key_enc")
        if enc and secret:
            return _auth.decrypt_api_key(enc, secret)
        return base_key

    if provider == "gemini":
        api_key = _get_key("gemini_api_key_enc", base_cfg.gemini_api_key)
    elif provider == "openai":
        api_key = _get_key("openai_api_key_enc", base_cfg.openai_api_key)
    elif provider == "anthropic":
        api_key = _get_key("anthropic_api_key_enc", base_cfg.anthropic_api_key)
    elif provider == "nvidia":
        api_key = _get_key("nvidia_api_key_enc", base_cfg.nvidia_api_key)
    else:
        api_key = None

    if not api_key:
        return {"valid": False, "provider": provider,
                "error": "No API key configured for this organisation."}

    try:
        if provider == "gemini":
            import google.genai as genai  # type: ignore
            client = genai.Client(api_key=api_key)
            client.models.embed_content(
                model="gemini-embedding-001",
                contents="ping",
            )
        elif provider == "openai":
            import openai as _openai  # type: ignore
            client = _openai.OpenAI(api_key=api_key)
            client.embeddings.create(model="text-embedding-3-small", input="ping")
        elif provider == "anthropic":
            import anthropic as _anthropic  # type: ignore
            client = _anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        elif provider == "nvidia":
            import openai as _openai  # type: ignore
            client = _openai.OpenAI(
                api_key=api_key,
                base_url="https://integrate.api.nvidia.com/v1",
            )
            client.embeddings.create(
                model="nvidia/nv-embedqa-e5-v5",
                input=["ping"],
                encoding_format="float",
                extra_body={"input_type": "query", "truncate": "END"},
            )
        else:
            return {"valid": False, "provider": provider,
                    "error": f"Validation not supported for provider '{provider}'."}
        return {"valid": True, "provider": provider, "error": None}
    except Exception as exc:
        return {"valid": False, "provider": provider, "error": str(exc)[:300]}


# ─── Org stats ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def org_stats(request: Request,
              current: CurrentUser = Depends(require_org_admin)):
    with _db.get_conn() as conn:
        stats = _db.org_stats(conn, current.org_id)
    return stats


# ─── Collections ───────────────────────────────────────────────────────────────

@router.get("/collections")
def list_collections(request: Request,
                     current: CurrentUser = Depends(require_org_admin)):
    with _db.get_conn() as conn:
        docs = _db.list_docs_by_org(conn, current.org_id)
    collections = sorted({d["collection_id"] for d in docs})
    return {"collections": collections}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _safe_user(u: dict) -> dict:
    return {
        "id":         str(u["id"]),
        "email":      u["email"],
        "full_name":  u["full_name"],
        "role":       u["role"],
        "active":     u["active"],
        "created_at": str(u.get("created_at", "")),
        "last_login": str(u["last_login"]) if u.get("last_login") else None,
    }


def _safe_invite(i: dict) -> dict:
    return {
        "id":         str(i["id"]),
        "email":      i["email"],
        "role":       i["role"],
        "expires_at": str(i["expires_at"]),
        "created_at": str(i["created_at"]),
    }


def _safe_org(org: dict) -> dict:
    provider = org.get("llm_provider", "gemini")
    # A provider-specific key exists if its dedicated column is set,
    # OR if the legacy generic column was set while that provider was active.
    def _has(col: str, prov: str) -> bool:
        return bool(
            org.get(col) or
            (org.get("llm_api_key_enc") and provider == prov)
        )

    return {
        "id":                 str(org["id"]),
        "name":               org["name"],
        "slug":               org["slug"],
        "llm_provider":       provider,
        "embedding_provider": org.get("embedding_provider"),
        "ollama_url":         org.get("ollama_url"),
        "plan":               org.get("plan"),
        "active":             org["active"],
        # Per-provider key status
        "pipeline_mode":      org.get("pipeline_mode") or "single",
        "has_openai_key":     _has("openai_api_key_enc",    "openai"),
        "has_gemini_key":     _has("gemini_api_key_enc",    "gemini"),
        "has_anthropic_key":  _has("anthropic_api_key_enc", "anthropic"),
        "has_nvidia_key":     _has("nvidia_api_key_enc",    "nvidia"),
        # Legacy flags (kept for compat)
        "has_llm_key":        bool(org.get("llm_api_key_enc")),
        "has_embedding_key":  bool(org.get("embedding_api_key_enc")),
        "created_at":         str(org.get("created_at", "")),
    }
