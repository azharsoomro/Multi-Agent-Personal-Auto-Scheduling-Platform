"""Mailman — monitors Gmail, classifies emails with LLM, labels/stars/alerts."""
import base64
import json
import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agents.base_agent import BaseAgent
from llm_client import query_llm
from email_utils import send_html_email, EMAIL_BASE_STYLE
from database import get_db, log_agent, MailmanRecord
from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, EMAIL_RECIPIENT

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

CATEGORIES = ["urgent", "newsletter", "work", "social", "spam", "finance", "personal", "other"]


class MailmanAgent(BaseAgent):
    name = "mailman"

    def _execute(self) -> dict:
        if not os.path.exists(GMAIL_CREDENTIALS_FILE):
            return _demo_mode(self.name)

        service = _get_gmail_service()
        messages = _fetch_unread(service, max_results=20)

        processed, urgent = 0, []
        for msg in messages:
            record = _process_message(service, msg, self.name)
            if record:
                processed += 1
                if record.priority == "high":
                    urgent.append(record)

        if urgent:
            _send_alert(urgent)

        return {
            "summary": f"Processed {processed} emails, {len(urgent)} urgent",
            "processed": processed,
            "urgent": len(urgent),
        }


def _get_gmail_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(GMAIL_TOKEN_FILE), exist_ok=True)
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _fetch_unread(service, max_results: int = 20) -> list:
    result = service.users().messages().list(
        userId="me", labelIds=["UNREAD"], maxResults=max_results
    ).execute()
    return result.get("messages", [])


def _get_message_text(payload: dict) -> str:
    def decode_part(part):
        data = part.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    if payload.get("mimeType") == "text/plain":
        return decode_part(payload)
    for part in payload.get("parts", []):
        text = _get_message_text(part)
        if text:
            return text
    return ""


def _process_message(service, msg: dict, agent_name: str) -> "MailmanRecord | None":
    with get_db() as db:
        existing = db.query(MailmanRecord).filter_by(gmail_msg_id=msg["id"]).first()
        if existing:
            return None

    full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
    headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}
    subject = headers.get("Subject", "(no subject)")
    sender  = headers.get("From", "unknown")
    body    = _get_message_text(full["payload"])[:1000]

    prompt = f"""Classify this email strictly as JSON with keys: category, priority, summary.
category must be one of: {', '.join(CATEGORIES)}
priority must be one of: high, medium, low
summary: one sentence max 20 words.

Subject: {subject}
From: {sender}
Body preview: {body[:500]}

Respond ONLY with valid JSON."""

    try:
        raw = query_llm(prompt, system="You are an email classifier. Output only JSON.")
        # strip markdown code fences if present
        raw = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
        category = data.get("category", "other")
        priority = data.get("priority", "low")
        summary  = data.get("summary", "")
    except Exception:
        category, priority, summary = "other", "low", ""

    # apply label
    label_id = _ensure_label(service, f"AI/{category.title()}")
    body_req = {"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]}
    if priority == "high":
        body_req["addLabelIds"].append("STARRED")
    service.users().messages().modify(userId="me", id=msg["id"], body=body_req).execute()

    with get_db() as db:
        record = MailmanRecord(
            gmail_msg_id=msg["id"],
            subject=subject,
            sender=sender,
            category=category,
            priority=priority,
            llm_summary=summary,
            starred=(priority == "high"),
            labeled=True,
        )
        db.add(record)
        log_agent(db, agent_name, "INFO", f"Classified: {subject[:60]} → {category}/{priority}")
    return record


_label_cache: dict[str, str] = {}

def _ensure_label(service, name: str) -> str:
    if name in _label_cache:
        return _label_cache[name]
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"] == name:
            _label_cache[name] = lbl["id"]
            return lbl["id"]
    created = service.users().labels().create(
        userId="me",
        body={"name": name, "labelListVisibility": "labelShow",
              "messageListVisibility": "show"}
    ).execute()
    _label_cache[name] = created["id"]
    return created["id"]


def _send_alert(records: list) -> None:
    rows = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #eee">{r.subject[:60]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee">{r.sender[:40]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee"><span class="tag">{r.category}</span></td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee">{r.llm_summary or ""}</td></tr>'
        for r in records
    )
    html = f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header" style="background:linear-gradient(135deg,#7f1d1d,#991b1b);">
        <h1>🚨 Mailman — Urgent Email Alert</h1>
        <div class="sub">{len(records)} high-priority emails need attention</div>
      </div>
      <div class="body">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#f8f9fa;font-weight:600;">
            <th style="padding:8px;text-align:left">Subject</th>
            <th style="padding:8px;text-align:left">From</th>
            <th style="padding:8px;text-align:left">Category</th>
            <th style="padding:8px;text-align:left">Summary</th>
          </tr>{rows}
        </table>
      </div>
      <div class="footer">Mailman Agent &bull; Multi-Agent Platform</div>
    </div></body></html>"""
    send_html_email("🚨 Urgent Emails Detected", html, agent_name="mailman")


def _demo_mode(agent_name: str) -> dict:
    """Run without Gmail credentials — classify mock emails."""
    mock_emails = [
        {"subject": "URGENT: Server Down in Production", "sender": "ops@company.com",
         "body": "The production database is unreachable. All services are impacted."},
        {"subject": "Weekly Newsletter — AI Trends", "sender": "newsletter@aiweekly.com",
         "body": "This week in AI: new models, papers, and tools you should know about."},
        {"subject": "Invoice #4521 Due", "sender": "billing@vendor.com",
         "body": "Your invoice of $1,200 is due in 3 days. Please process payment."},
    ]

    results = []
    for email in mock_emails:
        prompt = (f"Classify email. Subject: {email['subject']}. "
                  f"From: {email['sender']}. Body: {email['body']}. "
                  f"Return JSON with category ({', '.join(CATEGORIES)}), "
                  f"priority (high/medium/low), summary (1 sentence).")
        try:
            raw = query_llm(prompt, system="Output only valid JSON.")
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
        except Exception:
            data = {"category": "other", "priority": "low", "summary": ""}
        results.append({**email, **data})
        with get_db() as db:
            log_agent(db, agent_name, "INFO",
                      f"[DEMO] {email['subject'][:50]} → {data.get('category')}/{data.get('priority')}")

    return {"summary": f"Demo mode: classified {len(results)} mock emails", "results": results}
