import os
base = r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\backend"

gmail = '''import os
import base64
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from gemini_processor import extract_program_info
from database import upsert_program

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
ALERT_SENDER = "googlealerts-noreply@google.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

KEYWORDS = [
    "anaemia", "anemia", "malnutrition", "malnourished",
    "iron deficiency", "folic acid", "ifa supplementation",
    "micronutrient", "food fortification", "supplementary nutrition",
    "child nutrition", "maternal nutrition", "infant nutrition",
]


def _get_gmail_service():
    creds = None
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "token.json")
    creds_path = os.environ.get("GMAIL_CREDS_PATH", "credentials.json")
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _get_email_parts(payload):
    """Extract HTML and plain text bodies from email payload."""
    html_body = ""
    plain_body = ""
    for part in payload.get("parts", []):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if mime == "text/html":
                html_body = decoded
            elif mime == "text/plain":
                plain_body = decoded
        # Handle nested parts
        for subpart in part.get("parts", []):
            submime = subpart.get("mimeType", "")
            subdata = subpart.get("body", {}).get("data", "")
            if subdata:
                subdecoded = base64.urlsafe_b64decode(subdata).decode("utf-8", errors="replace")
                if submime == "text/html" and not html_body:
                    html_body = subdecoded
                elif submime == "text/plain" and not plain_body:
                    plain_body = subdecoded
    # Fallback to top-level body
    if not html_body and not plain_body:
        data = payload.get("body", {}).get("data", "")
        if data:
            plain_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return html_body, plain_body


def _extract_article_urls(html_body, plain_body):
    """Extract actual article URLs from Google Alert email."""
    links = []

    # Method 1: Extract from plain text (most reliable)
    google_urls = re.findall(r'https://www\\.google\\.com/url\\?[^\\s>]+', plain_body)
    for gurl in google_urls:
        match = re.search(r"url=(https?://[^&\\s]+)", gurl)
        if match:
            actual = urllib.parse.unquote(match.group(1))
            if "google.com" not in actual:
                links.append(actual)

    # Method 2: Extract from HTML
    if not links and html_body:
        soup = BeautifulSoup(html_body, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "google.com/url" in href:
                match = re.search(r"url=(https?://[^&]+)", href)
                if match:
                    actual = urllib.parse.unquote(match.group(1))
                    if "google.com" not in actual:
                        links.append(actual)
            elif href.startswith("http") and "google.com" not in href:
                links.append(href)

    # Remove duplicates
    seen = set()
    unique = []
    for l in links:
        if l not in seen:
            seen.add(l)
            unique.append(l)
    return unique[:10]


def _fetch_article_text(url):
    """Fetch full text of a news article."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        for selector in [
            "article", "div.article-body", "div.story-body",
            "div.content-body", "div.post-content", "div.entry-content",
            "div.article-content", "main", "div.story-content",
        ]:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator=" ", strip=True)
                if len(text) > 200:
                    return text[:5000]
        paras = [p.get_text(strip=True) for p in soup.find_all("p")
                 if len(p.get_text(strip=True)) > 50]
        return " ".join(paras)[:5000]
    except Exception as e:
        print(f"[gmail] Error fetching article {url}: {e}")
        return ""


def _is_relevant(text):
    t = text.lower()
    return any(k in t for k in KEYWORDS)


def fetch_gmail_alerts():
    try:
        service = _get_gmail_service()
    except Exception as e:
        print(f"[gmail] Could not authenticate: {e}")
        return 0

    query = f"from:{ALERT_SENDER} is:unread"
    results = service.users().messages().list(
        userId="me", q=query, maxResults=50
    ).execute()

    messages = results.get("messages", [])
    print(f"[gmail] Found {len(messages)} unread alert emails")

    count = 0
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"]
                   for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "")

        html_body, plain_body = _get_email_parts(msg["payload"])
        article_urls = _extract_article_urls(html_body, plain_body)
        print(f"[gmail] Found {len(article_urls)} article links in: {subject}")

        if article_urls:
            for url in article_urls:
                article_text = _fetch_article_text(url)
                if not article_text or not _is_relevant(article_text):
                    continue
                print(f"[gmail] Processing: {url[:80]}")
                programs = extract_program_info(
                    title=subject,
                    body=article_text,
                    ministry="Google Alert / News",
                    source_url=url,
                )
                for p in programs:
                    p["source_url"] = url
                    upsert_program(p)
                    count += 1
        else:
            # Fallback to email snippet
            snippet = plain_body or html_body
            if snippet and _is_relevant(snippet):
                programs = extract_program_info(
                    title=subject,
                    body=snippet[:5000],
                    ministry="Google Alert / News",
                    source_url="Gmail Alert",
                )
                for p in programs:
                    upsert_program(p)
                    count += 1

        # Mark as read
        service.users().messages().modify(
            userId="me",
            id=msg_ref["id"],
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    print(f"[gmail] {count} program records extracted from alerts")
    return count
'''

with open(os.path.join(base, "gmail_reader.py"), "w", encoding="utf-8") as f:
    f.write(gmail.strip())
print("gmail_reader.py written!")