"""
One-time Gmail OAuth setup for the Mailman agent.

Run this ONCE interactively to authorize Gmail access:

    cd backend
    ..\\.venv\\Scripts\\python.exe gmail_auth.py        (Windows)
    ../.venv/bin/python gmail_auth.py                   (macOS/Linux)

It opens your browser, you grant access, and it saves a reusable token to
data/gmail_token.json. After that, the Mailman agent runs fully unattended —
no browser needed — because it loads the saved token.

PREREQUISITE — create gmail_credentials.json first:
  1. Go to https://console.cloud.google.com/
  2. Create (or pick) a project.
  3. APIs & Services → Library → search "Gmail API" → Enable.
  4. APIs & Services → OAuth consent screen → External → fill app name +
     your email → add yourself under "Test users".
  5. APIs & Services → Credentials → Create Credentials → OAuth client ID →
     Application type: "Desktop app" → Create → Download JSON.
  6. Rename the downloaded file to  gmail_credentials.json  and place it in
     the project root (next to README.md).
Then run this script.
"""
import os
import sys
from pathlib import Path

# allow importing config from this directory
sys.path.insert(0, str(Path(__file__).parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


def main():
    print("=" * 60)
    print(" Mailman - Gmail OAuth one-time setup")
    print("=" * 60)

    if not os.path.exists(GMAIL_CREDENTIALS_FILE):
        print(f"\n[ERROR] Missing credentials file: {GMAIL_CREDENTIALS_FILE}")
        print("   Follow the steps in the docstring at the top of this file")
        print("   to download gmail_credentials.json, then run this again.\n")
        sys.exit(1)

    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        print(f"\n[INFO] Existing token found at {GMAIL_TOKEN_FILE}")
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("\n[BROWSER] Opening your browser for Gmail consent...")
            print("   Sign in and click 'Allow'. If you see an 'unverified app'")
            print("   warning, click Advanced -> Go to <app> (unsafe) -- it's YOUR app.\n")
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(GMAIL_TOKEN_FILE), exist_ok=True)
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"\n[OK] Token saved to {GMAIL_TOKEN_FILE}")

    # quick sanity check
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"\n[OK] Connected to Gmail as: {profile.get('emailAddress')}")
    print(f"   Total messages in mailbox: {profile.get('messagesTotal')}")
    print("\n[DONE] Mailman will now read your real inbox on its next run.")
    print("   Trigger it from the dashboard -> Mailman -> 'Scan Inbox Now'.\n")


if __name__ == "__main__":
    main()
