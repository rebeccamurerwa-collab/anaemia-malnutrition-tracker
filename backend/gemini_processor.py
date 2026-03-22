import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

EXTRACTION_PROMPT = """
You are a strict nutrition policy analyst for India. Your job is to identify ONLY programs that directly deliver nutrition or anaemia interventions to people.

A program QUALIFIES only if it does ONE OR MORE of these specific things:
1. Gives iron tablets, IFA supplements, or folic acid directly to people
2. Gives food, cooked meals, or nutritional supplements directly to children or women
3. Treats children with acute malnutrition using therapeutic foods (RUTF, F75, F100)
4. Provides take-home rations or supplementary feeding to mothers or children
5. Fortifies staple foods (flour, rice, oil, salt) with micronutrients for direct consumption
6. Provides vitamin A drops or zinc supplements directly to children
7. Runs deworming campaigns for children or women
8. Monitors child growth (height/weight) and provides nutrition support

A program does NOT qualify if it only:
- Increases agricultural production (cereals, pulses, oilseeds, maize)
- Provides general healthcare, insurance, or hospital access
- Focuses on immunisation or vaccination without nutrition component
- Provides cash transfers with no specific nutrition condition
- Improves water supply or sanitation (unless directly linked to nutrition outcomes)
- Addresses tuberculosis, malaria, or other diseases without direct nutrition intervention
- Funds research, builds infrastructure, or trains health workers without direct beneficiary nutrition

DEDUPLICATION:
- If the same program appears multiple times, include it ONCE only
- "POSHAN Abhiyaan", "Poshan Abhiyan", "POSHAN Mission" = same program, use "POSHAN Abhiyaan"
- "Mid-Day Meal Scheme", "PM POSHAN", "Mid-day Meal" = same program, use "PM POSHAN"

QUALITY CHECK - reject any program where you cannot fill in ALL THREE of:
- A specific official program name
- At least one qualifying intervention from the list above
- A specific beneficiary group (not just "population" or "people")

Return a JSON array. Each element must have:
- "program_name": string - most official name
- "ministry": string - as provided
- "date_announced": string - 4-digit launch year only e.g. "2018", or null
- "target_beneficiaries": string - specific group e.g. "children under 5, pregnant women"
- "budget_amount": string with units or null
- "status": one of: active, proposed, discontinued, under review
- "scope": one of: central, state
- "state_name": state name if state-specific, else null
- "category": one of: anaemia, malnutrition, both
- "key_interventions": array - only use these exact terms:
    ["IFA supplementation", "deworming", "mid-day meals", "take-home rations",
     "food fortification", "therapeutic feeding", "RUTF", "growth monitoring",
     "micronutrient supplementation", "dietary counselling", "supplementary nutrition",
     "vitamin A supplementation", "zinc supplementation", "haemoglobin testing",
     "nutrition rehabilitation", "cash transfers with nutrition conditions",
     "anganwadi services", "POSHAN Tracker", "kitchen gardens"]
- "summary": 2-3 sentences in English
- "source_url": as provided

If NO programs qualify, return [].
Return valid JSON only. No markdown. No explanation.

---
MINISTRY: {ministry}
SOURCE URL: {source_url}
TITLE: {title}
BODY:
{body}
---
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