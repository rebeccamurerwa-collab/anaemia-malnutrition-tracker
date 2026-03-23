import os
import base64
import re
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


def _decode_body(payload):
    if payload.get("body", {}).get("data"):
        raw = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        return raw
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text
    return ""


def _extract_alert_links(html_body):
    """Extract actual article URLs from Google Alert email."""
    soup = BeautifulSoup(html_body, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        # Google Alerts wraps links in a Google redirect URL
        # Extract the actual URL from the redirect
        if "google.com/url" in href:
            match = re.search(r"url=([^&]+)", href)
            if match:
                import urllib.parse
                actual_url = urllib.parse.unquote(match.group(1))
                if actual_url.startswith("http") and "google.com" not in actual_url:
                    links.append(actual_url)
        elif href.startswith("http") and "google.com" not in href:
            links.append(href)
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for l in links:
        if l not in seen:
            seen.add(l)
            unique_links.append(l)
    return unique_links[:10]  # max 10 articles per alert


def _fetch_article_text(url):
    """Fetch full text of a news article."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove navigation, ads, scripts
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        # Try common article content selectors
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
        # Fallback: get all paragraphs
        paras = [p.get_text(strip=True) for p in soup.find_all("p")
                 if len(p.get_text(strip=True)) > 50]
        return " ".join(paras)[:5000]
    except Exception as e:
        print(f"[gmail] Error fetching article {url}: {e}")
        return ""


def _is_relevant(text):
    t = text.lower()
    return any(k in t for k in KEYWORDS)


def _extract_alert_snippet(html_body):
    """Fallback: extract snippet text from alert email."""
    soup = BeautifulSoup(html_body, "html.parser")
    articles = soup.find_all("article") or soup.find_all("td", class_=re.compile("article"))
    if articles:
        return "\n\n".join(a.get_text(separator=" ", strip=True) for a in articles)
    return soup.get_text(separator="\n", strip=True)[:5000]


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
        body_html = _decode_body(msg["payload"])

        # Extract article links from the alert
        article_links = _extract_alert_links(body_html)
        print(f"[gmail] Found {len(article_links)} article links in alert: {subject}")

        # Process each article
        for url in article_links:
            # First check snippet relevance quickly
            article_text = _fetch_article_text(url)
            if not article_text:
                # Fallback to email snippet
                article_text = _extract_alert_snippet(body_html)

            if not article_text or not _is_relevant(article_text):
                continue

            print(f"[gmail] Processing article: {url[:80]}")

            programs = extract_program_info(
                title=subject,
                body=article_text,
                ministry="Google Alert / News",
                source_url=url,
            )
            for p in programs:
                # Use article URL as source instead of "Gmail Alert"
                p["source_url"] = url
                upsert_program(p)
                count += 1

        # If no article links found, fall back to email snippet
        if not article_links:
            snippet = _extract_alert_snippet(body_html)
            if snippet and _is_relevant(snippet):
                programs = extract_program_info(
                    title=subject,
                    body=snippet,
                    ministry="Google Alert / News",
                    source_url="Gmail Alert",
                )
                for p in programs:
                    upsert_program(p)
                    count += 1

        # Mark as read after processing
        service.users().messages().modify(
            userId="me",
            id=msg_ref["id"],
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    print(f"[gmail] {count} program records extracted from alerts")
    return count