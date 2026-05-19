"""
HubSpot Custom Properties Setup
=================================
Creates all required custom contact properties in HubSpot automatically.
Run this ONCE before using the CRM automation.

Usage:
    venv\\Scripts\\python setup_hubspot_properties.py
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

TOKEN = os.getenv("HUBSPOT_API_KEY", "")
BASE  = "https://api.hubapi.com"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
}

# ── All custom properties needed by the sequence ─────────────────────────────
# Format: (internal_name, label, type, fieldType, description)

PROPERTIES = [
    {
        "name":        "expo_followup_date",
        "label":       "Expo Follow-up Date",
        "type":        "date",
        "fieldType":   "date",
        "description": "Date when Day 1 email should fire",
        "groupName":   "contactinformation",
    },
    {
        "name":        "lead_type",
        "label":       "Lead Type",
        "type":        "string",
        "fieldType":   "text",
        "description": "bulk_liquid / private_label / general",
        "groupName":   "contactinformation",
    },
    {
        "name":        "expo_name",
        "label":       "Expo Name",
        "type":        "string",
        "fieldType":   "text",
        "description": "Name of the expo/event where lead was met",
        "groupName":   "contactinformation",
    },
    {
        "name":        "expo_source",
        "label":       "Expo Source",
        "type":        "string",
        "fieldType":   "text",
        "description": "Source of the lead (e.g. Expo, Referral)",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_sequence_day",
        "label":       "Email Sequence Day",
        "type":        "number",
        "fieldType":   "number",
        "description": "Last sequence day sent (0 = none, 1/3/7/14)",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_thread_id",
        "label":       "Email Thread ID",
        "type":        "string",
        "fieldType":   "text",
        "description": "Gmail threadId for the sequence thread",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_last_message_id",
        "label":       "Email Last Message ID",
        "type":        "string",
        "fieldType":   "text",
        "description": "RFC-2822 Message-ID of last sent email",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_references",
        "label":       "Email References",
        "type":        "string",
        "fieldType":   "textarea",
        "description": "Full References header chain for threading",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_replied",
        "label":       "Email Replied",
        "type":        "bool",
        "fieldType":   "booleancheckbox",
        "description": "True once contact replies to any email",
        "groupName":   "contactinformation",
        "options": [
            {"label": "Yes", "value": "true",  "displayOrder": 0, "hidden": False},
            {"label": "No",  "value": "false", "displayOrder": 1, "hidden": False},
        ],
    },
    {
        "name":        "email_replied_at",
        "label":       "Email Replied At",
        "type":        "datetime",
        "fieldType":   "date",
        "description": "Timestamp of first reply from contact",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_stalled_sent",
        "label":       "Email Stalled Sent",
        "type":        "bool",
        "fieldType":   "booleancheckbox",
        "description": "True once stalled re-engagement email was sent",
        "groupName":   "contactinformation",
        "options": [
            {"label": "Yes", "value": "true",  "displayOrder": 0, "hidden": False},
            {"label": "No",  "value": "false", "displayOrder": 1, "hidden": False},
        ],
    },
    {
        "name":        "email_stalled_sent_at",
        "label":       "Email Stalled Sent At",
        "type":        "datetime",
        "fieldType":   "date",
        "description": "Timestamp of stalled re-engagement send",
        "groupName":   "contactinformation",
    },
    {
        "name":        "email_sequence_complete",
        "label":       "Email Sequence Complete",
        "type":        "bool",
        "fieldType":   "booleancheckbox",
        "description": "True after Day 14 email sent",
        "groupName":   "contactinformation",
        "options": [
            {"label": "Yes", "value": "true",  "displayOrder": 0, "hidden": False},
            {"label": "No",  "value": "false", "displayOrder": 1, "hidden": False},
        ],
    },
    # NOTE: hs_lead_status is a HubSpot built-in property — no need to create it.
    # It already has: New, Contacted, Followed-up-1/2/3, Replied, Stalled, Re-engaged, Cold, Archived
]


def property_exists(name: str) -> bool:
    """Check if a contact property already exists in HubSpot."""
    url = f"{BASE}/crm/v3/properties/contacts/{name}"
    r = requests.get(url, headers=HEADERS)
    return r.status_code == 200


def create_property(prop: dict) -> tuple[bool, str]:
    """Create a single contact property. Returns (success, message)."""
    url = f"{BASE}/crm/v3/properties/contacts"
    r = requests.post(url, headers=HEADERS, json=prop)
    if r.status_code in (200, 201):
        return True, "created"
    elif r.status_code == 409:
        return True, "already exists"
    else:
        try:
            msg = r.json().get("message", r.text[:200])
        except Exception:
            msg = r.text[:200]
        return False, f"ERROR {r.status_code}: {msg}"


def main():
    if not TOKEN:
        print("ERROR: HUBSPOT_API_KEY not set in .env")
        return

    print("=" * 60)
    print("HubSpot Custom Properties Setup")
    print("=" * 60)
    print(f"Token: {TOKEN[:20]}...")
    print(f"Creating {len(PROPERTIES)} properties...\n")

    created = 0
    skipped = 0
    errors  = 0

    for prop in PROPERTIES:
        name = prop["name"]

        # Check if already exists
        if property_exists(name):
            print(f"  [SKIP]    {name} — already exists")
            skipped += 1
            continue

        success, msg = create_property(prop)
        if success:
            print(f"  [OK]      {name} — {msg}")
            created += 1
        else:
            print(f"  [FAILED]  {name} — {msg}")
            errors += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Created  : {created}")
    print(f"  Skipped  : {skipped} (already existed)")
    print(f"  Errors   : {errors}")

    if errors == 0:
        print("\nAll properties ready! You can now run:")
        print("  venv\\Scripts\\python test_reply_detection.py")
        print("  venv\\Scripts\\python scheduler.py --run-now")
    else:
        print("\nSome properties failed. Check your HubSpot token scopes:")
        print("  crm.schemas.contacts.write is required to create properties")

    print("=" * 60)


if __name__ == "__main__":
    main()
