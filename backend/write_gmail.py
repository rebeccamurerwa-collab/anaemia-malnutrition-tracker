import os
base = r"C:\Users\rebec\OneDrive\Documents\anaemia-malnutrition-tracker\backend"

gmail = '''import os
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from gemini_processor import extract_program_info
from database import upsert_program

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
ALERT_SENDER = "googlealerts-noreply@google.com"


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


def _extract_alert_text(html_body):
    soup = BeautifulSoup(html_body, "html.parser")
    articles = soup.find_all("article") or soup.find_all("td", class_=re.compile("article"))
    if articles:
        return "\\n\\n".join(a.get_text(separator=" ", strip=True) for a in articles)
    return soup.get_text(separator="\\n", strip=True)[:5000]


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
        text = _extract_alert_text(body_html)
        if not text:
            # Mark as read even if no text found
            service.users().messages().modify(
                userId="me",
                id=msg_ref["id"],
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            continue

        programs = extract_program_info(
            title=subject,
            body=text,
            ministry="Google Alert / News",
            source_url="Gmail Alert",
        )
        for p in programs:
            upsert_program(p)
            count += 1

        # Mark as read after processing so it is never picked up again
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