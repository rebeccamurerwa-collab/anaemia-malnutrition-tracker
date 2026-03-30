import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def _conn():
        return psycopg2.connect(DATABASE_URL, sslmode="prefer")

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
                    category          TEXT DEFAULT 'unknown',
                    key_interventions TEXT,
                    summary           TEXT,
                    source_url        TEXT,
                    created_at        TEXT,
                    updated_at        TEXT,
                    UNIQUE(program_name, ministry)
                )
                """)
                cur.execute("ALTER TABLE programs ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'unknown'")
            c.commit()

    def upsert_program(data):
        if not data or not data.get("program_name"):
            return
        now = datetime.utcnow().isoformat()
        ki = json.dumps(data.get("key_interventions") or [])
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute("""
                INSERT INTO programs
                    (program_name, ministry, date_announced, target_beneficiaries,
                     budget_amount, status, scope, state_name, category,
                     key_interventions, summary, source_url, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(program_name, ministry) DO UPDATE SET
                    date_announced       = EXCLUDED.date_announced,
                    target_beneficiaries = EXCLUDED.target_beneficiaries,
                    budget_amount        = EXCLUDED.budget_amount,
                    status               = EXCLUDED.status,
                    scope                = EXCLUDED.scope,
                    state_name           = EXCLUDED.state_name,
                    category             = EXCLUDED.category,
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
                    data.get("category", "unknown"),
                    ki,
                    data.get("summary"),
                    data.get("source_url"),
                    now, now,
                ))
            c.commit()

    def get_all_programs(ministry=None, scope=None, status=None,
                         state_name=None, year=None, category=None, source=None):
        filters, params = [], []
        if ministry:
            filters.append("ministry ILIKE %s")
            params.append(f"%{ministry}%")
        if state_name:
            filters.append("state_name ILIKE %s")
            params.append(f"%{state_name}%")
        if year:
            filters.append("date_announced = %s")
            params.append(year)
        if category:
            filters.append("category ILIKE %s")
            params.append(f"%{category}%")
        if source == "PIB":
            filters.append("source_url ILIKE %s")
            params.append("%pib.gov.in%")
        elif source == "Gmail":
            filters.append("source_url = %s")
            params.append("Gmail Alert")
        elif source == "Seed":
            filters.append("source_url = %s")
            params.append("Seed data")
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

    def get_program_by_id(pid):
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
                category          TEXT DEFAULT 'unknown',
                key_interventions TEXT,
                summary           TEXT,
                source_url        TEXT,
                created_at        TEXT,
                updated_at        TEXT,
                UNIQUE(program_name, ministry)
            )
            """)
            try:
                c.execute("ALTER TABLE programs ADD COLUMN category TEXT DEFAULT 'unknown'")
            except Exception:
                pass
            c.commit()

    def upsert_program(data):
        if not data or not data.get("program_name"):
            return
        now = datetime.utcnow().isoformat()
        ki = json.dumps(data.get("key_interventions") or [])
        with _conn() as c:
            c.execute("""
            INSERT INTO programs
                (program_name, ministry, date_announced, target_beneficiaries,
                 budget_amount, status, scope, state_name, category,
                 key_interventions, summary, source_url, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(program_name, ministry) DO UPDATE SET
                date_announced       = excluded.date_announced,
                target_beneficiaries = excluded.target_beneficiaries,
                budget_amount        = excluded.budget_amount,
                status               = excluded.status,
                scope                = excluded.scope,
                state_name           = excluded.state_name,
                category             = excluded.category,
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
                data.get("category", "unknown"),
                ki,
                data.get("summary"),
                data.get("source_url"),
                now, now,
            ))
            c.commit()

    def get_all_programs(ministry=None, scope=None, status=None,
                         state_name=None, year=None, category=None, source=None):
        filters, params = [], []
        if ministry:
            filters.append("ministry LIKE ?")
            params.append(f"%{ministry}%")
        if state_name:
            filters.append("state_name LIKE ?")
            params.append(f"%{state_name}%")
        if year:
            filters.append("date_announced = ?")
            params.append(year)
        if category:
            filters.append("category LIKE ?")
            params.append(f"%{category}%")
        if source == "PIB":
            filters.append("source_url LIKE ?")
            params.append("%pib.gov.in%")
        elif source == "Gmail":
            filters.append("source_url = ?")
            params.append("Gmail Alert")
        elif source == "Seed":
            filters.append("source_url = ?")
            params.append("Seed data")
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

    def get_program_by_id(pid):
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

