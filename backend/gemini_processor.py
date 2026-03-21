"""
Uses Groq (free) to extract structured program data
from raw PIB press-release text or Gmail alert snippets.
"""

import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

EXTRACTION_PROMPT = """
You are an expert policy analyst specialising in nutrition and public health programs in India.
Always respond in English, translating any Hindi or other language content to English.

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
- "summary": string — 2-3 sentence plain-language summary of the program in English
- "source_url": string — as provided

Important rules:
- Only include programs related to anaemia, malnutrition, nutrition, food security, or micronutrient deficiency.
- If the press release is about a completely unrelated topic, return an empty array [].
- Do not invent data. Use null for missing fields.
- Return valid JSON only, no markdown fences, no extra text.

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
    Call Groq to extract structured program records from press release text.
    Returns a list of program dicts (may be empty).
    """
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

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

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