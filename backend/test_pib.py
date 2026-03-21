"""
Run this locally to discover which PIB URLs work.
py -3.11 test_pib.py
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://pib.gov.in/",
}

def test_url(label, url):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"URL:  {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"STATUS: {resp.status_code}")
        print(f"CONTENT-TYPE: {resp.headers.get('content-type','')}")
        text = resp.text
        print(f"LENGTH: {len(text)}")
        # Look for press release links
        soup = BeautifulSoup(text, "html.parser")
        links = [a for a in soup.find_all("a", href=True)
                 if len(a.get_text(strip=True)) > 20]
        print(f"MEANINGFUL LINKS: {len(links)}")
        for l in links[:5]:
            print(f"  {l.get('href','')} | {l.get_text(strip=True)[:80]}")
        # Show raw text preview
        clean = soup.get_text(separator=" ", strip=True)
        print(f"TEXT PREVIEW: {clean[200:500]}")
    except Exception as e:
        print(f"ERROR: {e}")

# Test various PIB endpoints
test_url("RSS feed (Ministry 25 - MoHFW)",
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&MinCode=25")

test_url("RSS feed (all ministries)",
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3")

test_url("newsite RSS",
    "https://pib.gov.in/newsite/rss.aspx")

test_url("Search: anaemia",
    "https://pib.gov.in/search.aspx?searchterm=anaemia&lang=1")

test_url("Search: poshan",
    "https://pib.gov.in/search.aspx?searchterm=poshan&lang=1")

test_url("Direct press release",
    "https://pib.gov.in/newsite/PrintRelease.aspx?relid=194906")

test_url("Press release page",
    "https://pib.gov.in/PressReleasePage.aspx?PRID=2107042")

print("\n\nDONE - share the output above!")