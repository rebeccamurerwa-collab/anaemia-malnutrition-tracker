import os
base = r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\backend"

content = '''import os
os.environ["GROQ_API_KEY"] = "your_groq_key_here"
os.environ["DB_PATH"] = "test_programs.db"

from scraper import scrape_range

count = scrape_range(180000, 180100, 5, "test run 2018 range")
print(f"Total records found: {count}")
'''

with open(os.path.join(base, "test_scraper_small.py"), "w", encoding="utf-8") as f:
    f.write(content.strip())
print("Done!")