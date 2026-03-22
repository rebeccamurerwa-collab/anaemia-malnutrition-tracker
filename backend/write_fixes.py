import os
base = r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\backend"

# ── gemini_processor.py (tighter prompt) ─────────────────────────────────────
processor = '''import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

EXTRACTION_PROMPT = """
You are an expert policy analyst specialising in nutrition and public health programs in India.
Always respond in English, translating any Hindi or other language content to English.

Given the press release below, extract ONLY programs that DIRECTLY address anaemia OR malnutrition.

STRICT INCLUSION RULES - a program MUST do at least one of these to be included:
- Provide iron/folic acid (IFA) supplementation
- Provide food, meals, or nutritional supplements directly to beneficiaries
- Address stunting, wasting, or underweight in children
- Address anaemia through direct interventions
- Provide therapeutic feeding (RUTF, F75, F100)
- Provide take-home rations or supplementary nutrition
- Address micronutrient deficiencies through direct supplementation or fortification

STRICT EXCLUSION RULES - do NOT include programs that only:
- Provide general healthcare, insurance, or hospital services (e.g. Ayushman Bharat, NRHM)
- Focus on immunisation or vaccination (e.g. Mission Indradhanush)
- Address tuberculosis, malaria, or other diseases without a nutrition component
- Provide cash transfers WITHOUT a direct nutrition intervention
- Focus on agriculture, oilseeds, or general food production without direct beneficiary nutrition
- Mention nutrition only in passing or as a secondary benefit

DEDUPLICATION RULES:
- If the same program appears multiple times, include it only ONCE
- Use the most complete and official version of the program name
- "POSHAN Abhiyaan", "Poshan Abhiyan", "POSHAN Mission" are the same program - pick the most official name
- If unsure whether two mentions are the same program, include only the more detailed one

QUALITY RULES - every included program MUST have:
- A specific program name (not just "nutrition program" or "health scheme")
- At least one specific key intervention from the list below
- At least one target beneficiary group

Return a JSON array. Each element must have these fields (use null if not found):
- "program_name": string - official name
- "ministry": string - as provided
- "date_announced": string - ONLY the 4-digit launch year e.g. "2018". Look for "launched in", "started in", "introduced in", "since", "established in". Return null if not clearly stated.
- "target_beneficiaries": string e.g. "children under 5, pregnant women"
- "budget_amount": string with units e.g. "1500 crore" or null
- "status": string - one of: active, proposed, discontinued, under review
- "scope": string - one of: central, state
- "state_name": string - state name if state-specific, else null
- "category": string - one of: anaemia, malnutrition, both
- "key_interventions": array of strings - ONLY from this list:
    ["IFA supplementation", "deworming", "cash transfers", "mid-day meals",
     "take-home rations", "food fortification", "behaviour change communication",
     "POSHAN Tracker", "anganwadi services", "therapeutic feeding", "RUTF",
     "growth monitoring", "micronutrient supplementation", "dietary counselling",
     "supplementary nutrition", "food security", "nutrition rehabilitation",
     "kitchen gardens", "haemoglobin testing", "vitamin A supplementation"]
- "summary": string - 2-3 sentence plain-language summary in English
- "source_url": string - as provided

If no programs meet ALL the inclusion and quality rules, return an empty array [].
Return valid JSON only, no markdown fences, no extra text.

---
MINISTRY: {ministry}
SOURCE URL: {source_url}
TITLE: {title}
BODY:
{body}
---
Return JSON array:
"""

def extract_program_info(title, body, ministry, source_url):
    prompt = EXTRACTION_PROMPT.format(
        ministry=ministry,
        source_url=source_url,
        title=title,
        body=body[:5000],
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\\s*", "", raw)
        raw = re.sub(r"\\s*```$", "", raw)
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError as e:
        print(f"[groq] JSON parse error: {e}")
        return []
    except Exception as e:
        print(f"[groq] API error: {e}")
        return []
'''

# ── app.py cleanup endpoint ───────────────────────────────────────────────────
# We also need a cleanup endpoint to remove bad programs already in the DB
cleanup_route = '''
@app.route("/api/cleanup", methods=["POST"])
def cleanup():
    secret = request.headers.get("X-Scrape-Secret", "")
    if secret != os.environ.get("SCRAPE_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    from database import _conn
    # Remove programs that are clearly not nutrition/anaemia focused
    bad_programs = [
    "Mission Indradhanush",
    "Ayushman Bharat",
    "National Rural Health Mission",
    "PM-ARKVY",
    "National Tuberculosis Elimination Programme, Anaemia Mukt Bharat, and Vaccination Programme",
    "Niyota Bhoj Program",
    "Integrated Cereals Development Programme",
    "Integrated Scheme on Oilseeds, Pulses, Oilpalm and Maize",
    "National Food Security Mission",
]
    removed = 0
    # Remove near-duplicates - keep best version
    duplicates_to_remove = [
        "Poshan Abhiyan",
        "POSHAN Mission",
        "Nutrition Mission",
        "Niyota Bhoj Program",
    ]
    try:
        with _conn() as c:
            if hasattr(c, "cursor"):
                cur = c.cursor()
                for name in bad_programs + duplicates_to_remove:
                    cur.execute("DELETE FROM programs WHERE program_name = %s", (name,))
                    removed += cur.rowcount
                c.commit()
                cur.close()
            else:
                for name in bad_programs + duplicates_to_remove:
                    c.execute("DELETE FROM programs WHERE program_name = ?", (name,))
                    removed += c.execute("SELECT changes()").fetchone()[0]
                c.commit()
        return jsonify({"removed": removed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

with open(os.path.join(base, "gemini_processor.py"), "w", encoding="utf-8") as f:
    f.write(processor.strip())
print("gemini_processor.py written!")

# Read existing app.py and add cleanup route before health route
app_path = os.path.join(base, "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    app_content = f.read()

if "/api/cleanup" not in app_content:
    app_content = app_content.replace(
        '@app.route("/api/health"',
        cleanup_route + '\n\n@app.route("/api/health"'
    )
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app_content)
    print("app.py updated with cleanup endpoint!")
else:
    print("app.py already has cleanup endpoint, skipping.")