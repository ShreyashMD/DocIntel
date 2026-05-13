from __future__ import annotations
import secrets
import time

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

ACCESS_TTL  = 60 * 60        # 1 hour
REFRESH_TTL = 7 * 24 * 60 * 60  # 7 days
ALGORITHM   = "HS256"


# ─── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ─── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, org_id: str | None, role: str, secret: str) -> str:
    payload = {
        "sub":  user_id,
        "org":  org_id,
        "role": role,
        "type": "access",
        "exp":  int(time.time()) + ACCESS_TTL,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, secret: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
        "exp":  int(time.time()) + REFRESH_TTL,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=[ALGORITHM])


# ─── API-key encryption (Fernet) ───────────────────────────────────────────────
# SECRET_KEY is a 32-byte URL-safe base64 string (generate with secrets.token_urlsafe(32)).
# We derive a Fernet key from it with SHA-256 so any string works as the seed.

import base64
import hashlib


def _fernet(secret: str) -> Fernet:
    key = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_api_key(api_key: str, secret: str) -> str:
    return _fernet(secret).encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted: str, secret: str) -> str:
    try:
        return _fernet(secret).decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise ValueError("Could not decrypt API key — wrong SECRET_KEY?")


# ─── Invite tokens ─────────────────────────────────────────────────────────────

def generate_invite_token() -> str:
    return secrets.token_urlsafe(40)
