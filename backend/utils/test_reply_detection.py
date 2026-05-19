"""
Reply Detection Test Script
============================
Tests the full reply detection loop WITHOUT needing HubSpot contacts.

What this script does:
  1. Sends a Day 1 email to a test yopmail address
  2. Polls Gmail every 30 seconds for a reply on that thread
  3. When reply detected → prints success + logs timestamp
  4. Optionally updates HubSpot if a contact_id is provided

How to test:
  Step 1: Run this script
  Step 2: Go to https://yopmail.com → open the inbox for TEST_EMAIL
  Step 3: Open the email → click Reply → type anything → Send
  Step 4: Watch this script detect the reply within 30 seconds

Usage:
    venv\\Scripts\\python test_reply_detection.py
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
import os
import time
import logging
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

from gmail_sender import send_new_email, get_message_id_header, contact_has_replied
from email_templates import get_template

# ── Config ────────────────────────────────────────────────────────────────────

TEST_EMAIL   = "test.reply.check@yopmail.com"   # yopmail inbox to send to
LEAD_TYPE    = "General"                          # bulk_liquid / private_label / general
EXPO_NAME    = "Singapore Expo 2025"
FIRST_NAME   = "Test"
POLL_SECONDS = 30                                 # how often to check for reply
MAX_POLLS    = 20                                 # stop after this many checks (10 min)

OUR_EMAIL    = os.getenv("GMAIL_SENDER", "")

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(__import__("pathlib").Path(__file__).parent.parent / "logs" / "reply_detection_run.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# ── Step 1: Send Day 1 email ──────────────────────────────────────────────────

def send_test_email() -> dict:
    """Sends a Day 1 email to TEST_EMAIL and returns thread info."""
    contact = {
        "firstname": FIRST_NAME,
        "lead_type": LEAD_TYPE,
        "expo_name": EXPO_NAME,
    }

    subject, body = get_template(1, LEAD_TYPE, contact)

    log.info(f"Sending Day 1 test email to: {TEST_EMAIL}")
    log.info(f"Subject: {subject}")

    result = send_new_email(
        to      = TEST_EMAIL,
        subject = subject,
        body    = body,
    )

    gmail_msg_id = result["id"]
    thread_id    = result["threadId"]
    rfc_msg_id   = get_message_id_header(gmail_msg_id)

    log.info(f"Email sent successfully!")
    log.info(f"  Gmail msg ID : {gmail_msg_id}")
    log.info(f"  Thread ID    : {thread_id}")
    log.info(f"  RFC Msg-ID   : {rfc_msg_id}")

    return {
        "gmail_msg_id": gmail_msg_id,
        "thread_id":    thread_id,
        "rfc_msg_id":   rfc_msg_id,
    }


# ── Step 2: Poll Gmail for reply ──────────────────────────────────────────────

def poll_for_reply(thread_id: str) -> bool:
    """
    Polls Gmail every POLL_SECONDS for a reply on the given thread.
    Returns True when a reply is detected, False if timed out.

    Checks sender address carefully:
    - Gmail threads include your own sent messages
    - Only flags as 'replied' if message is FROM the lead, not from our sending address
    """
    log.info("")
    log.info("=" * 60)
    log.info("WAITING FOR REPLY")
    log.info("=" * 60)
    log.info(f"Thread ID    : {thread_id}")
    log.info(f"Our email    : {OUR_EMAIL}")
    log.info(f"Checking every {POLL_SECONDS} seconds (max {MAX_POLLS} checks = {MAX_POLLS * POLL_SECONDS // 60} min)")
    log.info("")
    log.info("ACTION REQUIRED:")
    log.info(f"  1. Go to https://yopmail.com")
    log.info(f"  2. Enter inbox: {TEST_EMAIL.split('@')[0]}")
    log.info(f"  3. Open the email and click Reply")
    log.info(f"  4. Type anything and send")
    log.info("")

    for poll_num in range(1, MAX_POLLS + 1):
        log.info(f"Poll {poll_num}/{MAX_POLLS} — checking thread {thread_id[:16]}...")

        try:
            replied = contact_has_replied(thread_id, our_email=OUR_EMAIL)
        except Exception as e:
            log.warning(f"  Error checking thread: {e}")
            replied = False

        if replied:
            log.info("")
            log.info("=" * 60)
            log.info("REPLY DETECTED!")
            log.info("=" * 60)
            log.info(f"  Thread ID    : {thread_id}")
            log.info(f"  Detected at  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
            log.info(f"  Lead email   : {TEST_EMAIL}")
            log.info("")
            log.info("In production, the sequence runner would now:")
            log.info("  -> Call hubspot_crm.mark_replied(client, contact_id)")
            log.info("  -> Set email_replied = true in HubSpot")
            log.info("  -> Set lead_status = Active in HubSpot")
            log.info("  -> Stop all future sequence emails for this contact")
            return True

        log.info(f"  No reply yet. Waiting {POLL_SECONDS}s...")
        time.sleep(POLL_SECONDS)

    log.info("")
    log.info("Timed out — no reply detected after max polls.")
    log.info(f"You can still reply to {TEST_EMAIL} and run the script again with the thread ID.")
    return False


# ── Optional: Update HubSpot if contact exists ────────────────────────────────

def try_mark_replied_in_hubspot(thread_id: str) -> None:
    """
    If a HubSpot contact with TEST_EMAIL exists, marks them as replied.
    Non-fatal if contact doesn't exist or HubSpot is unavailable.
    """
    try:
        import hubspot_crm as crm
        client = crm.get_client()
        contact = crm.get_contact_by_email(client, TEST_EMAIL)

        if contact:
            contact_id = contact.get("hs_object_id")
            crm.mark_replied(client, contact_id)
            log.info(f"HubSpot updated: contact {contact_id} marked as replied")
            log.info(f"  email_replied    = true")
            log.info(f"  email_replied_at = now")
            log.info(f"  lead_status      = Active")
        else:
            log.info(f"No HubSpot contact found for {TEST_EMAIL} — skipping HubSpot update")
            log.info("(This is fine for testing — in production contacts come from HubSpot)")

    except Exception as e:
        log.warning(f"HubSpot update skipped: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("REPLY DETECTION TEST")
    log.info("=" * 60)
    log.info(f"Test email   : {TEST_EMAIL}")
    log.info(f"Our sender   : {OUR_EMAIL}")
    log.info("")

    # Step 1: Send the email
    try:
        thread_info = send_test_email()
    except Exception as e:
        log.error(f"Failed to send test email: {e}")
        return

    thread_id = thread_info["thread_id"]

    # Step 2: Poll for reply
    reply_found = poll_for_reply(thread_id)

    # Step 3: If reply found, update HubSpot
    if reply_found:
        log.info("")
        log.info("Attempting HubSpot update...")
        try_mark_replied_in_hubspot(thread_id)

    log.info("")
    log.info("=" * 60)
    log.info("TEST COMPLETE")
    log.info(f"Result: {'REPLY DETECTED' if reply_found else 'NO REPLY (timed out)'}")
    log.info("=" * 60)
    log.info(f"Full log saved to: logs/reply_detection_test.log")


if __name__ == "__main__":
    main()
