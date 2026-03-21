"""
Uses Google Gemini Flash to extract structured program data
from raw PIB press-release text or Gmail alert snippets.
"""

import os
import json
import re
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

EXTRACTION_PROMPT = """
You are an expert policy analyst specialising in nutrition and public health programs in India.

Given the press release title, body text, and source ministry below, extract ALL anaemia and malnutrition-related programs or schemes mentioned.

Return a JSON array. Each element must have these fields (use null if not found):
- "program_name": string — official name / acronym
- "ministry": string — as provided
- "date_announced": string — ISO date or best guess from text (YYYY-MM-DD)
- "target_beneficiaries": string — e.g. "children under 5, pregnant women"
- "budget_amount": string — rupees or USD with units, e.g. "₹1,500 crore"
- "status": string — one of: "active", "proposed", "discontinued", "under review"
- "scope": string — one of: "central", "state"
- "state_name": string — state name if state-specific, else null
- "key_interventions": array of strings — specific activities e.g.:
    ["IFA supplementation", "deworming", "cash transfers", "mid-day meals",
     "take-home rations", "food fortification", "behaviour change communication",
     "POSHAN Tracker", "anganwadi services", "conditional cash transfer"]
- "summary": string — 2–3 sentence plain-language summary of the program
- "source_url": string — as provided

Important rules:
- Only include programs related to anaemia, malnutrition, nutrition, food security, or micronutrient deficiency.
- If the press release is about a completely unrelated topic, return an empty array [].
- Do not invent data. Use null for missing fields.
- Return valid JSON only, no markdown fences.

---
MINISTRY: {ministry}
SOURCE URL: {source_url}
TITLE: {title}
BODY:
{body}
---
Return JSON array:
"""


def extract_program_info(
    title: str,
    body: str,
    ministry: str,
    source_url: str,
) -> list[dict]:
    """
    Call Gemini to extract structured program records from press release text.
    Returns a list of program dicts (may be empty).
    """
    prompt = EXTRACTION_PROMPT.format(
        ministry=ministry,
        source_url=source_url,
        title=title,
        body=body[:5000],          # stay within token limits
    )
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown fences if Gemini adds them despite instructions
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError as e:
        print(f"[gemini] JSON parse error: {e}\nRaw: {raw[:300]}")
        return []
    except Exception as e:
        print(f"[gemini] API error: {e}")
        return []