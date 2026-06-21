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
from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, EMAIL_RECIPIENT, KEY_PEOPLE

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

# Spec-required categories
CATEGORIES = [
    "urgent", "action_required", "follow_up",
    "newsletter", "notification", "personal", "other"
]


def _normalize_category(raw: str) -> str:
    """Map any LLM category output to a canonical snake_case key."""
    key = (raw or "other").lower().strip().replace(" ", "_").replace("-", "_")
    valid = {
        "urgent", "action_required", "follow_up",
        "newsletter", "notification", "personal", "other",
    }
    # common aliases the LLM may emit
    aliases = {
        "action": "action_required", "actionrequired": "action_required",
        "followup": "follow_up", "follow": "follow_up",
        "promotion": "newsletter", "promotions": "newsletter",
        "marketing": "newsletter", "social": "notification",
        "alert": "notification", "spam": "other", "finance": "action_required",
        "work": "action_required",
    }
    if key in valid:
        return key
    return aliases.get(key, "other")


class MailmanAgent(BaseAgent):
    name = "mailman"

    def _execute(self) -> dict:
        if not os.path.exists(GMAIL_CREDENTIALS_FILE):
            return _demo_mode(self.name)

        service = _get_gmail_service()
        messages = _fetch_unread(service, max_results=20)

        with get_db() as db:
            log_agent(db, self.name, "INFO",
                      f"Connected to Gmail — found {len(messages)} unread message(s)")

        if not messages:
            return {"summary": "Inbox scanned — no unread emails to classify",
                    "processed": 0, "urgent": 0, "key_people": 0}

        processed, urgent, key_people_hits = 0, [], []
        for msg in messages:
            record = _process_message(service, msg, self.name)
            if record:
                processed += 1
                if record.category == "urgent" or record.priority == "high":
                    urgent.append(record)
                if KEY_PEOPLE and any(kp.lower() in record.sender.lower() for kp in KEY_PEOPLE):
                    key_people_hits.append(record)

        if urgent or key_people_hits:
            _send_alert(urgent, key_people_hits)

        return {
            "summary": f"Processed {processed} emails, {len(urgent)} urgent",
            "processed": processed,
            "urgent": len(urgent),
            "key_people": len(key_people_hits),
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

    cats_display = "Urgent, Action Required, Follow-Up, Newsletter, Notification, Personal, Other"
    prompt = f"""Classify this email strictly as JSON with keys: category, priority, summary.
category must be one of: {cats_display}
priority must be one of: high, medium, low
summary: one sentence max 20 words.

Subject: {subject}
From: {sender}
Body preview: {body[:500]}

Respond ONLY with valid JSON, no markdown."""

    try:
        raw = query_llm(prompt, system="You are an email classifier. Output only valid JSON, no markdown.")
        raw = raw.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
        category = _normalize_category(data.get("category", "other"))
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
        db.add(MailmanRecord(
            gmail_msg_id=msg["id"],
            subject=subject,
            sender=sender,
            category=category,
            priority=priority,
            llm_summary=summary,
            starred=(priority == "high"),
            labeled=True,
        ))
        log_agent(db, agent_name, "INFO", f"Classified: {subject[:60]} → {category}/{priority}")

    # Return a detached, plain object (not bound to any session) so the caller
    # can safely read these fields after the DB session has closed.
    from types import SimpleNamespace
    return SimpleNamespace(
        subject=subject, sender=sender, category=category,
        priority=priority, llm_summary=summary,
    )


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


def _send_alert(records: list, key_people: list = None) -> None:
    rows = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #eee">{r.subject[:60]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee">{r.sender[:40]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee"><span class="tag">{r.category}</span></td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee">{r.llm_summary or ""}</td></tr>'
        for r in records
    )
    kp_section = ""
    if key_people:
        kp_rows = "".join(
            f'<tr><td style="padding:8px;border-bottom:1px solid #eee;color:#7f1d1d;font-weight:600">'
            f'⭐ {r.subject[:60]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee">{r.sender[:40]}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee">{r.llm_summary or ""}</td></tr>'
            for r in key_people
        )
        kp_section = f"""
        <h3 style="color:#7f1d1d;margin:20px 0 8px">⭐ Key-People Emails ({len(key_people)})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#fff7ed;font-weight:600;">
            <th style="padding:8px;text-align:left">Subject</th>
            <th style="padding:8px;text-align:left">From</th>
            <th style="padding:8px;text-align:left">Summary</th>
          </tr>{kp_rows}
        </table>"""

    html = f"""<!DOCTYPE html><html><head>{EMAIL_BASE_STYLE}</head><body>
    <div class="container">
      <div class="header" style="background:linear-gradient(135deg,#7f1d1d,#991b1b);">
        <h1>🚨 Mailman — Priority Alert</h1>
        <div class="sub">{len(records)} urgent + {len(key_people or [])} key-people emails</div>
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
        {kp_section}
      </div>
      <div class="footer">Mailman Agent &bull; Multi-Agent Platform</div>
    </div></body></html>"""
    send_html_email("🚨 Priority Emails Detected", html, agent_name="mailman")


_DEMO_INBOX = [
    {"subject": "🚨 URGENT: Production database is down",
     "sender": "ops-alerts@company.com",
     "body": "PagerDuty alert: the primary production database is unreachable. "
             "All customer-facing services are returning 500 errors. Immediate action required."},
    {"subject": "Action needed: Approve Q3 budget by EOD Friday",
     "sender": "finance@company.com",
     "body": "Please review and approve the attached Q3 budget proposal. "
             "We need your sign-off before the board meeting on Monday."},
    {"subject": "Re: Following up on our partnership discussion",
     "sender": "sarah.chen@partnerco.com",
     "body": "Hi, just circling back on the integration proposal we discussed last week. "
             "Did you get a chance to review the API docs I sent over?"},
    {"subject": "Your weekly AI digest — 12 new papers",
     "sender": "newsletter@aiweekly.com",
     "body": "This week in AI: new open-weight models, agentic frameworks, and a viral "
             "paper on speculative decoding. Read the full roundup inside."},
    {"subject": "Your package has shipped 📦",
     "sender": "no-reply@shipping.com",
     "body": "Order #88231 has shipped and will arrive Thursday. Track your package here."},
    {"subject": "Lunch this weekend?",
     "sender": "mike.j@gmail.com",
     "body": "Hey! It's been a while. Want to grab lunch on Saturday and catch up? "
             "Let me know what works for you."},
    {"subject": "Invoice #4521 — payment due in 3 days",
     "sender": "billing@vendor.com",
     "body": "Your invoice of $1,200 is due on the 18th. Please process the payment "
             "to avoid a late fee. Payment portal link enclosed."},
    {"subject": "LinkedIn: You appeared in 9 searches this week",
     "sender": "notifications@linkedin.com",
     "body": "Your profile is getting noticed. See who's been searching for people like you."},
]


def _demo_mode(agent_name: str) -> dict:
    """Run without Gmail credentials — classify a realistic mock inbox and SAVE records."""
    import hashlib
    from datetime import datetime

    processed, urgent, by_cat = 0, [], {}

    for email in _DEMO_INBOX:
        prompt = (f"Classify this email strictly as JSON with keys: category, priority, summary.\n"
                  f"category must be one of: Urgent, Action Required, Follow-Up, Newsletter, "
                  f"Notification, Personal, Other\n"
                  f"priority must be one of: high, medium, low\n"
                  f"summary: one sentence, max 18 words.\n\n"
                  f"Subject: {email['subject']}\n"
                  f"From: {email['sender']}\n"
                  f"Body: {email['body']}\n\n"
                  f"Respond ONLY with valid JSON, no markdown.")
        try:
            raw = query_llm(prompt, system="You are an email classifier. Output only valid JSON.")
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)
            category = _normalize_category(data.get("category", "other"))
            priority = (data.get("priority", "low") or "low").lower()
            summary  = data.get("summary", "")
        except Exception:
            category, priority, summary = "other", "low", ""

        # Stable synthetic message id (so re-runs upsert instead of duplicating)
        msg_id = "demo-" + hashlib.md5(email["subject"].encode()).hexdigest()[:16]

        with get_db() as db:
            existing = db.query(MailmanRecord).filter_by(gmail_msg_id=msg_id).first()
            if existing:
                existing.category    = category
                existing.priority    = priority
                existing.llm_summary = summary
                existing.starred     = (priority == "high")
                existing.processed_at = datetime.utcnow()
            else:
                db.add(MailmanRecord(
                    gmail_msg_id=msg_id,
                    subject=email["subject"],
                    sender=email["sender"],
                    category=category,
                    priority=priority,
                    llm_summary=summary,
                    starred=(priority == "high"),
                    labeled=True,
                ))
            log_agent(db, agent_name, "INFO",
                      f"[DEMO] {email['subject'][:45]} → {category}/{priority}")

        processed += 1
        by_cat[category] = by_cat.get(category, 0) + 1
        if category == "urgent" or priority == "high":
            urgent.append(email["subject"])

    return {
        "summary": f"Classified {processed} emails — {len(urgent)} urgent · "
                   f"{len(by_cat)} categories",
        "processed": processed,
        "urgent": len(urgent),
        "by_category": by_cat,
    }
