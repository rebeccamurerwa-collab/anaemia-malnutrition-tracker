import os
import time
import requests
from bs4 import BeautifulSoup
from gemini_processor import extract_program_info
from database import upsert_program

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

KEYWORDS = [
    "anaemia", "anemia", "malnutrition", "nutrition", "poshan",
    "anganwadi", "icds", "stunting", "wasting",
    "mid-day meal", "midday meal", "food security",
    "iron deficiency", "folic acid", "ifa supplementation",
    "micronutrient", "food fortification", "supplementary nutrition",
    "take home ration", "therapeutic food", "acute malnutrition",
    "poshan abhiyaan", "anaemia mukt", "rashtriya poshan",
    "child nutrition", "maternal nutrition", "infant nutrition",
]

PROCESSED_FILE = "processed_relids.txt"

RELID_RANGES = [
    (1000,   50000,  50),
    (50000,  100000, 50),
    (100000, 150000, 30),
    (150000, 200000, 20),
    (200000, 250000, 10),
    (250000, 286000, 5),
]

WEEKLY_RANGE = (285000, 286000, 1)

def _is_relevant(text):
    t = text.lower()
    return any(k in t for k in KEYWORDS)

def _load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())

def _save_processed(relid):
    with open(PROCESSED_FILE, "a") as f:
        f.write(str(relid) + "\n")

def fetch_print_release(relid):
    url = f"https://pib.gov.in/newsite/PrintRelease.aspx?relid={relid}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        paras = [p.get_text(strip=True) for p in soup.find_all('p')
                 if len(p.get_text(strip=True)) > 30]
        if not paras:
            return None
        text = " ".join(paras)
        if len(text) < 100:
            return None
        return {"text": text, "url": url, "relid": relid}
    except Exception as e:
        print(f"[scraper] Error fetching relid {relid}: {e}")
        return None

def scrape_range(start, end, step, label=''):
    count = 0
    processed = _load_processed()
    relids = [r for r in range(start, end, step) if r not in processed]
    print(f"[scraper] {label}: checking {len(relids)} relids, {len(processed)} already processed")
    for i, relid in enumerate(relids):
        release = fetch_print_release(relid)
        if not release:
            _save_processed(relid)
            time.sleep(0.2)
            continue
        text = release['text']
        if not _is_relevant(text):
            _save_processed(relid)
            time.sleep(0.2)
            continue
        print(f"[scraper] Relevant relid {relid}: {text[:80]}")
        ministry = "PIB / Multiple Ministries"
        t = text.lower()
        if "health" in t or "mohfw" in t:
            ministry = "Ministry of Health and Family Welfare (MoHFW)"
        elif "women and child" in t or "wcd" in t or "anganwadi" in t:
            ministry = "Ministry of Women and Child Development (MoWCD)"
        elif "consumer affairs" in t or "food and public" in t:
            ministry = "Ministry of Consumer Affairs, Food & Public Distribution (MoCAFPD)"
        elif "education" in t or "mid-day meal" in t:
            ministry = "Ministry of Education (MoE)"
        elif "tribal" in t:
            ministry = "Ministry of Tribal Affairs (MoTA)"
        elif "niti aayog" in t:
            ministry = "NITI Aayog"
        title = text[:120]
        programs = extract_program_info(
            title=title,
            body=text[:5000],
            ministry=ministry,
            source_url=release['url'],
        )
        for p in programs:
            upsert_program(p)
            count += 1
        _save_processed(relid)
        time.sleep(0.8)
        if (i + 1) % 100 == 0:
            print(f"[scraper] Progress: {i+1}/{len(relids)} checked, {count} records so far")
    print(f"[scraper] {label}: done. {count} records upserted.")
    return count

def run_full_scrape(pages_per_ministry=5):
    total = 0
    for start, end, step in RELID_RANGES:
        label = f"relid {start}-{end}"
        total += scrape_range(start, end, step, label)
    print(f"[scraper] Full archive scrape complete. {total} total records.")
    return total

def run_weekly_scrape():
    start, end, step = WEEKLY_RANGE
    count = scrape_range(start, end, step, "weekly update")
    print(f"[scraper] Weekly scrape complete. {count} new records.")
    return count