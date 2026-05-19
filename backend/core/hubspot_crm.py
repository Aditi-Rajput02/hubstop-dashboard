"""
HubSpot CRM Operations — Phase 3
Uses the official HubSpot Python SDK (hubspot-api-client).

Responsibilities:
  - Fetch contacts due for follow-up today
  - Read / write sequence state (thread_id, last_message_id, sequence_day,
    replied_at, stalled_sent_at) stored as HubSpot contact properties
  - Mark contacts as replied / archived / stalled
  - Log email activity as HubSpot Engagements (email type)

Custom HubSpot properties required (create these in HubSpot → Settings →
Properties → Contact properties before running):

  Property internal name          | Type   | Description
  --------------------------------|--------|-----------------------------
  expo_followup_date              | date   | Day 1 fires on this date
  lead_type                       | string | bulk_liquid / private_label / general
  expo_name                       | string | Name of the expo
  email_sequence_day              | number | Last sequence day sent (0 = none)
  email_thread_id                 | string | Gmail threadId
  email_last_message_id           | string | RFC-2822 Message-ID of last sent msg
  email_references                | string | Full References header chain
  email_replied                   | bool   | True once contact replies
  email_replied_at                | datetime | Timestamp of first reply
  email_stalled_sent              | bool   | True once stalled re-engage sent
  email_stalled_sent_at           | datetime | Timestamp of stalled re-engage
  email_sequence_complete         | bool   | True after Day 14 sent
  lead_status                     | string | New / Active / Stalled / Archived / Cold
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
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
import hubspot
from hubspot.crm.contacts import ApiException
from hubspot.crm.contacts.models import SimplePublicObjectInput
from hubspot.crm.objects.emails import (
    SimplePublicObjectInputForCreate as EmailInputForCreate,
)

from pathlib import Path as _Path
load_dotenv(_Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

# ── All contact properties we read / write ────────────────────────────────────
CONTACT_PROPS = [
    "firstname", "lastname", "email",
    "lead_type", "expo_name", "expo_source", "expo_followup_date",
    "lead_status",
    "email_sequence_day",
    "email_thread_id",
    "email_last_message_id",
    "email_references",
    "email_replied",
    "email_replied_at",
    "email_stalled_sent",
    "email_stalled_sent_at",
    "email_sequence_complete",
]


# ── Client factory ────────────────────────────────────────────────────────────

def get_client() -> hubspot.Client:
    api_key = os.getenv("HUBSPOT_API_KEY")
    if not api_key:
        raise ValueError("HUBSPOT_API_KEY not set in .env")
    return hubspot.Client.create(access_token=api_key)


# ── Fetch contacts ────────────────────────────────────────────────────────────

def get_contacts_due_today(client: hubspot.Client) -> list[dict]:
    """
    Returns all contacts whose expo_followup_date is today (UTC)
    AND whose lead_status is NOT Cold or Archived
    AND who have NOT completed the sequence yet.

    HubSpot date properties are stored as midnight UTC milliseconds.
    We compare against today's date in UTC.
    """
    today_ms = _today_midnight_utc_ms()

    # HubSpot filter: expo_followup_date == today AND sequence not complete
    filter_groups = [
        {
            "filters": [
                {
                    "propertyName": "expo_followup_date",
                    "operator":     "EQ",
                    "value":        str(today_ms),
                },
                {
                    "propertyName": "email_sequence_complete",
                    "operator":     "NEQ",
                    "value":        "true",
                },
            ]
        }
    ]

    contacts = _search_contacts(client, filter_groups)

    # Filter out Cold / Archived in Python (HubSpot filter on string is case-sensitive)
    excluded = {"cold", "archived"}
    result = [
        c for c in contacts
        if (c.get("lead_status") or "").lower() not in excluded
    ]
    log.info(f"Contacts due today: {len(result)}")
    return result


def get_active_sequence_contacts(client: hubspot.Client) -> list[dict]:
    """
    Returns contacts that are mid-sequence:
      - email_sequence_day > 0
      - email_sequence_complete != true
      - email_replied != true
      - lead_status not Cold / Archived
    """
    filter_groups = [
        {
            "filters": [
                {
                    "propertyName": "email_sequence_day",
                    "operator":     "GT",
                    "value":        "0",
                },
                {
                    "propertyName": "email_sequence_complete",
                    "operator":     "NEQ",
                    "value":        "true",
                },
                {
                    "propertyName": "email_replied",
                    "operator":     "NEQ",
                    "value":        "true",
                },
            ]
        }
    ]

    contacts = _search_contacts(client, filter_groups)
    excluded = {"cold", "archived"}
    return [
        c for c in contacts
        if (c.get("lead_status") or "").lower() not in excluded
    ]


def get_replied_contacts(client: hubspot.Client) -> list[dict]:
    """
    Returns contacts that have replied but whose conversation may have stalled.
    Used by the stalled-conversation checker.
    """
    filter_groups = [
        {
            "filters": [
                {
                    "propertyName": "email_replied",
                    "operator":     "EQ",
                    "value":        "true",
                },
                {
                    "propertyName": "email_stalled_sent",
                    "operator":     "NEQ",
                    "value":        "true",
                },
            ]
        }
    ]
    return _search_contacts(client, filter_groups)


def get_contact_by_email(client: hubspot.Client, email: str) -> dict | None:
    """Fetch a single contact by email address. Returns props dict or None."""
    try:
        result = client.crm.contacts.basic_api.get_by_id(
            contact_id=email,
            id_property="email",
            properties=CONTACT_PROPS,
        )
        return _flatten(result)
    except ApiException as e:
        if e.status == 404:
            return None
        raise


# ── Write sequence state back to HubSpot ─────────────────────────────────────

def update_contact_props(
    client: hubspot.Client,
    contact_id: str,
    props: dict,
) -> None:
    """
    Updates arbitrary contact properties.

    Args:
        contact_id : HubSpot contact ID (numeric string)
        props      : dict of {property_name: value}
    """
    update_input = SimplePublicObjectInput(properties=props)
    client.crm.contacts.basic_api.update(
        contact_id=contact_id,
        simple_public_object_input=update_input,
    )
    log.debug(f"Updated contact {contact_id}: {list(props.keys())}")


def mark_sequence_day_sent(
    client: hubspot.Client,
    contact_id: str,
    day: int,
    thread_id: str,
    last_message_id: str,
    references: str,
) -> None:
    """
    Records that a sequence email was sent for a contact.
    Stores thread state so the next email can reply on the same thread.
    """
    props = {
        "email_sequence_day":     str(day),
        "email_thread_id":        thread_id,
        "email_last_message_id":  last_message_id,
        "email_references":       references,
        "lead_status":            "Active",
    }
    if day == 14:
        props["email_sequence_complete"] = "true"

    update_contact_props(client, contact_id, props)
    log.info(f"Contact {contact_id}: sequence day {day} recorded in HubSpot")


def mark_replied(
    client: hubspot.Client,
    contact_id: str,
) -> None:
    """Marks a contact as having replied. Stops the sequence."""
    now_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    update_contact_props(client, contact_id, {
        "email_replied":    "true",
        "email_replied_at": now_ms,
        "lead_status":      "Active",
    })
    log.info(f"Contact {contact_id}: marked as replied — sequence stopped")


def mark_stalled_sent(
    client: hubspot.Client,
    contact_id: str,
) -> None:
    """Marks that a stalled re-engagement email was sent."""
    now_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))
    update_contact_props(client, contact_id, {
        "email_stalled_sent":    "true",
        "email_stalled_sent_at": now_ms,
        "lead_status":           "Stalled",
    })
    log.info(f"Contact {contact_id}: stalled re-engagement sent")


def mark_archived(client: hubspot.Client, contact_id: str) -> None:
    """Archives a contact after Day 14 with no reply."""
    update_contact_props(client, contact_id, {
        "lead_status":            "Archived",
        "email_sequence_complete": "true",
    })
    log.info(f"Contact {contact_id}: archived after sequence completion")


# ── Log email activity as HubSpot Engagement ─────────────────────────────────

def log_email_engagement(
    client: hubspot.Client,
    contact_id: str,
    subject: str,
    body: str,
    to_email: str,
) -> None:
    """
    Creates an Email engagement on the contact's timeline in HubSpot.
    This makes the sent email visible in the contact's activity feed.
    """
    try:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        properties = {
            "hs_timestamp":        str(now_ms),
            "hubspot_owner_id":    "",          # leave blank or set your owner ID
            "hs_email_direction":  "EMAIL",
            "hs_email_status":     "SENT",
            "hs_email_subject":    subject,
            "hs_email_text":       body,
            "hs_email_to_email":   to_email,
            "hs_email_from_email": os.getenv("GMAIL_SENDER", ""),
        }
        email_input = EmailInputForCreate(
            properties=properties,
            associations=[
                {
                    "to":   {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId":   198,  # contact → email
                        }
                    ],
                }
            ],
        )
        client.crm.objects.emails.basic_api.create(
            simple_public_object_input_for_create=email_input
        )
        log.debug(f"Logged email engagement for contact {contact_id}")
    except Exception as e:
        # Non-fatal — engagement logging failure should not stop the sequence
        log.warning(f"Could not log email engagement for {contact_id}: {e}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _today_midnight_utc_ms() -> int:
    """Returns today's date as midnight UTC in milliseconds (HubSpot date format)."""
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp() * 1000)


def _search_contacts(client: hubspot.Client, filter_groups: list) -> list[dict]:
    """
    Runs a HubSpot CRM search and returns a flat list of contact property dicts.
    Handles pagination automatically (up to 10,000 contacts).
    """
    all_contacts = []
    after = None

    while True:
        body = {
            "filterGroups": filter_groups,
            "properties":   CONTACT_PROPS,
            "limit":        100,
        }
        if after:
            body["after"] = after

        try:
            result = client.crm.contacts.search_api.do_search(
                public_object_search_request=body
            )
        except ApiException as e:
            log.error(f"HubSpot search error: {e.reason}")
            break

        for contact in result.results:
            all_contacts.append(_flatten(contact))

        paging = result.paging
        if paging and paging.next and paging.next.after:
            after = paging.next.after
        else:
            break

    return all_contacts


def _flatten(contact_obj) -> dict:
    """
    Converts a HubSpot SDK contact object into a plain dict.
    Adds 'hs_object_id' as the contact's numeric ID.
    """
    props = dict(contact_obj.properties or {})
    props["hs_object_id"] = contact_obj.id
    return props


# ── Deal creation ─────────────────────────────────────────────────────────────

def create_deal_for_contact(
    client: hubspot.Client,
    contact: dict,
    pipeline_id: str = "default",
    deal_stage: str = "appointmentscheduled",
) -> str | None:
    """
    Creates a HubSpot Deal when a contact replies and associates it with the contact.

    Pipeline stage mapping (use your real stage IDs from HubSpot):
      appointmentscheduled  → "Interested" (first stage after reply)

    Returns the new deal ID, or None on failure.
    """
    contact_id = contact.get("hs_object_id", "")
    first      = (contact.get("firstname") or "").strip()
    last       = (contact.get("lastname") or "").strip()
    name       = f"{first} {last}".strip() or contact.get("email", "Contact")
    expo       = contact.get("expo_name", "") or "Inbound Lead"
    lead_type  = contact.get("lead_type", "general")

    deal_name  = f"{name} — {expo}"

    # Map lead_type → deal type label
    deal_type_map = {
        "bulk_liquid":   "Bulk Liquid",
        "private_label": "Private Label",
        "general":       "General",
    }
    deal_type_label = deal_type_map.get(lead_type, "General")

    props = {
        "dealname":    deal_name,
        "pipeline":    pipeline_id,
        "dealstage":   deal_stage,
        "deal_type":   deal_type_label,   # custom property — create in HubSpot if needed
        "description": f"Auto-created when {name} replied to {expo} sequence.",
    }

    try:
        from hubspot.crm.deals.models import SimplePublicObjectInputForCreate as DealInput
        from hubspot.crm.deals.models import PublicAssociationsForObject, AssociationSpec

        associations = [
            PublicAssociationsForObject(
                to={"id": contact_id},
                types=[AssociationSpec(
                    association_category="HUBSPOT_DEFINED",
                    association_type_id=3,   # Deal → Contact
                )],
            )
        ]

        result = client.crm.deals.basic_api.create(
            simple_public_object_input_for_create=DealInput(
                properties=props,
                associations=associations,
            )
        )
        deal_id = result.id
        log.info(f"✅ Deal created: '{deal_name}' (id={deal_id}) for contact {contact_id}")
        return deal_id

    except Exception as e:
        log.warning(f"Deal creation failed for contact {contact_id}: {e}")
        return None
