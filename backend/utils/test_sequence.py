"""
TEST MODE Sequence Runner
========================
- Sends all 4 emails 15 minutes apart (instead of Day 1, 3, 7, 14)
- Updates HubSpot Lead Status automatically after each email:
    Email 1 sent → Status: Contacted
    Email 2 sent → Status: Followed-up-1
    Email 3 sent → Status: Followed-up-2
    Email 4 sent → Status: Followed-up-3
    No reply after all 4 → Status: Cold
- Checks for replies before each send — stops sequence if reply detected
- Logs every action to console and logs/test_sequence.log

HOW TO RUN:
    python test_sequence.py --email test.bulk.new@yopmail.com
    python test_sequence.py --email test.private.new@yopmail.com
    python test_sequence.py --all   ← runs for all yopmail test contacts

STOP ANYTIME:
    Ctrl+C
"""

import os
import sys
import time
import json
import base64
import logging
import argparse
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
import hubspot
from hubspot.crm.contacts.models import SimplePublicObjectInput
from hubspot.crm.contacts import ApiException

# ── Path setup — works from any working directory ─────────────────────────────
_HERE    = Path(__file__).parent                    # backend/utils/
_BACKEND = _HERE.parent                             # backend/
_ROOT    = _BACKEND.parent                          # repo root (CRM/)
_CORE    = _BACKEND / "core"
_SETUP   = _BACKEND / "setup"
_EMAIL_SETUP = _BACKEND / "email_setup"

for _p in [str(_ROOT), str(_BACKEND), str(_CORE), str(_SETUP), str(_EMAIL_SETUP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

load_dotenv(_ROOT / ".env")

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(str(_ROOT / "logs"), exist_ok=True)
_LOG_FILE = str(_ROOT / "logs" / "test_sequence.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────
TEST_INTERVAL_MINUTES = 15          # gap between each email in test mode
SENDER                = os.getenv("GMAIL_SENDER", "")

# HubSpot hs_lead_status enum values (these exist in your HubSpot account):
#   New, Contacted, Followed-up-1, Followed-up-2, Followed-up-3,
#   Replied, Stalled, Re-engaged, Cold, Archived
STATUS_MAP = {
    0: "Contacted",      # after Email 1 — first contact
    1: "Followed-up-1",  # after Email 2 — Follow-1
    2: "Followed-up-2",  # after Email 3 — Follow-2
    3: "Followed-up-3",  # after Email 4 — Follow-3
    4: "Cold",           # after Email 5 — no reply, mark cold
}

# Human-readable labels for logging
STATUS_LABEL = {
    0: "Contacted (Email 1 sent)",
    1: "Followed-up-1 (Email 2 sent)",
    2: "Followed-up-2 (Email 3 sent)",
    3: "Followed-up-3 (Email 4 sent)",
    4: "Cold (Email 5 sent - last nudge)",
}

# Yopmail test contacts (from your CSV)
TEST_CONTACTS = [
    "test.private.new@yopmail.com",
    "test.general.new@yopmail.com",
    "test.day3.check@yopmail.com",
    "test.day7.check@yopmail.com",
    "test.day14.check@yopmail.com",
]


# ── Load templates from JSON ──────────────────────────────────────────────────
def get_templates() -> dict:
    path = _ROOT / "data" / "templates.json"
    if not path.exists():
        # Fallback default templates if file doesn't exist yet
        return {
            "day1": {
                "subject": "Great connecting with you at {{expo_name}}",
                "body": (
                    "Hi {{firstname}},\n\n"
                    "It was great meeting you at {{expo_name}}.\n\n"
                    "We specialize in {{lead_type}} solutions — helping businesses "
                    "with reliable supply and competitive pricing.\n\n"
                    "I have attached our brochure for reference.\n\n"
                    "Would you be open to a quick conversation?\n\n"
                    "Best,\nAditi"
                )
            },
            "day3": {
                "subject": "Re: Great connecting with you at {{expo_name}}",
                "body": (
                    "Hi {{firstname}},\n\n"
                    "Just following up in case my last note got buried.\n\n"
                    "We recently worked with a buyer in Iraq who reached out after "
                    "an expo. Within one month we had a container shipped and delivered. "
                    "Their second order is already in progress.\n\n"
                    "Worth a quick reply?\n\n"
                    "Best,\nAditi"
                )
            },
            "day7": {
                "subject": "Re: Great connecting with you at {{expo_name}}",
                "body": (
                    "Hi {{firstname}},\n\n"
                    "I wanted to follow up from a different angle.\n\n"
                    "Most conversations we have fall into one of these:\n\n"
                    "- Bulk Liquid — container level purchasing\n"
                    "- Private Label — custom brand, custom formula\n"
                    "- General sourcing — evaluating options\n\n"
                    "Just reply with whichever fits.\n\n"
                    "Best,\nAditi"
                )
            },
            "day14": {
                "subject": "Re: Great connecting with you at {{expo_name}}",
                "body": (
                    "Hi {{firstname}},\n\n"
                    "I have reached out a few times so I will keep this short.\n\n"
                    "If timing was not right before, no problem — just let me know "
                    "and I will check back in a few months.\n\n"
                    "If you are still evaluating, I am happy to help.\n\n"
                    "Best,\nAditi"
                )
            },
            "day21": {
                "subject": "Re: Great connecting with you at {{expo_name}}",
                "body": (
                    "Hi {{firstname}},\n\n"
                    "This will be my last note for now.\n\n"
                    "If the timing is not right, no worries at all. "
                    "I will circle back in a few months.\n\n"
                    "If you ever want to explore options for {{lead_type}}, "
                    "my contact is always open.\n\n"
                    "Wishing you all the best.\n\n"
                    "Best,\nAditi"
                )
            }
        }
    with open(path) as f:
        return json.load(f)


# ── Fill template tokens ──────────────────────────────────────────────────────
def fill_template(text: str, contact: dict) -> str:
    return (
        text
        .replace("{{firstname}}",  contact.get("firstname", "there"))
        .replace("{{expo_name}}",  contact.get("expo_name", "the expo"))
        .replace("{{lead_type}}",  contact.get("lead_type", ""))
        .replace("{{company}}",    contact.get("company", ""))
    )


# ── HubSpot helpers ───────────────────────────────────────────────────────────
def get_hubspot_client():
    return hubspot.Client.create(access_token=os.getenv("HUBSPOT_API_KEY"))


def get_contact(client, email: str) -> dict | None:
    """Fetch contact from HubSpot by email."""
    try:
        result = client.crm.contacts.basic_api.get_by_id(
            contact_id=email,
            id_property="email",
            properties=[
                "firstname", "lastname", "email",
                "expo_name", "lead_type", "lead_status", "company"
            ]
        )
        p = result.properties
        return {
            "id":          result.id,
            "firstname":   p.get("firstname", ""),
            "lastname":    p.get("lastname", ""),
            "email":       p.get("email", email),
            "expo_name":   p.get("expo_name", "the expo"),
            "lead_type":   p.get("lead_type", ""),
            "lead_status": p.get("lead_status", "New"),
            "company":     p.get("company", ""),
        }
    except ApiException as e:
        if e.status == 404:
            log.error(f"Contact not found in HubSpot: {email}")
            log.error("Make sure you ran import_contacts.py first")
        else:
            log.error(f"HubSpot error fetching {email}: {e.reason}")
        return None


def update_lead_status(client, contact_id: str, status: str, email_num: int = None) -> None:
    """
    Update hs_lead_status (HubSpot built-in Lead Status property) and
    optionally email_sequence_day after each email send.

    hs_lead_status accepted values (already configured in HubSpot):
      New, Contacted, Followed-up-1, Followed-up-2, Followed-up-3,
      Replied, Stalled, Re-engaged, Cold, Archived

    Strategy: update hs_lead_status first (always works), then try
    email_sequence_day separately (may not exist yet — non-fatal).
    """
    # Step 1: Update hs_lead_status (always works — built-in property)
    try:
        client.crm.contacts.basic_api.update(
            contact_id=contact_id,
            simple_public_object_input=SimplePublicObjectInput(
                properties={"hs_lead_status": status}
            )
        )
        log.info(f"  [OK] HubSpot hs_lead_status → {status}")
    except ApiException as e:
        log.error(f"  [ERR] hs_lead_status update failed: {e.reason}")

    # Step 2: Update email_sequence_day (custom property — may not exist yet)
    if email_num is not None:
        try:
            client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=SimplePublicObjectInput(
                    properties={"email_sequence_day": str(email_num)}
                )
            )
            log.info(f"  [OK] HubSpot email_sequence_day → {email_num}")
        except ApiException as e:
            log.warning(f"  [WARN] email_sequence_day update failed (property may not exist): {e.reason}")
            log.warning(f"  [WARN] Run: venv\\Scripts\\python backend\\setup\\setup_hubspot_properties.py")


def log_email_to_hubspot(
    client, contact: dict, subject: str, body: str,
    gmail_id: str, thread_id: str = None
) -> None:
    """
    Log the sent email as an EMAIL engagement on the HubSpot contact record.
    This is what makes HubSpot aware of the email so it can track replies.

    Includes threadId in metadata so HubSpot can link the Gmail thread.
    Uses HubSpot Engagements API v1 (still supported for email logging).
    """
    import requests
    token = os.getenv("HUBSPOT_API_KEY", "")
    url   = "https://api.hubapi.com/engagements/v1/engagements"
    metadata = {
        "from": {
            "email":     SENDER,
            "firstName": "Aditi",
            "lastName":  "Rajput",
        },
        "to":      [{"email": contact["email"]}],
        "cc":      [],
        "bcc":     [],
        "subject": subject,
        "text":    body,
        "html":    body.replace("\n", "<br>"),
    }
    # Include Gmail threadId so HubSpot can link the thread
    if thread_id:
        metadata["threadId"] = thread_id

    payload = {
        "engagement": {
            "active":    True,
            "type":      "EMAIL",
            "timestamp": int(datetime.now().timestamp() * 1000),
        },
        "associations": {
            "contactIds": [int(contact["id"])],
            "companyIds": [],
            "dealIds":    [],
            "ownerIds":   [],
        },
        "metadata": metadata,
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            eng_id = resp.json().get("engagement", {}).get("id", "?")
            log.info(f"  [OK] Email logged to HubSpot -- Engagement ID: {eng_id}")
        else:
            log.warning(f"  [WARN] HubSpot email log failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log.warning(f"  [WARN] Could not log email to HubSpot: {e}")


def create_deal(client, contact: dict) -> None:
    """Create a deal in HubSpot when lead replies."""
    try:
        from hubspot.crm.deals import SimplePublicObjectInputForCreate as DealInput
        from hubspot.crm.associations import BatchInputPublicAssociation, PublicAssociation
        company   = contact.get("company", "Unknown")
        lead_type = contact.get("lead_type", "General")
        deal = client.crm.deals.basic_api.create(
            simple_public_object_input_for_create=DealInput(
                properties={
                    "dealname":  f"{company} - {lead_type}",
                    "dealstage": "appointmentscheduled",
                    "pipeline":  "default",
                }
            )
        )
        # Associate deal with contact using v3 associations API
        try:
            client.crm.associations.batch_api.create(
                from_object_type="deals",
                to_object_type="contacts",
                batch_input_public_association=BatchInputPublicAssociation(
                    inputs=[PublicAssociation(
                        _from={"id": deal.id},
                        to={"id": contact["id"]},
                        type="deal_to_contact"
                    )]
                )
            )
            log.info(f"  [OK] Deal associated with contact")
        except Exception as assoc_err:
            log.warning(f"  [WARN] Deal created but association failed: {assoc_err}")
        log.info(f"  [OK] Deal created in HubSpot -- ID: {deal.id}")
    except Exception as e:
        log.error(f"  [ERR] Failed to create deal: {e}")


def check_for_reply(service, thread_id: str, our_email: str = "") -> bool:
    """
    Check if the lead replied on the email thread.
    Detects a reply by finding a message NOT sent by us in the thread.
    This is more reliable than counting messages.
    """
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="metadata",
            metadataHeaders=["From"]
        ).execute()
        messages = thread.get("messages", [])
        for msg in messages:
            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            sender = headers.get("From", "")
            # If a message was NOT sent by us → it's a reply
            if our_email and our_email.lower() not in sender.lower():
                return True
            elif not our_email and sender:
                # Fallback: count > 1 if no sender provided
                return len(messages) > 1
        return False
    except HttpError as e:
        log.warning(f"Could not check thread for replies: {e}")
        return False


# ── Gmail helpers ─────────────────────────────────────────────────────────────
def get_gmail_service():
    # Try email_setup folder first, then setup folder
    try:
        from gmail_setup import get_gmail_service as _get
        return _get()
    except ImportError:
        pass
    try:
        import importlib.util
        for folder in [_EMAIL_SETUP, _SETUP]:
            p = folder / "gmail_setup.py"
            if p.exists():
                spec = importlib.util.spec_from_file_location("gmail_setup", p)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.get_gmail_service()
        raise FileNotFoundError("gmail_setup.py not found in email_setup/ or setup/")
    except Exception as e:
        log.error(f"Could not load Gmail service: {e}")
        raise


def send_email(
    service,
    to: str,
    subject: str,
    body: str,
    thread_id: str = None,
    message_id: str = None
) -> dict:
    """
    Send email via Gmail API.
    If thread_id provided — sends as reply on same thread.
    Returns dict with messageId and threadId.
    """
    msg = MIMEMultipart()
    msg["to"]      = to
    msg["from"]    = SENDER
    msg["subject"] = subject

    # For threading — add In-Reply-To and References headers
    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"]  = message_id

    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    result = service.users().messages().send(
        userId="me",
        body=send_body
    ).execute()

    # Fetch the sent message to get its Message-ID header for threading
    sent = service.users().messages().get(
        userId="me",
        id=result["id"],
        format="metadata",
        metadataHeaders=["Message-ID"]
    ).execute()

    headers   = {h["name"]: h["value"] for h in sent.get("payload", {}).get("headers", [])}
    msg_id    = headers.get("Message-ID", "")
    thread_id = result.get("threadId", "")

    return {"message_id": msg_id, "thread_id": thread_id, "gmail_id": result["id"]}


# ── Main sequence ─────────────────────────────────────────────────────────────
def run_test_sequence(email: str) -> None:
    """
    Runs the full 4-email test sequence for one contact.
    Emails fire every 15 minutes.
    HubSpot status updates automatically after each send.
    """
    log.info(f"\n{'='*55}")
    log.info(f"TEST SEQUENCE STARTING: {email}")
    log.info(f"Interval: {TEST_INTERVAL_MINUTES} minutes between emails")
    log.info(f"{'='*55}\n")

    hs_client  = get_hubspot_client()
    gmail      = get_gmail_service()
    templates  = get_templates()

    # Fetch contact from HubSpot
    contact = get_contact(hs_client, email)
    if not contact:
        log.error(f"Skipping {email} — not found in HubSpot")
        return

    log.info(f"Contact loaded: {contact['firstname']} {contact['lastname']}")
    log.info(f"Current status: {contact['lead_status']}")

    thread_id  = None
    message_id = None
    days       = ["day1", "day3", "day7", "day14", "day21"]
    labels     = ["Email 1 - Intro", "Email 2 - Follow-1",
                  "Email 3 - Follow-2", "Email 4 - Follow-3",
                  "Email 5 - Final Nudge"]

    for i, (day, label) in enumerate(zip(days, labels)):
        log.info(f"\n--- Sending {label} ---")

        # Check for reply before sending (skip Day 1 — no thread yet)
        if thread_id and check_for_reply(gmail, thread_id, SENDER):
            log.info(f"[REPLY] REPLY DETECTED -- stopping sequence for {email}")
            update_lead_status(hs_client, contact["id"], "Replied")
            create_deal(hs_client, contact)
            log.info("Deal created in HubSpot pipeline")
            return

        # Get and fill template
        tmpl    = templates[day]
        subject = fill_template(tmpl["subject"], contact)
        body    = fill_template(tmpl["body"], contact)

        # Send email via Gmail API
        try:
            result     = send_email(gmail, email, subject, body, thread_id, message_id)
            thread_id  = result["thread_id"]
            message_id = result["message_id"]
            log.info(f"  [OK] Email sent -- Gmail ID: {result['gmail_id']}")
            log.info(f"  [THREAD] Thread ID: {thread_id}")
            log.info(f"  Subject: {subject}")
        except Exception as e:
            log.error(f"  [ERR] Failed to send email: {e}")
            return

        # Log email to HubSpot contact record (so HubSpot can track replies)
        log_email_to_hubspot(hs_client, contact, subject, body, result["gmail_id"], thread_id)

        # Update HubSpot status (email_num = i+1 so Email 1 = 1, Email 2 = 2, etc.)
        new_status = STATUS_MAP[i]
        update_lead_status(hs_client, contact["id"], new_status, email_num=i + 1)

        # Wait before next email (skip wait after last email)
        if i < len(days) - 1:
            wait_seconds = TEST_INTERVAL_MINUTES * 60
            next_send    = datetime.now().strftime("%H:%M:%S")
            log.info(f"\n  [WAIT] Waiting {TEST_INTERVAL_MINUTES} mins before next email...")
            log.info(f"  Next email at: {next_send} + {TEST_INTERVAL_MINUTES} mins")

            # Countdown -- checks for reply every 60 seconds during wait
            for remaining in range(wait_seconds, 0, -60):
                time.sleep(min(60, remaining))
                if thread_id and check_for_reply(gmail, thread_id, SENDER):
                    log.info(f"\n  [REPLY] REPLY DETECTED DURING WAIT -- stopping sequence")
                    update_lead_status(hs_client, contact["id"], "Replied")
                    create_deal(hs_client, contact)
                    return
                mins_left = remaining // 60
                if mins_left > 0:
                    log.info(f"  [WAIT] {mins_left} min remaining...")

    # All 5 emails sent — no reply
    log.info(f"\n{'='*55}")
    log.info(f"SEQUENCE COMPLETE -- no reply from {email}")
    log.info(f"Setting Lead Status: Cold")
    update_lead_status(hs_client, contact["id"], "Cold")
    log.info(f"{'='*55}\n")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CRM Test Sequence Runner")
    parser.add_argument("--email", help="Run sequence for one specific email")
    parser.add_argument("--all",   action="store_true",
                        help="Run sequence for all yopmail test contacts")
    args = parser.parse_args()

    if args.all:
        log.info(f"Running test sequence for {len(TEST_CONTACTS)} contacts...")
        for contact_email in TEST_CONTACTS:
            run_test_sequence(contact_email)
            log.info(f"\nWaiting 2 minutes before next contact...\n")
            time.sleep(120)

    elif args.email:
        run_test_sequence(args.email)

    else:
        # Default — run for first yopmail contact
        log.info("No email specified — running for test.bulk.new@yopmail.com")
        log.info("Use --email your@email.com or --all for multiple contacts\n")
        run_test_sequence("test.bulk.new@yopmail.com")