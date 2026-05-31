"""SMTP email helper — sends HTML emails via Gmail."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import SMTP_HOST, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_RECIPIENT
from database import get_db, EmailRecord


def send_html_email(subject: str, html_body: str,
                    recipient: str = EMAIL_RECIPIENT,
                    agent_name: str = "system") -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Multi-Agent Platform <{EMAIL_ADDRESS}>"
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body, "html"))

    success = False
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
        success = True
    except Exception as e:
        raise RuntimeError(f"Email send failed: {e}") from e
    finally:
        with get_db() as db:
            db.add(EmailRecord(
                agent_name=agent_name,
                subject=subject,
                recipient=recipient,
                sent_at=datetime.utcnow(),
                success=success,
            ))
    return success


EMAIL_BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#f0f2f5; margin:0; padding:20px; }
  .container { max-width:700px; margin:0 auto; background:#fff;
               border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,.1); }
  .header { background:linear-gradient(135deg,#1a1a2e,#16213e);
            color:#fff; padding:28px 32px; }
  .header h1 { margin:0; font-size:24px; }
  .header .sub { opacity:.7; font-size:13px; margin-top:4px; }
  .body { padding:28px 32px; }
  .card { background:#f8f9fa; border-left:4px solid #4f46e5;
          border-radius:8px; padding:16px; margin-bottom:16px; }
  .card h3 { margin:0 0 8px; color:#1a1a2e; font-size:15px; }
  .card p  { margin:0; color:#555; font-size:13px; line-height:1.6; }
  .tag { display:inline-block; background:#4f46e5; color:#fff;
         padding:2px 8px; border-radius:12px; font-size:11px; margin-right:4px; }
  .footer { background:#f8f9fa; padding:16px 32px; text-align:center;
            color:#999; font-size:12px; border-top:1px solid #eee; }
  .metric { display:inline-block; text-align:center; padding:12px 20px;
            background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.06);
            margin:6px; }
  .metric .val { font-size:22px; font-weight:700; color:#4f46e5; }
  .metric .lbl { font-size:11px; color:#888; margin-top:2px; }
  .up   { color:#16a34a; font-weight:600; }
  .down { color:#dc2626; font-weight:600; }
</style>
"""
