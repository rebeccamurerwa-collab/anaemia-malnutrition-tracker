import os
os.environ["GEMINI_API_KEY"] = "placeholder"

from scraper import _fetch_archive_prids, _fetch_press_release, _is_relevant, KEYWORDS

prids = _fetch_archive_prids("56", pages=3)

for prid in ["2243376", "2243248", "2243362"]:
    r = _fetch_press_release(prid)
    text = r["title"] + " " + r["body"]
    matched = [k for k in KEYWORDS if k in text.lower()]
    print(f"\nPRID {prid}: {r['title'][:60]}")
    print(f"MATCHED KEYWORDS: {matched}")

