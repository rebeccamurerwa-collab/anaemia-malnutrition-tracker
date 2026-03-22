import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, get_all_programs, get_program_by_id, upsert_program
from scraper import run_full_scrape
from gmail_reader import fetch_gmail_alerts
from scheduler import start_scheduler

app = Flask(__name__)
CORS(app)

# ── DB init ──────────────────────────────────────────────────────────────────
init_db()

# ── Scheduler (weekly) ───────────────────────────────────────────────────────
start_scheduler()


# ── API Routes ────────────────────────────────────────────────────────────────

@app.route("/api/programs", methods=["GET"])
def programs():
    ministry   = request.args.get("ministry")
    state      = request.args.get("state")
    year       = request.args.get("year")
    category   = request.args.get("category")
    rows = get_all_programs(ministry=ministry, state_name=state, year=year, category=category)
    return jsonify(rows)


@app.route("/api/programs/<int:pid>", methods=["GET"])
def program_detail(pid):
    row = get_program_by_id(pid)
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row)


@app.route("/api/trigger-scrape", methods=["POST"])
def trigger_scrape():
    """Manual one-off scrape (protected by a secret header)."""
    import threading
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    thread = threading.Thread(target=run_full_scrape)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "Scrape started in background"})


@app.route("/api/trigger-gmail", methods=["POST"])
def trigger_gmail():
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    count = fetch_gmail_alerts()
    return jsonify({"processed": count})


@app.route("/api/stats", methods=["GET"])
def stats():
    rows = get_all_programs()
    ministries = {}
    scopes     = {"central": 0, "state": 0}
    statuses   = {"active": 0, "proposed": 0, "unknown": 0}
    for r in rows:
        m = r.get("ministry", "Unknown")
        ministries[m] = ministries.get(m, 0) + 1
        s = r.get("scope", "central")
        scopes[s] = scopes.get(s, 0) + 1
        st = r.get("status", "unknown")
        statuses[st] = statuses.get(st, 0) + 1
    return jsonify({
        "total": len(rows),
        "by_ministry": ministries,
        "by_scope": scopes,
        "by_status": statuses,
    })


@app.route("/api/seed", methods=["POST"])
def seed():
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    import json
    from database import upsert_program
    try:
        with open("programs.json", "r", encoding="utf-8") as f:
            programs = json.load(f)
        count = 0
        for p in programs:
            record = {
                "program_name": p.get("name"),
                "ministry": p.get("implementing_body"),
                "date_announced": str(p.get("launch_year")) if p.get("launch_year") else None,
                "target_beneficiaries": p.get("target_group"),
                "budget_amount": None,
                "status": p.get("status", "active"),
                "scope": "state" if p.get("state") else "central",
                "state_name": p.get("state"),
                "key_interventions": [p.get("key_features")] if p.get("key_features") else [],
                "summary": p.get("purpose"),
                "source_url": "Seed data",
            }
            upsert_program(record)
            count += 1
        return jsonify({"seeded": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)