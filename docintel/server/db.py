from __future__ import annotations
import pathlib
import uuid
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

psycopg2.extras.register_uuid()

_pool: ThreadedConnectionPool | None = None


def init_pool(db_url: str, min_conn: int = 2, max_conn: int = 10) -> None:
    global _pool
    _pool = ThreadedConnectionPool(min_conn, max_conn, dsn=db_url)
    _run_migrations(db_url)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def get_conn():
    if _pool is None:
        raise RuntimeError("DB pool not initialized.")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def _run_migrations(db_url: str) -> None:
    migrations_dir = pathlib.Path(__file__).parent.parent / "storage" / "migrations"
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


# ─── Organizations ─────────────────────────────────────────────────────────────

def create_org(conn, name: str, slug: str) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "INSERT INTO organizations (name, slug) VALUES (%s, %s) RETURNING *",
        (name, slug),
    )
    return dict(cur.fetchone())


def get_org(conn, org_id: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_org_by_slug(conn, slug: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM organizations WHERE slug = %s", (slug,))
    row = cur.fetchone()
    return dict(row) if row else None


def list_orgs(conn) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM organizations ORDER BY created_at DESC")
    return [dict(r) for r in cur.fetchall()]


def update_org(conn, org_id: str, **fields) -> dict | None:
    if not fields:
        return get_org(conn, org_id)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [org_id]
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"UPDATE organizations SET {set_clause} WHERE id = %s RETURNING *",
        values,
    )
    row = cur.fetchone()
    return dict(row) if row else None


def delete_org(conn, org_id: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM organizations WHERE id = %s", (org_id,))


# ─── Users ─────────────────────────────────────────────────────────────────────

def create_user(conn, email: str, password_hash: str, full_name: str,
                org_id: str | None, role: str) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO users (email, password_hash, full_name, org_id, role)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (email, password_hash, full_name, org_id, role),
    )
    return dict(cur.fetchone())


def get_user_by_email(conn, email: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_user(conn, user_id: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def list_users_by_org(conn, org_id: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM users WHERE org_id = %s ORDER BY created_at",
        (org_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def list_all_users(conn) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    return [dict(r) for r in cur.fetchall()]


def update_user(conn, user_id: str, **fields) -> dict | None:
    if not fields:
        return get_user(conn, user_id)
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id]
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *",
        values,
    )
    row = cur.fetchone()
    return dict(row) if row else None


def touch_last_login(conn, user_id: str) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_login = now() WHERE id = %s", (user_id,))


# ─── Invitations ───────────────────────────────────────────────────────────────

def create_invitation(conn, email: str, org_id: str, role: str,
                      token: str, invited_by: str, expires_at) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO invitations (email, org_id, role, token, invited_by, expires_at)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (email, org_id, role, token, invited_by, expires_at),
    )
    return dict(cur.fetchone())


def get_invitation_by_token(conn, token: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM invitations WHERE token = %s", (token,))
    row = cur.fetchone()
    return dict(row) if row else None


def accept_invitation(conn, token: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "UPDATE invitations SET accepted_at = now() WHERE token = %s",
        (token,),
    )


def list_invitations_by_org(conn, org_id: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM invitations WHERE org_id = %s ORDER BY created_at DESC",
        (org_id,),
    )
    return [dict(r) for r in cur.fetchall()]


# ─── Document Library ──────────────────────────────────────────────────────────

def get_doc_by_id(conn, doc_id: str, org_id: str) -> dict | None:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM document_library WHERE id = %s AND org_id = %s",
        (doc_id, org_id),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def upsert_doc_record(conn, org_id: str, collection_id: str, uploaded_by: str,
                      filename: str, file_path: str, file_size: int,
                      sha256: str, status: str = "pending") -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO document_library
               (org_id, collection_id, uploaded_by, filename, file_path, file_size, sha256, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT DO NOTHING
           RETURNING *""",
        (org_id, collection_id, uploaded_by, filename, file_path, file_size, sha256, status),
    )
    row = cur.fetchone()
    if row:
        return dict(row)
    cur.execute("SELECT * FROM document_library WHERE org_id=%s AND file_path=%s",
                (org_id, file_path))
    return dict(cur.fetchone())


def update_doc_status(conn, doc_id: str, status: str,
                      chunk_count: int = 0, error_message: str | None = None) -> None:
    cur = conn.cursor()
    cur.execute(
        """UPDATE document_library
           SET status=%s, chunk_count=%s, error_message=%s, updated_at=now()
           WHERE id=%s""",
        (status, chunk_count, error_message, doc_id),
    )


def list_docs_by_org(conn, org_id: str, collection_id: str | None = None) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if collection_id:
        cur.execute(
            "SELECT * FROM document_library WHERE org_id=%s AND collection_id=%s ORDER BY created_at DESC",
            (org_id, collection_id),
        )
    else:
        cur.execute(
            "SELECT * FROM document_library WHERE org_id=%s ORDER BY created_at DESC",
            (org_id,),
        )
    return [dict(r) for r in cur.fetchall()]


def delete_doc_record(conn, doc_id: str, org_id: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM document_library WHERE id=%s AND org_id=%s",
        (doc_id, org_id),
    )


# ─── Query History ─────────────────────────────────────────────────────────────

def save_query(conn, user_id: str, org_id: str, collection_id: str,
               question: str, answer: str, sources: Any,
               model: str, duration_ms: int) -> dict:
    import json
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """INSERT INTO query_history
               (user_id, org_id, collection_id, question, answer, sources, model, duration_ms)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
        (user_id, org_id, collection_id, question, answer,
         json.dumps(sources), model, duration_ms),
    )
    return dict(cur.fetchone())


def list_query_history(conn, org_id: str, user_id: str | None = None,
                       limit: int = 50) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if user_id:
        cur.execute(
            """SELECT * FROM query_history
               WHERE org_id=%s AND user_id=%s
               ORDER BY created_at DESC LIMIT %s""",
            (org_id, user_id, limit),
        )
    else:
        cur.execute(
            "SELECT * FROM query_history WHERE org_id=%s ORDER BY created_at DESC LIMIT %s",
            (org_id, limit),
        )
    return [dict(r) for r in cur.fetchall()]


# ─── Platform Stats ────────────────────────────────────────────────────────────

def platform_stats(conn) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM organizations WHERE active=true")
    orgs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE active=true")
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM document_library WHERE status='ready'")
    docs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM query_history")
    queries = cur.fetchone()[0]
    return {"orgs": orgs, "users": users, "docs": docs, "queries": queries}


def org_stats(conn, org_id: str) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE org_id=%s AND active=true", (org_id,))
    users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), COALESCE(SUM(chunk_count),0) FROM document_library WHERE org_id=%s AND status='ready'", (org_id,))
    row = cur.fetchone()
    docs, chunks = row[0], row[1]
    cur.execute("SELECT COUNT(*) FROM query_history WHERE org_id=%s", (org_id,))
    queries = cur.fetchone()[0]
    return {"users": users, "docs": docs, "chunks": int(chunks), "queries": queries}
