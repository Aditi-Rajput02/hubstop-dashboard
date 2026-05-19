import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).parent.parent.parent      # CRM/
_CORE = _ROOT / "backend" / "core"
_SETUP = _ROOT / "backend" / "setup"
for _p in [str(_ROOT), str(_ROOT / "backend"), str(_CORE), str(_SETUP)]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
del _sys, _Path, _ROOT, _CORE, _SETUP, _p

from pathlib import Path
"""
Phase 2 — Lead Capture
Reads the expo CSV and imports all contacts into HubSpot
with all custom properties mapped correctly.
"""

import os
import csv
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import hubspot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, ApiException
from hubspot.crm.contacts.models import SimplePublicObjectInput
from gmail_setup import get_gmail_service  # uses refresh token from .env

load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(Path(__file__).parent.parent / "logs/import.log")),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── HubSpot client ────────────────────────────────────────────────────────────
def get_hubspot_client():
    api_key = os.getenv("HUBSPOT_API_KEY")
    if not api_key:
        raise ValueError("HUBSPOT_API_KEY not set in .env")
    return hubspot.Client.create(access_token=api_key)


# ── Map CSV row → HubSpot properties ─────────────────────────────────────────
def map_row_to_properties(row: dict) -> dict:
    """
    Maps every CSV column to the correct HubSpot internal property name.
    Custom properties use the internal name you set in HubSpot settings.
    """
    props = {}

    # Standard HubSpot properties
    if row.get("First Name"):
        props["firstname"] = row["First Name"].strip()
    if row.get("Last Name"):
        props["lastname"] = row["Last Name"].strip()
    if row.get("Email"):
        props["email"] = row["Email"].strip().lower()
    if row.get("Phone"):
        props["phone"] = row["Phone"].strip()
    if row.get("Company"):
        props["company"] = row["Company"].strip()

    # Custom properties — internal names must match what you created in HubSpot
    if row.get("Expo Source"):
        props["expo_source"] = row["Expo Source"].strip()
    if row.get("Expo Name"):
        props["expo_name"] = row["Expo Name"].strip()
    if row.get("Lead Status"):
        props["lead_status"] = row["Lead Status"].strip()
    if row.get("Lead Type"):
        props["lead_type"] = row["Lead Type"].strip()

    # Expo Follow-up Date → HubSpot expects milliseconds timestamp for date fields
    if row.get("Expo Follow-up Date"):
        try:
            date_str = row["Expo Follow-up Date"].strip()
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            props["expo_followup_date"] = int(dt.timestamp() * 1000)
        except ValueError:
            log.warning(f"Invalid date format for {row.get('Email')}: {row.get('Expo Follow-up Date')}")

    return props


# ── Check if contact already exists by email ──────────────────────────────────
def contact_exists(client, email: str) -> str | None:
    """Returns contact ID if exists, None if not."""
    try:
        result = client.crm.contacts.basic_api.get_by_id(
            contact_id=email,
            id_property="email",
            properties=["email"]
        )
        return result.id
    except ApiException as e:
        if e.status == 404:
            return None
        raise


# ── Create new contact ────────────────────────────────────────────────────────
def create_contact(client, properties: dict) -> str:
    contact_input = SimplePublicObjectInputForCreate(properties=properties)
    result = client.crm.contacts.basic_api.create(
        simple_public_object_input_for_create=contact_input
    )
    return result.id


# ── Update existing contact ───────────────────────────────────────────────────
def update_contact(client, contact_id: str, properties: dict) -> None:
    update_input = SimplePublicObjectInput(properties=properties)
    client.crm.contacts.basic_api.update(
        contact_id=contact_id,
        simple_public_object_input=update_input
    )


# ── Main import function ──────────────────────────────────────────────────────
def import_csv(csv_path: str) -> dict:
    """
    Reads the CSV and creates or updates contacts in HubSpot.
    Returns a summary dict with counts.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    client = get_hubspot_client()
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    log.info(f"Starting import: {len(rows)} rows from {csv_path}")

    for i, row in enumerate(rows, 1):
        email = row.get("Email", "").strip().lower()

        if not email:
            log.warning(f"Row {i}: No email — skipped")
            summary["skipped"] += 1
            continue

        try:
            properties = map_row_to_properties(row)
            existing_id = contact_exists(client, email)

            if existing_id:
                update_contact(client, existing_id, properties)
                log.info(f"Row {i}: Updated — {email}")
                summary["updated"] += 1
            else:
                create_contact(client, properties)
                log.info(f"Row {i}: Created — {email}")
                summary["created"] += 1

        except ApiException as e:
            log.error(f"Row {i}: HubSpot API error for {email} — {e.reason}")
            summary["errors"].append({"email": email, "error": str(e.reason)})

        except Exception as e:
            log.error(f"Row {i}: Unexpected error for {email} — {e}")
            summary["errors"].append({"email": email, "error": str(e)})

        # Rate limiting — HubSpot free tier = 100 requests/10 seconds
        # Stay safe with a small delay
        time.sleep(0.15)

    log.info(f"Import complete — Created: {summary['created']} | "
             f"Updated: {summary['updated']} | "
             f"Skipped: {summary['skipped']} | "
             f"Errors: {len(summary['errors'])}")

    if summary["errors"]:
        log.warning("Failed rows:")
        for err in summary["errors"]:
            log.warning(f"  {err['email']}: {err['error']}")

    return summary


# ── Verify import — spot check 5 contacts ────────────────────────────────────
def verify_import(client, emails: list) -> None:
    """
    Pulls 5 contacts from HubSpot after import and prints their key properties.
    Run this immediately after import to confirm everything mapped correctly.
    """
    log.info("Running verification spot check...")

    props_to_check = [
        "firstname", "lastname", "email", "expo_source",
        "expo_name", "lead_status", "lead_type", "expo_followup_date"
    ]

    for email in emails:
        try:
            result = client.crm.contacts.basic_api.get_by_id(
                contact_id=email,
                id_property="email",
                properties=props_to_check
            )
            p = result.properties
            log.info(
                f"\n  ✅ {email}\n"
                f"     Name       : {p.get('firstname')} {p.get('lastname')}\n"
                f"     Expo Source: {p.get('expo_source')}\n"
                f"     Expo Name  : {p.get('expo_name')}\n"
                f"     Lead Status: {p.get('lead_status')}\n"
                f"     Lead Type  : {p.get('lead_type')}\n"
                f"     Follow-up  : {p.get('expo_followup_date')}"
            )
        except ApiException as e:
            log.error(f"  ❌ Could not fetch {email}: {e.reason}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CSV_PATH = "data/singapore_expo_may2025.csv"

    # Step 1 — Import
    result = import_csv(CSV_PATH)

    # Step 2 — Verify spot check using yopmail test contacts
    if result["created"] > 0 or result["updated"] > 0:
        client = get_hubspot_client()
        verify_import(client, [
            "test.bulk.new@yopmail.com",
            "test.private.new@yopmail.com",
            "test.reply.check@yopmail.com",
            "test.cold.check@yopmail.com",
            "test.archived.check@yopmail.com",
        ])