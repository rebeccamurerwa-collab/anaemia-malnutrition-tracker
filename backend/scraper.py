"""
PIB scraper — fetches press releases from the Ministry archive pages
and pushes them through Gemini for structured extraction.

Target ministries / dept codes on PIB allRel.aspx:
  MoHFW        → mincode=25
  MoCAFPD      → mincode=36
  MoWCD        → mincode=56
  MoE          → mincode=16
  MoTA         → mincode=53
  NITI Aayog   → mincode=27
"""

import time
import requests
from bs4 import BeautifulSoup
from gemini_processor import extract_program_info
from database import upsert_program

BASE_URL = "https://pib.gov.in"
ARCHIVE_URL = "https://www.pib.gov.in/allRel.aspx?reg=3&lang=1"

MINISTRY_MAP = {
    "25": "Ministry of Health and Family Welfare (MoHFW)",
    "36": "Ministry of Consumer Affairs, Food & Public Distribution (MoCAFPD)",
    "56": "Ministry of Women and Child Development (MoWCD)",
    "16": "Ministry of Education (MoE)",
    "53": "Ministry of Tribal Affairs (MoTA)",
    "27": "NITI Aayog",
}

KEYWORDS = [
    "anaemia", "anemia", "malnutrition", "nutrition", "iron",
    "folic acid", "ifa", "vitamin", "supplementation", "stunting",
    "wasting", "undernutrition", "mid-day meal", "poshan", "sam",
    "mam", "acute malnutrition", "child nutrition", "maternal nutrition",
    "fortification", "food security", "pds", "ration", "deworming",
    "micronutrient", "wcd", "icds", "anganwadi", "poshan abhiyaan",
    "poshan tracker", "cash transfer", "dbt", "food distribution",
    "supplementary nutrition",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in KEYWORDS)


def _fetch_release_links(min_code: str, pages: int = 5) -> list[dict]:
    """Scrape listing pages for a given ministry code."""
    links = []
    for page in range(1, pages + 1):
        url = (
            f"https://pib.gov.in/allRel.aspx?"
            f"reg=3&lang=1&MinCode={min_code}&strdate=&enddate=&Pageno={page}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("ul.ReleaseListing li a"):
                href = a.get("href", "")
                title = a.get_text(strip=True)
                if href and _is_relevant(title):
                    full_url = BASE_URL + href if href.startswith("/") else href
                    links.append({"url": full_url, "title": title,
                                  "min_code": min_code})
        except Exception as e:
            print(f"[scraper] Error fetching listing page {page} for {min_code}: {e}")
        time.sleep(1.2)          # be polite
    return links


def _fetch_release_text(url: str) -> str:
    """Fetch the full text of a single PIB press release."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        # PIB press release body lives in div.innner-page-content
        content_div = (
            soup.select_one("div.innner-page-content") or
            soup.select_one("div#ContentPlaceHolder1_lblContentDetail") or
            soup.find("div", class_=lambda c: c and "content" in c.lower())
        )
        if content_div:
            return content_div.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)[:6000]
    except Exception as e:
        print(f"[scraper] Error fetching release {url}: {e}")
        return ""


def run_full_scrape(pages_per_ministry: int = 5) -> int:
    """
    Run a full archive scrape across all target ministries.
    Returns the number of new/updated records inserted.
    """
    count = 0
    for min_code, ministry_name in MINISTRY_MAP.items():
        print(f"[scraper] Scraping {ministry_name} …")
        links = _fetch_release_links(min_code, pages=pages_per_ministry)
        print(f"[scraper]   → {len(links)} relevant links found")

        for item in links:
            text = _fetch_release_text(item["url"])
            if not text:
                continue
            if not _is_relevant(text):
                continue

            program_data = extract_program_info(
                title=item["title"],
                body=text,
                ministry=ministry_name,
                source_url=item["url"],
            )
            if program_data:
                upsert_program(program_data)
                count += 1
            time.sleep(0.8)

    print(f"[scraper] Done. {count} records upserted.")
    return count