"""
Fix missing thread_id for a contact.
Searches Gmail for the sent email, gets the thread ID, and saves it to HubSpot.

Usage (from CRM root):
    venv\Scripts\python backend\fix_thread_id.py
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

import sys
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # backend/
sys.path.insert(0, str(ROOT))                   # CRM/

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import hubspot_crm as crm
import gmail_sender as gmail
from gmail_setup import get_gmail_service

CONTACT_EMAIL = "test.contacted.web@yopmail.com"
CONTACT_ID    = "484989970130"   # from: venv\Scripts\python backend\check_contact.py

print("=" * 60)
print(f"Looking for Gmail thread sent to: {CONTACT_EMAIL}")
print("=" * 60)

# Search Gmail for sent messages to this address
service = get_gmail_service()
result = service.users().messages().list(
    userId="me",
    q=f"to:{CONTACT_EMAIL}",
    maxResults=5,
).execute()

messages = result.get("messages", [])
if not messages:
    print("No sent messages found in Gmail for this contact.")
    print("The email may not have been sent, or Gmail search is delayed.")
    sys.exit(1)

print(f"Found {len(messages)} message(s) in Gmail:")

# Get the most recent message
msg = service.users().messages().get(
    userId="me",
    id=messages[0]["id"],
    format="metadata",
    metadataHeaders=["Subject", "Message-ID", "To"],
).execute()

thread_id  = msg["threadId"]
msg_id_raw = msg["id"]

# Get the RFC Message-ID header
rfc_msg_id = gmail.get_message_id_header(msg_id_raw) or msg_id_raw

print(f"  Gmail msg ID  : {msg_id_raw}")
print(f"  Thread ID     : {thread_id}")
print(f"  RFC Message-ID: {rfc_msg_id}")

# Get subject from headers
headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
print(f"  Subject       : {headers.get('Subject', '(unknown)')}")
print(f"  To            : {headers.get('To', '(unknown)')}")

# Save to HubSpot
print(f"\nSaving thread state to HubSpot contact {CONTACT_ID}...")
client = crm.get_client()
crm.mark_sequence_day_sent(
    client,
    contact_id      = CONTACT_ID,
    day             = 1,
    thread_id       = thread_id,
    last_message_id = rfc_msg_id,
    references      = rfc_msg_id,
)

print("✅ HubSpot updated:")
print(f"   email_sequence_day    = 1")
print(f"   email_thread_id       = {thread_id}")
print(f"   email_last_message_id = {rfc_msg_id}")
print(f"   lead_status           = Active")
print()
print("Now run: venv\\Scripts\\python backend\\run_reply_check.py")
print("=" * 60)
