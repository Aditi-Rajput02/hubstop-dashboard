"""
Sequence Runner — Phase 3 Core Orchestrator
Ties together Gmail sender, HubSpot CRM, throttle, and templates.

What this module does on each run:
  1. Send Day-1 emails to contacts whose expo_followup_date == today
  2. Send Day-3 / 7 / 14 follow-ups to contacts mid-sequence
  3. Detect replies → stop sequence, mark replied in HubSpot
  4. Detect stalled conversations → send re-engagement email
  5. Archive contacts after Day-14 with no reply

All sends are throttled: business hours only, daily cap, random delays.
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


import logging
import os
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

import hubspot_crm   as crm
import gmail_sender  as gmail
import email_throttle as throttle
from email_templates import get_template, stalled_reengage, SEQUENCE_DAYS

load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

log = logging.getLogger(__name__)

STALLED_DAYS = int(os.getenv("STALLED_DAYS", 14))  # days of silence before re-engage


# Step → calendar day label for logging
STEP_LABEL = {1: "Day-1", 2: "Day-3", 3: "Day-7", 4: "Day-14"}
# Step → template day number (used by get_template)
STEP_TO_TEMPLATE_DAY = {1: 1, 2: 3, 3: 7, 4: 14}


# ── Single-contact send helper ────────────────────────────────────────────────

def _send_sequence_email(
    hs_client,
    contact: dict,
    step: int,
) -> bool:
    """
    Sends one sequence email for a contact.

    step 1 → Day-1  (new thread)  → hs_lead_status = Contacted
    step 2 → Day-3  (reply)       → hs_lead_status = Followed-up-1
    step 3 → Day-7  (reply)       → hs_lead_status = Followed-up-2
    step 4 → Day-14 (reply)       → hs_lead_status = Followed-up-3 + complete

    Returns True on success, False on failure.
    """
    email_addr   = contact.get("email", "")
    contact_id   = contact.get("hs_object_id", "")
    lead_type    = (contact.get("lead_type") or "general").lower()
    thread_id    = contact.get("email_thread_id", "")
    last_msg_id  = contact.get("email_last_message_id", "")
    references   = contact.get("email_references", "")
    template_day = STEP_TO_TEMPLATE_DAY.get(step, 1)

    if not email_addr:
        log.warning(f"Contact {contact_id}: no email address — skipping")
        return False

    ok, reason = throttle.can_send_now()
    if not ok:
        log.info(f"Throttle blocked send for {email_addr}: {reason}")
        return False

    try:
        subject, body = get_template(template_day, lead_type, contact)
    except ValueError as e:
        log.error(f"Template error for {email_addr}: {e}")
        return False

    try:
        if step == 1 or not thread_id:
            result = gmail.send_new_email(email_addr, subject, body)
        else:
            result = gmail.send_reply(
                to=email_addr,
                subject=subject,
                body=body,
                thread_id=thread_id,
                message_id=last_msg_id,
                references=references,
            )

        new_msg_id     = gmail.get_message_id_header(result["id"]) or result["id"]
        new_references = f"{references} {new_msg_id}".strip() if references else new_msg_id

        crm.mark_sequence_day_sent(
            hs_client,
            contact_id,
            step=step,
            thread_id=result["threadId"],
            last_message_id=new_msg_id,
            references=new_references,
        )

        crm.log_email_engagement(hs_client, contact_id, subject, body, email_addr)
        throttle.record_send()

        log.info(
            f"✅ {STEP_LABEL.get(step, f'Step-{step}')} sent → {email_addr} "
            f"(thread={result['threadId'][:12]}...)"
        )
        return True

    except Exception as e:
        log.error(f"❌ Failed to send step-{step} to {email_addr}: {e}")
        return False


# ── Step 1: Day-1 emails for contacts due today ───────────────────────────────

def run_day1_sends(hs_client) -> dict:
    """
    Sends Day-1 (step 1) emails to all contacts whose:
      - expo_followup_date == today
      - hs_lead_status == "New"  (or not yet set)
      - email_sequence_day == 0  (not yet started)
    """
    contacts = crm.get_contacts_due_today(hs_client)
    summary  = {"attempted": 0, "sent": 0, "skipped": 0, "throttled": 0}

    for contact in contacts:
        lead_status = (contact.get("hs_lead_status") or "New").strip()
        seq_step    = int(contact.get("email_sequence_day") or 0)

        # Only send Day-1 to truly new contacts
        if seq_step > 0 or lead_status not in ("New", ""):
            log.debug(
                f"Contact {contact.get('email')}: already at step {seq_step} "
                f"/ status={lead_status} — skip Day-1"
            )
            summary["skipped"] += 1
            continue

        summary["attempted"] += 1
        ok, reason = throttle.can_send_now()
        if not ok:
            log.info(f"Throttle: stopping Day-1 batch — {reason}")
            summary["throttled"] += (len(contacts) - summary["attempted"] - summary["skipped"])
            break

        sent = _send_sequence_email(hs_client, contact, step=1)
        if sent:
            summary["sent"] += 1
            throttle.random_delay()
        else:
            summary["skipped"] += 1

    log.info(f"Day-1 batch: {summary}")
    return summary


# ── Step 2: Follow-up emails (Day 3 / 7 / 14) ────────────────────────────────

# Days offset from expo_followup_date (Day 1) when each step becomes due.
# Using fixed offsets from Day 1 is immune to spurious hs_lastmodifieddate updates.
#   step 1 sent on Day 1  (expo_followup_date + 0)
#   step 2 due  on Day 3  (expo_followup_date + 2)
#   step 3 due  on Day 7  (expo_followup_date + 6)
#   step 4 due  on Day 14 (expo_followup_date + 13)
STEP_DUE_OFFSET_DAYS = {
    2: 2,    # step 2 (Day-3)  is due 2 days after Day 1
    3: 6,    # step 3 (Day-7)  is due 6 days after Day 1
    4: 13,   # step 4 (Day-14) is due 13 days after Day 1
}

# Fallback: minimum days since hs_lastmodifieddate if expo_followup_date is missing
DAYS_BETWEEN_STEPS = {
    1: 2,
    2: 4,
    3: 7,
}


def run_followup_sends(hs_client) -> dict:
    """
    Sends the next follow-up to all mid-sequence contacts whose next step is due.

    Step mapping:
      step 1 (Contacted)     → step 2 after 2 days from Day 1  → hs_lead_status = Followed-up-1
      step 2 (Followed-up-1) → step 3 after 6 days from Day 1  → hs_lead_status = Followed-up-2
      step 3 (Followed-up-2) → step 4 after 13 days from Day 1 → hs_lead_status = Followed-up-3 + Cold

    Due-date is calculated from expo_followup_date (Day 1) + fixed offset.
    This is immune to spurious hs_lastmodifieddate updates caused by CRM writes,
    throttle syncs, or HubSpot UI edits.
    """
    contacts = crm.get_active_sequence_contacts(hs_client)
    summary  = {"attempted": 0, "sent": 0, "skipped": 0, "throttled": 0}
    today    = datetime.now(timezone.utc).date()

    for contact in contacts:
        email_addr   = contact.get("email", "")
        contact_id   = contact.get("hs_object_id", "")
        current_step = int(contact.get("email_sequence_day") or 0)

        if current_step not in DAYS_BETWEEN_STEPS:
            # step 4 already sent — sequence complete
            log.debug(f"{email_addr}: no next step after step {current_step}")
            summary["skipped"] += 1
            continue

        next_step = current_step + 1

        # ── Primary: use expo_followup_date + fixed offset ────────────────────
        followup_date_str = contact.get("expo_followup_date", "")
        step_due = None

        if followup_date_str:
            try:
                # HubSpot stores date props as "YYYY-MM-DD" or as ms timestamp
                if followup_date_str.isdigit():
                    # milliseconds → date
                    day1 = datetime.fromtimestamp(
                        int(followup_date_str) / 1000, tz=timezone.utc
                    ).date()
                else:
                    day1 = datetime.fromisoformat(
                        followup_date_str.split("T")[0]
                    ).date()

                offset = STEP_DUE_OFFSET_DAYS.get(next_step, 0)
                step_due = day1 + timedelta(days=offset)

                if today < step_due:
                    log.debug(
                        f"{email_addr}: step {next_step} not due yet "
                        f"(due {step_due}, today {today})"
                    )
                    summary["skipped"] += 1
                    continue

                log.debug(
                    f"{email_addr}: step {next_step} due on {step_due} — "
                    f"today is {today} ✓ proceeding"
                )

            except (ValueError, OSError) as e:
                log.warning(
                    f"{email_addr}: could not parse expo_followup_date "
                    f"'{followup_date_str}': {e} — falling back to hs_lastmodifieddate"
                )
                step_due = None  # fall through to fallback

        # ── Fallback: use hs_lastmodifieddate if expo_followup_date missing ──
        if step_due is None:
            days_needed = DAYS_BETWEEN_STEPS[current_step]
            last_modified_str = contact.get("hs_lastmodifieddate", "")
            if last_modified_str:
                try:
                    last_modified = datetime.fromisoformat(
                        last_modified_str.replace("Z", "+00:00")
                    )
                    days_since = (datetime.now(timezone.utc) - last_modified).days
                    if days_since < days_needed:
                        log.debug(
                            f"{email_addr}: step {next_step} not due yet "
                            f"(fallback: {days_since}/{days_needed} days since last modified)"
                        )
                        summary["skipped"] += 1
                        continue
                except ValueError:
                    pass

        summary["attempted"] += 1
        ok, reason = throttle.can_send_now()
        if not ok:
            log.info(f"Throttle: stopping follow-up batch — {reason}")
            summary["throttled"] += 1
            break

        sent = _send_sequence_email(hs_client, contact, step=next_step)
        if sent:
            summary["sent"] += 1
            # After step 4 (Day-14), mark as Cold if no reply
            if next_step == 4:
                crm.mark_archived(hs_client, contact_id)
            throttle.random_delay()
        else:
            summary["skipped"] += 1

    log.info(f"Follow-up batch: {summary}")
    return summary


# ── Step 3: Reply detection — stop sequence if contact replied ────────────────

def run_reply_check(hs_client) -> int:
    """
    Checks all active-sequence contacts for replies.
    If a reply is detected, marks the contact as replied in HubSpot
    (which stops the sequence on the next run).

    Returns the number of new replies detected.
    """
    contacts     = crm.get_active_sequence_contacts(hs_client)
    reply_count  = 0

    for contact in contacts:
        thread_id  = contact.get("email_thread_id", "")
        contact_id = contact.get("hs_object_id", "")
        email_addr = contact.get("email", "")

        if not thread_id:
            continue

        if gmail.contact_has_replied(thread_id):
            crm.mark_replied(hs_client, contact_id)
            reply_count += 1
            log.info(f"Reply detected: {email_addr} — sequence stopped")
            # Auto-create a deal in HubSpot pipeline (non-fatal)
            try:
                deal_id = crm.create_deal_for_contact(hs_client, contact)
                if deal_id:
                    log.info(f"Deal auto-created for {email_addr}: id={deal_id}")
            except Exception as deal_err:
                log.warning(f"Deal creation skipped for {email_addr}: {deal_err}")

    if reply_count:
        log.info(f"Reply check: {reply_count} new replies detected")
    return reply_count


# ── Step 4: Stalled conversation detection ───────────────────────────────────

def run_stalled_check(hs_client) -> int:
    """
    Checks contacts that have replied but whose conversation has gone quiet
    for STALLED_DAYS days. Sends a re-engagement email on the same thread.

    Returns the number of stalled re-engagements sent.
    """
    contacts      = crm.get_replied_contacts(hs_client)
    stalled_count = 0

    for contact in contacts:
        thread_id  = contact.get("email_thread_id", "")
        contact_id = contact.get("hs_object_id", "")
        email_addr = contact.get("email", "")

        if not thread_id:
            continue

        # Get timestamp of last message in thread
        last_ts_ms = gmail.get_last_message_timestamp(thread_id)
        if last_ts_ms is None:
            continue

        last_dt      = datetime.fromtimestamp(last_ts_ms / 1000, tz=timezone.utc)
        days_silent  = (datetime.now(timezone.utc) - last_dt).days

        if days_silent < STALLED_DAYS:
            log.debug(
                f"{email_addr}: conversation active "
                f"({days_silent}/{STALLED_DAYS} days silent)"
            )
            continue

        # Conversation has stalled — send re-engagement on same thread
        ok, reason = throttle.can_send_now()
        if not ok:
            log.info(f"Throttle: stopping stalled check — {reason}")
            break

        subject, body = stalled_reengage(contact)
        last_msg_id   = contact.get("email_last_message_id", "")
        references    = contact.get("email_references", "")

        try:
            result = gmail.send_reply(
                to=email_addr,
                subject=subject,
                body=body,
                thread_id=thread_id,
                message_id=last_msg_id,
                references=references,
            )
            crm.mark_stalled_sent(hs_client, contact_id)
            crm.log_email_engagement(hs_client, contact_id, subject, body, email_addr)
            throttle.record_send()
            stalled_count += 1
            log.info(
                f"Stalled re-engage sent → {email_addr} "
                f"({days_silent} days silent)"
            )
            throttle.random_delay()
        except Exception as e:
            log.error(f"Failed stalled re-engage for {email_addr}: {e}")

    if stalled_count:
        log.info(f"Stalled check: {stalled_count} re-engagements sent")
    return stalled_count


# ── Full run — called by the scheduler ───────────────────────────────────────

def run_all(hs_client=None) -> dict:
    """
    Runs the complete sequence cycle:
      1. Reply check (fast, no sends)
      2. Stalled check
      3. Day-1 sends for new contacts
      4. Follow-up sends for mid-sequence contacts

    Returns a summary dict.
    """
    if hs_client is None:
        hs_client = crm.get_client()

    log.info("=" * 60)
    log.info(f"Sequence run started — {datetime.now(timezone.utc).isoformat()}")
    status = throttle.get_status()
    log.info(
        f"Throttle status: window={'OPEN' if status['window_open'] else 'CLOSED'} | "
        f"sent={status['sent_today']}/{status['daily_cap']} | "
        f"warmup day {status['warmup_day']} | "
        f"sender time {status['sender_time']}"
    )

    if not throttle.is_send_window_open():
        log.info("Send window is closed — skipping sends (reply/stalled checks still run)")

    replies  = run_reply_check(hs_client)
    stalled  = run_stalled_check(hs_client)
    day1     = run_day1_sends(hs_client)
    followup = run_followup_sends(hs_client)

    summary = {
        "run_at":          datetime.now(timezone.utc).isoformat(),
        "replies_detected": replies,
        "stalled_sent":    stalled,
        "day1":            day1,
        "followup":        followup,
    }
    log.info(f"Sequence run complete: {summary}")
    log.info("=" * 60)
    return summary
