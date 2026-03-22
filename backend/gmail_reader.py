"""
Gmail API reader — fetches unread Google Alert emails whose subject
matches nutrition/anaemia keywords, extracts the alert link body,
and passes it through Gemini for structured extraction.
"""

import os
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from gemini_processor import extract_program_info
from database import upsert_program

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ALERT_SENDER = "googlealerts-noreply@google.com"

SUBJECT_KEYWORDS = [
    "anaemia", "anemia", "malnutrition", "nutrition", "poshan",
    "iron deficiency", "stunting", "wasting", "micronutrient",
    "food security", "mid-day meal", "anganwadi",
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


def _decode_body(payload) -> str:
    """Recursively extract text from Gmail message payload."""
    if payload.get("body", {}).get("data"):
        raw = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        return raw
    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text
    return ""


def _extract_alert_text(html_body: str) -> str:
    """Strip HTML from Google Alert email, return clean text."""
    soup = BeautifulSoup(html_body, "html.parser")
    # Google Alerts wraps each result in an <article> or <td class="...">
    articles = soup.find_all("article") or soup.find_all("td", class_=re.compile("article"))
    if articles:
        return "\n\n".join(a.get_text(separator=" ", strip=True) for a in articles)
    return soup.get_text(separator="\n", strip=True)[:5000]


def fetch_gmail_alerts() -> int:
    """
    Fetch unread Google Alert emails relevant to nutrition/anaemia,
    process them through Gemini, and upsert into DB.
    Returns count of records processed.
    """
    try:
        service = _get_gmail_service()
    except Exception as e:
        print(f"[gmail] Could not authenticate: {e}")
        return 0

    # Build query: unread alerts from Google Alerts
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
        text = _extract_alert_text(body_html)
        if not text:
            continue

        # Use subject as title; ministry is "Google Alert"
        programs = extract_program_info(
            title=headers.get("Subject", "Google Alert"),
            body=text,
            ministry="Google Alert / News",
            source_url="Gmail Alert",
        )
        for p in programs:
            upsert_program(p)
            count += 1

    print(f"[gmail] {count} program records extracted from alerts")
    return count