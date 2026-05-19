"""
Gmail Connection — OAuth Playground Method
No Google Cloud Console needed.
Uses refresh token from OAuth Playground directly.

Run this to test your Gmail connection:
    python gmail_setup.py
"""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).parent.parent.parent      # CRM/
_CORE = _ROOT / "backend" / "core"
_SETUP = _ROOT / "backend" / "setup"
for _p in [str(_ROOT), str(_ROOT / "backend"), str(_CORE), str(_SETUP)]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
del _sys, _Path, _ROOT, _CORE, _SETUP, _p


import os
import base64
from email.mime.text import MIMEText
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

# Google OAuth credentials — loaded from .env
CLIENT_ID     = os.getenv("GMAIL_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
TOKEN_URI     = "https://oauth2.googleapis.com/token"
SCOPES        = ["https://mail.google.com/"]


def get_gmail_credentials() -> Credentials:
    """
    Builds Gmail credentials from the refresh token in .env.
    Auto-refreshes the access token when expired.
    """
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    sender        = os.getenv("GMAIL_SENDER")

    if not refresh_token:
        raise ValueError(
            "GMAIL_REFRESH_TOKEN not found in config/.env\n"
            "Go to developers.google.com/oauthplayground and generate one."
        )
    if not sender:
        raise ValueError("GMAIL_SENDER not found in config/.env")

    creds = Credentials(
        token         = None,
        refresh_token = refresh_token,
        token_uri     = TOKEN_URI,
        client_id     = CLIENT_ID,
        client_secret = CLIENT_SECRET,
        scopes        = SCOPES,
    )

    # Refresh to get a valid access token
    creds.refresh(Request())
    return creds


def get_gmail_service():
    """Returns an authenticated Gmail API service object."""
    creds = get_gmail_credentials()
    return build("gmail", "v1", credentials=creds)


def test_connection() -> bool:
    """
    Sends a test email to yourself to confirm Gmail API is working.
    Check your inbox at aditirajput00710@gmail.com after running.
    """
    sender = os.getenv("GMAIL_SENDER")

    try:
        service = get_gmail_service()

        message = MIMEText(
            "Gmail API is connected and working.\n\n"
            "Your CRM project Phase 2 is ready.\n"
            "Next step: Run validate_csv.py then import_contacts.py\n\n"
            "— CRM Automation"
        )
        message["to"]      = sender
        message["from"]    = sender
        message["subject"] = "✅ CRM Project — Gmail Connected Successfully"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        print(f"\n✅ Gmail connected successfully as: {sender}")
        print(f"✅ Test email sent — Message ID: {result['id']}")
        print(f"✅ Check your inbox at {sender}")
        return True

    except Exception as e:
        print(f"\nFAILED: Gmail connection failed: {e}")
        print("\nPossible reasons:")
        print("  1. Client_ID or Client_Secret in .env is wrong")
        print("  2. GMAIL_REFRESH_TOKEN in .env is wrong or expired")
        print("  3. You need to generate a new token from OAuth Playground")
        print("  4. Access was revoked — go to myaccount.google.com/permissions")
        return False


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("Testing Gmail connection...")
    print(f"Sender       : {os.getenv('GMAIL_SENDER')}")
    print(f"Client ID    : {CLIENT_ID[:20]}..." if CLIENT_ID else "Client ID    : [NOT SET]")
    print(f"Client Secret: {CLIENT_SECRET[:6]}..." if CLIENT_SECRET else "Client Secret: [NOT SET]")
    rt = os.getenv("GMAIL_REFRESH_TOKEN", "")
    print(f"Refresh Token: {rt[:20]}..." if rt else "Refresh Token: [NOT SET]")
    print("Refreshing access token...\n")
    test_connection()
