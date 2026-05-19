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
Pre-import duplicate checker.
Run this BEFORE import_contacts.py to catch problems early.
Checks for: duplicate emails in CSV, duplicate emails already in HubSpot,
missing required fields, invalid date formats, empty Lead Type.
"""

import os
import csv
import logging
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
import hubspot
from hubspot.crm.contacts import ApiException

load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(Path(__file__).parent.parent / "logs/validation.log")),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def get_hubspot_client():
    return hubspot.Client.create(access_token=os.getenv("HUBSPOT_API_KEY"))


def validate_csv(csv_path: str) -> dict:
    issues = {
        "duplicate_emails_in_csv": [],
        "missing_email": [],
        "missing_lead_type": [],
        "missing_expo_followup_date": [],
        "invalid_date_format": [],
        "missing_expo_name": [],
        "total_rows": 0,
        "clean_rows": 0
    }

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    issues["total_rows"] = len(rows)

    # Check for duplicate emails within the CSV
    emails = [r.get("Email", "").strip().lower() for r in rows if r.get("Email")]
    email_counts = Counter(emails)
    issues["duplicate_emails_in_csv"] = [e for e, c in email_counts.items() if c > 1]

    for i, row in enumerate(rows, 1):
        email = row.get("Email", "").strip().lower()
        row_id = f"Row {i} ({email or 'no email'})"
        row_clean = True

        if not email:
            issues["missing_email"].append(row_id)
            row_clean = False

        if not row.get("Lead Type", "").strip():
            issues["missing_lead_type"].append(row_id)
            row_clean = False

        expo_source = row.get("Expo Source", "").strip()
        followup_date = row.get("Expo Follow-up Date", "").strip()
        expo_name = row.get("Expo Name", "").strip()

        # Expo leads must have follow-up date and expo name
        if expo_source and "expo" in expo_source.lower():
            if not followup_date:
                issues["missing_expo_followup_date"].append(row_id)
                row_clean = False
            else:
                try:
                    datetime.strptime(followup_date, "%Y-%m-%d")
                except ValueError:
                    issues["invalid_date_format"].append(
                        f"{row_id} — value: '{followup_date}' (expected YYYY-MM-DD)"
                    )
                    row_clean = False

            if not expo_name:
                issues["missing_expo_name"].append(row_id)
                row_clean = False

        if row_clean:
            issues["clean_rows"] += 1

    return issues, rows


def check_hubspot_duplicates(client, emails: list) -> list:
    """Check which emails already exist in HubSpot."""
    existing = []
    for email in emails:
        try:
            client.crm.contacts.basic_api.get_by_id(
                contact_id=email,
                id_property="email",
                properties=["email"]
            )
            existing.append(email)
        except ApiException as e:
            if e.status != 404:
                log.warning(f"API error checking {email}: {e.reason}")
        except Exception:
            pass
    return existing


def print_report(issues: dict, existing_in_hubspot: list) -> bool:
    """Prints validation report. Returns True if safe to import."""
    log.info("\n" + "="*55)
    log.info("CSV VALIDATION REPORT")
    log.info("="*55)
    log.info(f"Total rows       : {issues['total_rows']}")
    log.info(f"Clean rows       : {issues['clean_rows']}")
    log.info(f"Already in CRM   : {len(existing_in_hubspot)} (will be updated, not duplicated)")

    has_blockers = False

    if issues["duplicate_emails_in_csv"]:
        log.error(f"\n❌ DUPLICATE EMAILS IN CSV ({len(issues['duplicate_emails_in_csv'])}):")
        for e in issues["duplicate_emails_in_csv"]:
            log.error(f"   {e}")
        has_blockers = True

    if issues["missing_email"]:
        log.error(f"\n❌ MISSING EMAIL ({len(issues['missing_email'])}):")
        for r in issues["missing_email"]:
            log.error(f"   {r}")
        has_blockers = True

    if issues["invalid_date_format"]:
        log.error(f"\n❌ INVALID DATE FORMAT ({len(issues['invalid_date_format'])}):")
        for r in issues["invalid_date_format"]:
            log.error(f"   {r}")
        has_blockers = True

    if issues["missing_lead_type"]:
        log.warning(f"\n⚠️  MISSING LEAD TYPE ({len(issues['missing_lead_type'])}):")
        for r in issues["missing_lead_type"]:
            log.warning(f"   {r}")

    if issues["missing_expo_name"]:
        log.warning(f"\n⚠️  MISSING EXPO NAME ({len(issues['missing_expo_name'])}):")
        for r in issues["missing_expo_name"]:
            log.warning(f"   {r}")

    if issues["missing_expo_followup_date"]:
        log.warning(f"\n⚠️  MISSING FOLLOW-UP DATE ({len(issues['missing_expo_followup_date'])}):")
        for r in issues["missing_expo_followup_date"]:
            log.warning(f"   {r}")

    if existing_in_hubspot:
        log.info(f"\nℹ️  CONTACTS ALREADY IN HUBSPOT (will update):")
        for e in existing_in_hubspot:
            log.info(f"   {e}")

    log.info("\n" + "="*55)

    if has_blockers:
        log.error("❌ FIX THE ERRORS ABOVE BEFORE IMPORTING")
        return False
    else:
        log.info("✅ CSV IS CLEAN — SAFE TO IMPORT")
        return True


if __name__ == "__main__":
    CSV_PATH = "data/singapore_expo_may2025.csv"

    log.info(f"Validating: {CSV_PATH}")
    issues, rows = validate_csv(CSV_PATH)

    # Check HubSpot for existing contacts
    client = get_hubspot_client()
    emails = [r.get("Email", "").strip().lower() for r in rows if r.get("Email")]
    log.info(f"Checking {len(emails)} emails against HubSpot...")
    existing = check_hubspot_duplicates(client, emails)

    safe = print_report(issues, existing)

    if safe:
        confirm = input("\nProceed with import? (y/n): ").strip().lower()
        if confirm == "y":
            os.system("python import_contacts.py")