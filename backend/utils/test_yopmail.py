"""
Yopmail Test Script
Pulls contacts from HubSpot, filters for yopmail addresses,
and sends Day 1 test emails to each one.

Usage:
    venv\Scripts\python test_yopmail.py

Then check: https://yopmail.com -> enter each email address
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
import requests
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

from gmail_sender import send_new_email, get_message_id_header
from email_templates import get_template

# ── HubSpot contact fetcher ───────────────────────────────────────────────────

def get_hubspot_contacts():
    """
    Fetches contacts from HubSpot CRM including all custom sequence properties.
    Returns a list of property dicts.
    """
    token = os.getenv("HUBSPOT_API_KEY")
    if not token:
        raise ValueError("HUBSPOT_API_KEY not set in .env")

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "limit": 100,
        "properties": ",".join([
            "firstname", "lastname", "email", "phone", "company",
            "lead_type", "expo_name", "expo_followup_date",
            "email_sequence_day", "email_thread_id",
            "email_last_message_id", "email_references",
            "email_replied", "email_sequence_complete",
        ])
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"HubSpot API error {response.status_code}: {response.text}")

    data = response.json()
    contacts = []

    for result in data.get("results", []):
        props = result["properties"]
        props["hs_object_id"] = result["id"]   # HubSpot contact ID
        contacts.append(props)

    return contacts


def filter_yopmail(contacts: list) -> list:
    """Returns only contacts with a yopmail.com email address."""
    return [c for c in contacts if "yopmail.com" in (c.get("email") or "").lower()]


# ── Send Day 1 to each yopmail contact ───────────────────────────────────────

def run_test():
    print("=" * 60)
    print("Fetching contacts from HubSpot...")
    print("=" * 60)

    try:
        all_contacts = get_hubspot_contacts()
    except Exception as e:
        print(f"FAILED to fetch HubSpot contacts: {e}")
        return

    print(f"Total contacts fetched : {len(all_contacts)}")

    yopmail_contacts = filter_yopmail(all_contacts)
    print(f"Yopmail contacts found : {len(yopmail_contacts)}")

    if not yopmail_contacts:
        print("\nNo yopmail contacts found in HubSpot.")
        print("Add contacts with @yopmail.com emails in HubSpot first,")
        print("or use the hardcoded test contacts below by editing TEST_CONTACTS.")
        return

    print("\nYopmail contacts:")
    for c in yopmail_contacts:
        name      = f"{c.get('firstname','')} {c.get('lastname','')}".strip() or "(no name)"
        email     = c.get("email")
        lead_type = c.get("lead_type") or "General"
        expo      = c.get("expo_name") or "the expo"
        print(f"  {name:20s}  {email:35s}  lead_type={lead_type}  expo={expo}")

    print("\n" + "=" * 60)
    print("Sending Day 1 emails...")
    print("=" * 60)

    results = []

    for contact in yopmail_contacts:
        email     = contact.get("email", "")
        lead_type = contact.get("lead_type") or "General"
        day       = 1

        print(f"\nSending to: {email}  (lead_type={lead_type})")

        try:
            subject, body = get_template(day, lead_type, contact)
            print(f"  Subject : {subject}")

            result = send_new_email(
                to      = email,
                subject = subject,
                body    = body,
            )

            msg_id     = result.get("id")
            thread_id  = result.get("threadId")
            rfc_msg_id = get_message_id_header(msg_id)

            print(f"  SENT OK")
            print(f"  Gmail msg ID : {msg_id}")
            print(f"  Thread ID    : {thread_id}")
            print(f"  RFC Msg-ID   : {rfc_msg_id}")

            results.append({
                "email":      email,
                "status":     "OK",
                "msg_id":     msg_id,
                "thread_id":  thread_id,
                "rfc_msg_id": rfc_msg_id,
            })

        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"email": email, "status": "FAILED", "error": str(e)})

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    ok     = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] == "FAILED"]
    print(f"  Sent    : {len(ok)}")
    print(f"  Failed  : {len(failed)}")

    if ok:
        print("\nCheck these inboxes at https://yopmail.com :")
        for r in ok:
            print(f"  -> {r['email']}")

    if failed:
        print("\nFailed sends:")
        for r in failed:
            print(f"  -> {r['email']} : {r.get('error')}")

    print("=" * 60)


if __name__ == "__main__":
    run_test()
