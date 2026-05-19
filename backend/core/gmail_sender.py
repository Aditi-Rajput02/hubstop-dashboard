"""
Gmail Sender — Phase 3
Sends plain-text emails via Gmail API.
Supports same-thread replies using threadId + In-Reply-To + References headers.
No tracking pixels. No HTML. No unsubscribe footer.
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
import logging
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from gmail_setup import get_gmail_service

from pathlib import Path as _Path
load_dotenv(_Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("GMAIL_SENDER", "")


# ── Build a plain-text MIME message ──────────────────────────────────────────

def _build_message(
    to: str,
    subject: str,
    body: str,
    message_id: str | None = None,   # Message-ID of the first email in thread
    references: str | None = None,   # Full References header chain
) -> MIMEMultipart:
    """
    Builds a MIME message.
    When message_id is provided the email is threaded as a reply:
      - In-Reply-To  = message_id
      - References   = references or message_id
    """
    msg = MIMEMultipart("alternative")
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to
    msg["Subject"] = subject

    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"]  = references if references else message_id

    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def _encode(msg: MIMEMultipart) -> str:
    """Base64url-encode a MIME message for the Gmail API."""
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


# ── Send a new email (Day 1 — starts the thread) ─────────────────────────────

def send_new_email(
    to: str,
    subject: str,
    body: str,
) -> dict:
    """
    Sends a brand-new email (no thread).
    Returns Gmail API message resource dict:
      { "id": "...", "threadId": "...", "labelIds": [...] }
    """
    service = get_gmail_service()
    msg     = _build_message(to, subject, body)
    raw     = _encode(msg)

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    log.info(f"Sent Day-1 email → {to} | msgId={result['id']} threadId={result['threadId']}")
    return result


# ── Send a reply on the same thread (Day 3 / 7 / 14) ─────────────────────────

def send_reply(
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    message_id: str,
    references: str | None = None,
) -> dict:
    """
    Sends a reply on an existing Gmail thread.

    Args:
        to          : recipient email address
        subject     : email subject (should start with "Re: ...")
        body        : plain-text body
        thread_id   : Gmail threadId from the Day-1 send result
        message_id  : Message-ID header of the previous email in the thread
        references  : Full References header chain (optional; built from message_id if omitted)

    Returns:
        Gmail API message resource dict
    """
    service = get_gmail_service()
    msg     = _build_message(to, subject, body, message_id=message_id, references=references)
    raw     = _encode(msg)

    result = service.users().messages().send(
        userId="me",
        body={
            "raw":      raw,
            "threadId": thread_id,   # keeps the reply in the same thread
        }
    ).execute()

    log.info(
        f"Sent reply → {to} | msgId={result['id']} "
        f"threadId={result['threadId']}"
    )
    return result


# ── Fetch the Message-ID header of a sent message ────────────────────────────

def get_message_id_header(gmail_msg_id: str) -> str | None:
    """
    Fetches the RFC-2822 Message-ID header for a Gmail message.
    This is needed to set In-Reply-To on the next email in the thread.

    Args:
        gmail_msg_id : the 'id' field from the Gmail API send response

    Returns:
        The Message-ID header string (e.g. '<abc123@mail.gmail.com>')
        or None if not found.
    """
    service = get_gmail_service()
    msg = service.users().messages().get(
        userId="me",
        id=gmail_msg_id,
        format="metadata",
        metadataHeaders=["Message-ID"],
    ).execute()

    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "message-id":
            return h["value"]
    return None


# ── Check if a contact has replied to our thread ─────────────────────────────

def contact_has_replied(thread_id: str, our_email: str = SENDER_EMAIL) -> bool:
    """
    Returns True if anyone OTHER than our sender has sent a message
    in the given Gmail thread (i.e. the contact replied).

    Args:
        thread_id : Gmail threadId to inspect
        our_email : the sender's Gmail address (defaults to GMAIL_SENDER env var)

    Returns:
        True if a reply from the contact exists, False otherwise.
    """
    service = get_gmail_service()
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="metadata",
            metadataHeaders=["From"],
        ).execute()
    except Exception as e:
        log.warning(f"Could not fetch thread {thread_id}: {e}")
        return False

    # Addresses to ignore — these are automated/system senders, not real replies
    IGNORE_SENDERS = [
        "mailer-daemon",
        "postmaster",
        "noreply",
        "no-reply",
        "googlemail.com",
        "bounce",
        "delivery",
    ]

    messages = thread.get("messages", [])
    for msg in messages:
        headers = msg.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"].lower() == "from":
                sender = h["value"].lower()
                # Skip our own sent messages
                if our_email.lower() in sender:
                    continue
                # Skip automated bounce/delivery notifications
                if any(ignore in sender for ignore in IGNORE_SENDERS):
                    log.debug(f"Ignoring automated sender in thread {thread_id}: {h['value']}")
                    continue
                # Real reply from the lead
                log.info(f"Reply detected in thread {thread_id} from: {h['value']}")
                return True
    return False


# ── Get the timestamp of the last message in a thread ────────────────────────

def get_last_message_timestamp(thread_id: str) -> int | None:
    """
    Returns the internalDate (Unix ms) of the most recent message in a thread.
    Used to detect stalled conversations.

    Args:
        thread_id : Gmail threadId

    Returns:
        internalDate in milliseconds, or None on error.
    """
    service = get_gmail_service()
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id,
            format="minimal",
        ).execute()
        messages = thread.get("messages", [])
        if not messages:
            return None
        # messages are in chronological order; last is most recent
        return int(messages[-1].get("internalDate", 0))
    except Exception as e:
        log.warning(f"Could not get last message timestamp for thread {thread_id}: {e}")
        return None
