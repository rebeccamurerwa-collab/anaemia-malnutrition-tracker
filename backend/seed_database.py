import json
import os
os.environ["GROQ_API_KEY"] = "placeholder"

from database import init_db, upsert_program

init_db()

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
    print(f"✓ {p.get('name')}")

print(f"\nDone! {count} programs seeded.")