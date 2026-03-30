import os
base = r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\backend"

app_code = '''import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, get_all_programs, get_program_by_id, upsert_program
from scraper import run_full_scrape
from gmail_reader import fetch_gmail_alerts
from scheduler import start_scheduler

app = Flask(__name__)
CORS(app)

try:
    init_db()
except Exception as e:
    print(f"[startup] DB init warning: {e}")

start_scheduler()


@app.route("/api/programs", methods=["GET"])
def programs():
    ministry = request.args.get("ministry")
    state    = request.args.get("state")
    year     = request.args.get("year")
    category = request.args.get("category")
    source   = request.args.get("source")
    search   = request.args.get("search")
    rows = get_all_programs(ministry=ministry, state_name=state,
                            year=year, category=category,
                            source=source, search=search)
    return jsonify(rows)


@app.route("/api/programs/new", methods=["GET"])
def new_programs():
    from datetime import datetime, timedelta
    rows = get_all_programs()
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    new = [r for r in rows if r.get("created_at", "") >= week_ago]
    return jsonify(new)


@app.route("/api/programs/<int:pid>", methods=["GET"])
def program_detail(pid):
    row = get_program_by_id(pid)
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row)


@app.route("/api/trigger-scrape", methods=["POST"])
def trigger_scrape():
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
                "category": p.get("category", "unknown"),
                "key_interventions": [p.get("key_features")] if p.get("key_features") else [],
                "summary": p.get("purpose"),
                "source_url": "Seed data",
            }
            upsert_program(record)
            count += 1
        return jsonify({"seeded": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/deduplicate", methods=["POST"])
def deduplicate():
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    from database import _conn
    canonical = {
        "Poshan Abhiyan": "POSHAN Abhiyaan",
        "POSHAN Mission": "POSHAN Abhiyaan",
        "National Nutrition Mission": "POSHAN Abhiyaan",
        "Poshan Abhiyaan": "POSHAN Abhiyaan",
        "Mid-Day Meal Scheme": "PM POSHAN",
        "Mid-day Meal": "PM POSHAN",
        "Midday Meal Scheme": "PM POSHAN",
        "Anemia Mukt Bharat": "Anaemia Mukt Bharat",
        "Anaemia Mukt Bharat Abhiyan": "Anaemia Mukt Bharat",
        "Integrated Child Development Services Scheme (ICDS)": "Integrated Child Development Services (ICDS)",
        "ICDS Scheme": "Integrated Child Development Services (ICDS)",
        "POSHAN Abhiyan": "POSHAN Abhiyaan",
    }
    merged = 0
    deleted = 0
    try:
        conn = _conn()
        cur = conn.cursor()
        for wrong_name, correct_name in canonical.items():
            cur.execute("SELECT id FROM programs WHERE program_name = %s LIMIT 1", (correct_name,))
            correct = cur.fetchone()
            cur.execute("SELECT id FROM programs WHERE program_name = %s", (wrong_name,))
            wrong = cur.fetchall()
            if wrong:
                if correct:
                    cur.execute("DELETE FROM programs WHERE program_name = %s", (wrong_name,))
                    deleted += cur.rowcount
                else:
                    cur.execute("UPDATE programs SET program_name = %s WHERE program_name = %s",
                                (correct_name, wrong_name))
                    merged += cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"merged": merged, "deleted": deleted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cleanup", methods=["POST"])
def cleanup():
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    from database import _conn
    bad_names = [
        "Mission Indradhanush",
        "Ayushman Bharat",
        "National Rural Health Mission",
        "PM-ARKVY",
        "National Tuberculosis Elimination Programme, Anaemia Mukt Bharat, and Vaccination Programme",
        "Niyota Bhoj Program",
        "Integrated Cereals Development Programme",
        "Integrated Scheme on Oilseeds, Pulses, Oilpalm and Maize",
        "National Food Security Mission",
        "Nutrition Mission",
        "Poshan Abhiyan",
    ]
    removed = 0
    try:
        conn = _conn()
        cur = conn.cursor()
        for name in bad_names:
            cur.execute("DELETE FROM programs WHERE program_name = %s", (name,))
            removed += cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"removed": removed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
'''

with open(os.path.join(base, "app.py"), "w", encoding="utf-8") as f:
    f.write(app_code.strip())
print("app.py written!")