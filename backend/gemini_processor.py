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
- "program_name": string
- "ministry": string — as provided
- "date_announced": string — the YEAR the program was launched. Look for "launched in", "started in", "introduced in", "since", "established in". Return just 4-digit year e.g. "2018". If not found return null.
- "target_beneficiaries": string
- "budget_amount": string — with units e.g. "1500 crore"
- "status": string — one of: "active", "proposed", "discontinued", "under review"
- "scope": string — one of: "central", "state"
- "state_name": string — state name if state-specific, else null
- "category": string — one of: "anaemia", "malnutrition", "both". Classify based on program focus.
- "key_interventions": array of strings e.g. ["IFA supplementation", "deworming", "cash transfers", "mid-day meals", "take-home rations", "food fortification", "anganwadi services"]
- "summary": string — 2-3 sentence plain-language summary in English
- "source_url": string — as provided

Rules:
- Only include programs related to anaemia, malnutrition, nutrition, food security, or micronutrient deficiency.
- If unrelated, return empty array [].
- Do not invent data. Use null for missing fields.
- Avoid duplicates: if the same program appears multiple times in the text, only include it once.
- Use the most official and complete version of the program name e.g. prefer "POSHAN Abhiyaan" over "Poshan Mission".
- If unsure whether two mentions are the same program, include only the more detailed one.
- Return valid JSON only, no markdown fences.
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