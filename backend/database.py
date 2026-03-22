"""
Database helpers — uses PostgreSQL (Supabase) when DATABASE_URL is set,
falls back to SQLite for local development.
"""

import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

# ── PostgreSQL (Render/Supabase) ──────────────────────────────────
if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def _conn():
        return psycopg2.connect(DATABASE_URL)

    def init_db():
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS programs (
                    id                SERIAL PRIMARY KEY,
                    program_name      TEXT NOT NULL,
                    ministry          TEXT,
                    date_announced    TEXT,
                    target_beneficiaries TEXT,
                    budget_amount     TEXT,
                    status            TEXT DEFAULT 'unknown',
                    scope             TEXT DEFAULT 'central',
                    state_name        TEXT,
                    key_interventions TEXT,
                    summary           TEXT,
                    source_url        TEXT,
                    created_at        TEXT,
                    updated_at        TEXT,
                    UNIQUE(program_name, ministry)
                )
                """)
            c.commit()

    def upsert_program(data: dict):
        if not data or not data.get("program_name"):
            return
        now = datetime.utcnow().isoformat()
        ki = json.dumps(data.get("key_interventions") or [])
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute("""
                INSERT INTO programs
                    (program_name, ministry, date_announced, target_beneficiaries,
                     budget_amount, status, scope, state_name, key_interventions,
                     summary, source_url, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(program_name, ministry) DO UPDATE SET
                    date_announced       = EXCLUDED.date_announced,
                    target_beneficiaries = EXCLUDED.target_beneficiaries,
                    budget_amount        = EXCLUDED.budget_amount,
                    status               = EXCLUDED.status,
                    scope                = EXCLUDED.scope,
                    state_name           = EXCLUDED.state_name,
                    key_interventions    = EXCLUDED.key_interventions,
                    summary              = EXCLUDED.summary,
                    source_url           = EXCLUDED.source_url,
                    updated_at           = EXCLUDED.updated_at
                """, (
                    data.get("program_name"),
                    data.get("ministry"),
                    data.get("date_announced"),
                    data.get("target_beneficiaries"),
                    data.get("budget_amount"),
                    data.get("status", "unknown"),
                    data.get("scope", "central"),
                    data.get("state_name"),
                    ki,
                    data.get("summary"),
                    data.get("source_url"),
                    now, now,
                ))
            c.commit()

    def get_all_programs(ministry=None, scope=None, status=None,
                         state_name=None, year=None) -> list[dict]:
        filters, params = [], []
        if ministry:
            filters.append("ministry ILIKE %s")
            params.append(f"%{ministry}%")
        if scope:
            filters.append("scope = %s")
            params.append(scope)
        if status:
            filters.append("status = %s")
            params.append(status)
        if state_name:
            filters.append("state_name ILIKE %s")
            params.append(f"%{state_name}%")
        if year:
            filters.append("date_announced LIKE %s")
            params.append(f"%{year}%")
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        with _conn() as c:
            with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"SELECT * FROM programs {where} ORDER BY updated_at DESC",
                    params
                )
                rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["key_interventions"] = json.loads(d["key_interventions"] or "[]")
            except Exception:
                d["key_interventions"] = []
            result.append(d)
        return result

    def get_program_by_id(pid: int) -> dict | None:
        with _conn() as c:
            with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM programs WHERE id=%s", (pid,))
                row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["key_interventions"] = json.loads(d["key_interventions"] or "[]")
        except Exception:
            d["key_interventions"] = []
        return d

# ── SQLite (local development) ────────────────────────────────────
else:
    import sqlite3

    DB_PATH = os.environ.get("DB_PATH", "programs.db")

    def _conn():
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

    def init_db():
        with _conn() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                program_name      TEXT NOT NULL,
                ministry          TEXT,
                date_announced    TEXT,
                target_beneficiaries TEXT,
                budget_amount     TEXT,
                status            TEXT DEFAULT 'unknown',
                scope             TEXT DEFAULT 'central',
                state_name        TEXT,
                key_interventions TEXT,
                summary           TEXT,
                source_url        TEXT,
                created_at        TEXT,
                updated_at        TEXT,
                UNIQUE(program_name, ministry)
            )
            """)
            c.commit()

    def upsert_program(data: dict):
        if not data or not data.get("program_name"):
            return
        now = datetime.utcnow().isoformat()
        ki = json.dumps(data.get("key_interventions") or [])
        with _conn() as c:
            c.execute("""
            INSERT INTO programs
                (program_name, ministry, date_announced, target_beneficiaries,
                 budget_amount, status, scope, state_name, key_interventions,
                 summary, source_url, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(program_name, ministry) DO UPDATE SET
                date_announced       = excluded.date_announced,
                target_beneficiaries = excluded.target_beneficiaries,
                budget_amount        = excluded.budget_amount,
                status               = excluded.status,
                scope                = excluded.scope,
                state_name           = excluded.state_name,
                key_interventions    = excluded.key_interventions,
                summary              = excluded.summary,
                source_url           = excluded.source_url,
                updated_at           = excluded.updated_at
            """, (
                data.get("program_name"),
                data.get("ministry"),
                data.get("date_announced"),
                data.get("target_beneficiaries"),
                data.get("budget_amount"),
                data.get("status", "unknown"),
                data.get("scope", "central"),
                data.get("state_name"),
                ki,
                data.get("summary"),
                data.get("source_url"),
                now, now,
            ))
            c.commit()

    def get_all_programs(ministry=None, scope=None, status=None,
                         state_name=None, year=None) -> list[dict]:
        filters, params = [], []
        if ministry:
            filters.append("ministry LIKE ?")
            params.append(f"%{ministry}%")
        if scope:
            filters.append("scope = ?")
            params.append(scope)
        if status:
            filters.append("status = ?")
            params.append(status)
        if state_name:
            filters.append("state_name LIKE ?")
            params.append(f"%{state_name}%")
        if year:
            filters.append("date_announced LIKE ?")
            params.append(f"%{year}%")
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        with _conn() as c:
            rows = c.execute(
                f"SELECT * FROM programs {where} ORDER BY updated_at DESC",
                params
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["key_interventions"] = json.loads(d["key_interventions"] or "[]")
            except Exception:
                d["key_interventions"] = []
            result.append(d)
        return result

    def get_program_by_id(pid: int) -> dict | None:
        with _conn() as c:
            row = c.execute(
                "SELECT * FROM programs WHERE id=?", (pid,)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["key_interventions"] = json.loads(d["key_interventions"] or "[]")
        except Exception:
            d["key_interventions"] = []
        return d