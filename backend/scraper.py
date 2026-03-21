"""
PIB scraper — uses RSS feeds to get PRIDs, then fetches
each press release via PressReleasePage.aspx?PRID=...
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from gemini_processor import extract_program_info
from database import upsert_program

BASE_URL = "https://pib.gov.in"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://pib.gov.in/",
}

MINISTRY_MAP = {
    "25": "Ministry of Health and Family Welfare (MoHFW)",
    "36": "Ministry of Consumer Affairs, Food & Public Distribution (MoCAFPD)",
    "56": "Ministry of Women and Child Development (MoWCD)",
    "16": "Ministry of Education (MoE)",
    "53": "Ministry of Tribal Affairs (MoTA)",
    "27": "NITI Aayog",
}

KEYWORDS = [
    # English
    "anaemia", "anemia", "malnutrition", "nutrition",
    # Hindi
    "एनीमिया", "रक्ताल्पता", "कुपोषण", "पोषण",
]


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in KEYWORDS)


def _extract_prids_from_rss(min_code: str) -> list[str]:
    """
    Fetch RSS feed for a ministry and extract all PRIDs from URLs.
    Returns list of PRID strings.
    """
    url = (
        f"https://pib.gov.in/RssMain.aspx"
        f"?ModId=6&Lang=1&Regid=3&MinCode={min_code}"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        # Parse as XML using lxml
        soup = BeautifulSoup(resp.content, features="xml")
        
        prids = set()
        
        # Extract PRIDs from all links in the RSS
        for tag in soup.find_all(["link", "guid", "description", "title"]):
            text = tag.get_text()
            # Find PRID= patterns in URLs
            matches = re.findall(r"PRID=(\d+)", text)
            prids.update(matches)
        
        # Also search raw text for PRID patterns
        raw_matches = re.findall(r"PRID=(\d+)", resp.text)
        prids.update(raw_matches)
        
        print(f"[scraper]   Found {len(prids)} PRIDs in RSS for ministry {min_code}")
        return list(prids)
    except Exception as e:
        print(f"[scraper] RSS error for ministry {min_code}: {e}")
        return []


def _fetch_press_release(prid: str) -> dict:
    """
    Fetch full text of a press release by PRID.
    Returns dict with title and body.
    """
    url = f"https://pib.gov.in/PressReleasePage.aspx?PRID={prid}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Get title
        title = ""
        for sel in ["h2", "h1", "title", ".release-title"]:
            t = soup.select_one(sel)
            if t and len(t.get_text(strip=True)) > 10:
                title = t.get_text(strip=True)
                break
        
        # Get body — try multiple selectors
        body = ""
        for selector in [
            "div.innner-page-content",
            "div#ContentPlaceHolder1_lblContentDetail",
            "div.content-area",
            "div.press-content",
            "div#content",
            "article",
        ]:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    body = text[:6000]
                    break
        
        # Fallback: get all paragraphs
        if not body:
            paras = soup.find_all("p")
            body = "\n".join(p.get_text(strip=True) for p in paras
                           if len(p.get_text(strip=True)) > 20)[:6000]
        
        return {"title": title, "body": body, "url": url, "prid": prid}
    except Exception as e:
        print(f"[scraper] Error fetching PRID {prid}: {e}")
        return {}


def _fetch_archive_prids(min_code: str, pages: int = 10) -> list[str]:
    """
    Fetch PRIDs from archive pages by scraping the IframePage links.
    These pages load content server-side.
    """
    prids = set()
    for page in range(1, pages + 1):
        try:
            url = (
                f"https://pib.gov.in/allRel.aspx"
                f"?reg=3&lang=1&MinCode={min_code}"
                f"&strdate=&enddate=&Pageno={page}"
            )
            resp = requests.get(url, headers=HEADERS, timeout=20)
            # Extract any PRID numbers from the raw HTML
            matches = re.findall(r"PRID=(\d+)", resp.text)
            prids.update(matches)
            if not matches:
                break  # No more pages
            time.sleep(1)
        except Exception as e:
            print(f"[scraper] Archive page error: {e}")
            break
    return list(prids)


def run_full_scrape(pages_per_ministry: int = 5) -> int:
    """
    Full scrape using RSS + archive pages.
    Returns number of records upserted.
    """
    count = 0
    seen_prids = set()

    for min_code, ministry_name in MINISTRY_MAP.items():
        print(f"\n[scraper] Processing {ministry_name}...")

        # Get PRIDs from RSS feed (recent releases)
        rss_prids = _extract_prids_from_rss(min_code)

        # Get PRIDs from archive pages (historical)
        arc_prids = _fetch_archive_prids(min_code, pages=pages_per_ministry)

        all_prids = list(set(rss_prids + arc_prids))
        print(f"[scraper]   Total unique PRIDs: {len(all_prids)}")

        for prid in all_prids:
            if prid in seen_prids:
                continue
            seen_prids.add(prid)

            release = _fetch_press_release(prid)
            if not release or not release.get("body"):
                continue

            # Check relevance
            combined = release["title"] + " " + release["body"]
            if not _is_relevant(combined):
                continue

            print(f"[scraper]   ✓ Relevant: {release['title'][:60]}")

            programs = extract_program_info(
                title=release["title"],
                body=release["body"],
                ministry=ministry_name,
                source_url=release["url"],
            )
            for p in programs:
                upsert_program(p)
                count += 1

            time.sleep(0.8)

    print(f"\n[scraper] Complete. {count} records upserted.")
    return count