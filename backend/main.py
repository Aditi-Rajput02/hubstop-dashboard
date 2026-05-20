"""
FastAPI Backend — CRM Sequence Automator Dashboard
Serves real data from HubSpot, Gmail throttle state, and scheduler logs.

Run (development):
    cd c:\\Users\\abc\\Downloads\\CRM\\CRM
    venv\\Scripts\\uvicorn backend.main:app --reload --port 8000

Run (production):
    venv\\Scripts\\uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
"""

import os
import sys
import json
import logging
import logging.config
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent          # CRM/
BACKEND = Path(__file__).parent                 # CRM/backend/
CORE    = BACKEND / "core"
SETUP   = BACKEND / "setup"
for _p in [str(ROOT), str(BACKEND), str(CORE), str(SETUP)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
load_dotenv(ROOT / ".env")

# ── Logging setup ─────────────────────────────────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "development").lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_log_format = (
    '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)r}'
    if APP_ENV == "production"
    else "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=_log_format,
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Startup validation ────────────────────────────────────────────────────────
_REQUIRED_ENV = ["HUBSPOT_API_KEY", "GMAIL_SENDER", "Client_ID", "Client_Secret", "GMAIL_REFRESH_TOKEN"]
_missing = [k for k in _REQUIRED_ENV if not os.getenv(k)]
if _missing:
    log.warning(
        f"⚠️  Missing environment variables: {', '.join(_missing)}. "
        "Some API endpoints will return errors until these are set."
    )

# ── CORS origins from env ─────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if _raw_origins.strip() == "*":
    _cors_origins = ["*"]
else:
    _cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CRM Sequence Automator API",
    description="Dashboard backend for the email sequence automation system",
    version="1.0.0",
    # Hide docs in production
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Compress responses > 1 KB automatically
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_hubspot_contacts() -> list[dict]:
    try:
        import hubspot_crm as crm
        client = crm.get_client()

        SAFE_PROPS = [
            "firstname", "lastname", "email", "hs_lead_status",
            "hs_lastmodifieddate",
        ]
        OPTIONAL_PROPS = [
            "lead_type", "expo_name", "expo_source", "expo_followup_date",
            "email_sequence_day", "email_thread_id", "email_last_message_id",
            "email_references", "email_replied", "email_replied_at",
            "email_stalled_sent", "email_stalled_sent_at", "email_sequence_complete",
        ]
        all_props = SAFE_PROPS + OPTIONAL_PROPS

        all_contacts = []
        after = None

        while True:
            kwargs = {"limit": 100, "properties": all_props, "archived": False}
            if after:
                kwargs["after"] = after

            log.info(f"Fetching contacts with kwargs={kwargs}")

            try:
                result = client.crm.contacts.basic_api.get_page(**kwargs)
            except Exception as page_err:
                log.warning(f"get_page with all props failed: {page_err}")
                kwargs["properties"] = SAFE_PROPS
                result = client.crm.contacts.basic_api.get_page(**kwargs)

            log.info(f"Page returned {len(result.results or [])} contacts")

            for c in (result.results or []):
                props = dict(c.properties or {})
                props["hs_object_id"] = c.id
                # hs_lastmodifieddate in properties is always None from the SDK;
                # the real timestamp lives on c.updated_at (datetime object)
                if not props.get("hs_lastmodifieddate"):
                    updated = getattr(c, "updated_at", None)
                    if updated:
                        props["hs_lastmodifieddate"] = updated.isoformat()
                all_contacts.append(props)

            paging = getattr(result, "paging", None)
            next_page = getattr(paging, "next", None) if paging else None
            after = getattr(next_page, "after", None) if next_page else None

            if not after:
                break

        log.info(f"Fetched {len(all_contacts)} contacts from HubSpot")
        return all_contacts

    except Exception:
        log.exception("HubSpot fetch failed")
        raise


def _get_throttle_status() -> dict:
    """Get current throttle state."""
    try:
        import email_throttle as throttle
        return throttle.get_status()
    except Exception as e:
        log.warning(f"Throttle status failed: {e}")
        return {
            "window_open": False,
            "sent_today": 0,
            "daily_cap": 50,
            "warmup_day": 1,
            "sender_time": "unknown",
        }


def _read_logs(lines: int = 50) -> list[str]:
    """Read last N lines from scheduler.log."""
    log_path = ROOT / "logs" / "scheduler.log"
    if not log_path.exists():
        return ["No log file found yet."]
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return [line.rstrip() for line in all_lines[-lines:]]
    except Exception as e:
        return [f"Error reading log: {e}"]


def _status_label(contact: dict) -> str:
    """Derive a display status from contact properties."""
    if (contact.get("email_replied") or "").lower() == "true":
        return "Replied"
    if (contact.get("email_sequence_complete") or "").lower() == "true":
        return "Complete"
    if (contact.get("email_stalled_sent") or "").lower() == "true":
        return "Stalled"
    # Use hs_lead_status (HubSpot built-in) — was incorrectly "lead_status"
    lead_status = (contact.get("hs_lead_status") or "").strip()
    if lead_status:
        return lead_status
    seq_day = contact.get("email_sequence_day") or "0"
    if str(seq_day) != "0":
        return "Active"
    return "New"


def _format_contact(c: dict) -> dict:
    """Format a HubSpot contact dict for the frontend."""
    first = (c.get("firstname") or "").strip()
    last  = (c.get("lastname") or "").strip()
    name  = f"{first} {last}".strip() or c.get("email", "Unknown")

    return {
        "id":               c.get("hs_object_id", ""),
        "name":             name,
        "email":            c.get("email", ""),
        "company":          c.get("company", ""),
        "lead_type":        c.get("lead_type", "general"),
        "expo_name":        c.get("expo_name", ""),
        "sequence_day":     int(c.get("email_sequence_day") or 0),
        "lead_status":      c.get("hs_lead_status", "New"),
        "status":           _status_label(c),
        "replied":          (c.get("email_replied") or "").lower() == "true",
        "sequence_complete":(c.get("email_sequence_complete") or "").lower() == "true",
        "thread_id":        c.get("email_thread_id", ""),
        "replied_at":       c.get("email_replied_at", ""),
        "last_modified":    c.get("hs_lastmodifieddate", ""),
    }


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "CRM Sequence Automator API"}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@app.get("/api/dashboard")
def get_dashboard():
    """
    Returns KPI summary stats for the dashboard cards.
    sent_today is derived from HubSpot contacts modified today so it reflects
    emails sent via any path (scheduler, manual, HubSpot UI, etc.).
    """
    contacts = _get_hubspot_contacts()
    throttle = _get_throttle_status()

    total     = len(contacts)
    active    = sum(1 for c in contacts if _status_label(c) == "Active")
    replied   = sum(1 for c in contacts if _status_label(c) == "Replied")
    stalled   = sum(1 for c in contacts if _status_label(c) == "Stalled")
    complete  = sum(1 for c in contacts if _status_label(c) == "Complete")
    new_leads = sum(1 for c in contacts if _status_label(c) == "New")

    # ── Derive real sent_today: combine scheduler file + HubSpot activity ────
    # The scheduler file tracks emails sent via the Python runner.
    # HubSpot's hs_lastmodifieddate tracks contacts touched today via any path
    # (HubSpot UI, manual sends, API, etc.).
    # We combine both: scheduler_count + contacts modified today that were NOT
    # already counted by the scheduler (i.e. HubSpot-only sends).
    today_utc = datetime.now(timezone.utc).date().isoformat()  # "YYYY-MM-DD"

    # Count contacts modified today in HubSpot
    sent_today_hs = sum(
        1 for c in contacts
        if (c.get("hs_lastmodifieddate") or "").startswith(today_utc)
    )

    # Scheduler's own count (from throttle_state.json)
    scheduler_sent = throttle.get("sent_today", 0)

    # Combined: use whichever is higher — HubSpot is the ground truth
    # (scheduler count is always a subset of HubSpot modifications)
    real_sent_today = max(scheduler_sent, sent_today_hs)

    # Patch the throttle dict so the frontend sees the correct combined number
    throttle["sent_today"] = real_sent_today
    throttle["remaining_today"] = max(0, throttle.get("daily_cap", 100) - real_sent_today)

    # Sync corrected count back to throttle_state.json so the scheduler
    # doesn't over-send on its next run
    try:
        import email_throttle as _et
        state = _et._load_state()
        if state.get("sent_today", 0) < real_sent_today:
            state["sent_today"] = real_sent_today
            _et._save_state(state)
            log.info(f"Throttle state synced: sent_today updated to {real_sent_today} (scheduler={scheduler_sent}, hubspot={sent_today_hs})")
    except Exception as _e:
        log.debug(f"Could not sync throttle state: {_e}")

    return {
        "kpi": {
            "total_contacts":    total,
            "active_sequences":  active,
            "replied_24h":       replied,
            "stalled_leads":     stalled,
            "complete":          complete,
            "new_leads":         new_leads,
        },
        "throttle": throttle,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/contacts")
def get_contacts(
    status: Optional[str] = None,
    limit: int = 100,
):
    """
    Returns all contacts with their sequence status.
    Optional ?status=Active|Replied|Stalled|New|Complete filter.
    """
    contacts = _get_hubspot_contacts()
    formatted = [_format_contact(c) for c in contacts]

    if status:
        formatted = [c for c in formatted if c["status"].lower() == status.lower()]

    return {
        "contacts": formatted[:limit],
        "total": len(formatted),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/throttle")
def get_throttle():
    """Returns current throttle/send window status."""
    return _get_throttle_status()


@app.get("/api/deals")
def get_deals():
    """
    Returns all open deals from HubSpot, grouped by pipeline stage.
    Lightweight — only fetches dealname, dealstage, amount, closedate, deal_type.
    """
    try:
        import hubspot_crm as crm
        client = crm.get_client()
        props  = ["dealname", "dealstage", "pipeline", "amount", "closedate", "deal_type", "description"]
        result = client.crm.deals.basic_api.get_page(
            limit=100,
            properties=props,
            archived=False,
        )
        deals = []
        for d in (result.results or []):
            p = d.properties or {}
            deals.append({
                "id":          d.id,
                "name":        p.get("dealname", ""),
                "stage":       p.get("dealstage", ""),
                "pipeline":    p.get("pipeline", "default"),
                "amount":      p.get("amount", ""),
                "close_date":  p.get("closedate", ""),
                "deal_type":   p.get("deal_type", ""),
                "description": p.get("description", ""),
            })
        # Group by stage
        stages: dict = {}
        for deal in deals:
            s = deal["stage"] or "unknown"
            stages.setdefault(s, []).append(deal)
        return {"deals": deals, "by_stage": stages, "total": len(deals)}
    except Exception as e:
        log.warning(f"/api/deals error: {e}")
        return {"deals": [], "by_stage": {}, "total": 0, "error": str(e)}


@app.get("/api/logs")
def get_logs(lines: int = 50):
    """Returns last N lines from scheduler.log."""
    log_lines = _read_logs(lines)
    return {
        "lines": log_lines,
        "count": len(log_lines),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/run-now")
def trigger_run(background_tasks: BackgroundTasks):
    """
    Triggers a full sequence run in the background.
    Returns immediately; run happens async.
    """
    def _run():
        try:
            import sequence_runner as runner
            import hubspot_crm as crm
            client = crm.get_client()
            result = runner.run_all(client)
            log.info(f"Manual run triggered from dashboard: {result}")
        except Exception as e:
            log.error(f"Manual run failed: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "triggered",
        "message": "Sequence run started in background",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/check-replies")
def check_replies(background_tasks: BackgroundTasks):
    """Runs reply detection only."""
    def _run():
        try:
            import sequence_runner as runner
            import hubspot_crm as crm
            client = crm.get_client()
            count = runner.run_reply_check(client)
            log.info(f"Manual reply check: {count} replies detected")
        except Exception as e:
            log.error(f"Reply check failed: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "triggered",
        "message": "Reply check started in background",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/check-stalled")
def check_stalled(background_tasks: BackgroundTasks):
    """Runs stalled conversation check only."""
    def _run():
        try:
            import sequence_runner as runner
            import hubspot_crm as crm
            client = crm.get_client()
            count = runner.run_stalled_check(client)
            log.info(f"Manual stalled check: {count} re-engagements sent")
        except Exception as e:
            log.error(f"Stalled check failed: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "triggered",
        "message": "Stalled check started in background",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Sequences API ─────────────────────────────────────────────────────────────

@app.get("/api/sequences")
def get_sequences():
    """
    Groups HubSpot contacts into sequences by expo_name + lead_type.
    Each unique (expo_name, lead_type) pair = one sequence row.
    """
    contacts = _get_hubspot_contacts()
    formatted = [_format_contact(c) for c in contacts]

    # Group by expo_name + lead_type
    groups: dict[tuple, dict] = {}
    for c in formatted:
        expo = (c.get("expo_name") or "Unknown Expo").strip() or "Unknown Expo"
        lt   = (c.get("lead_type") or "general").strip() or "general"
        key  = (expo, lt)
        if key not in groups:
            groups[key] = {
                "id":         f"{expo}_{lt}".replace(" ", "_").lower(),
                "name":       expo,
                "lead_type":  lt,
                "contacts":   0,
                "active":     0,
                "replied":    0,
                "complete":   0,
                "stalled":    0,
                "new":        0,
                "max_day":    0,
            }
        g = groups[key]
        g["contacts"] += 1
        status = c.get("status", "New")
        if status == "Active":    g["active"]   += 1
        elif status == "Replied": g["replied"]  += 1
        elif status == "Complete":g["complete"] += 1
        elif status == "Stalled": g["stalled"]  += 1
        else:                     g["new"]      += 1
        day = c.get("sequence_day", 0) or 0
        if day > g["max_day"]:
            g["max_day"] = day

    result = []
    for (expo, lt), g in sorted(groups.items()):
        total = g["contacts"]
        replied_pct = round(g["replied"] / total * 100, 1) if total else 0
        complete_pct = round(g["complete"] / total * 100, 1) if total else 0
        # Sequence status: Active if any active, Paused if all complete/new
        if g["active"] > 0:
            seq_status = "Active"
        elif g["complete"] == total:
            seq_status = "Complete"
        else:
            seq_status = "Paused"

        result.append({
            "id":           g["id"],
            "name":         expo,
            "sub":          lt.replace("_", " ").title(),
            "lead_type":    lt,
            "status":       seq_status,
            "contacts":     total,
            "active":       g["active"],
            "replied":      g["replied"],
            "complete":     g["complete"],
            "stalled":      g["stalled"],
            "new":          g["new"],
            "reply_rate":   replied_pct,
            "complete_rate":complete_pct,
            "max_day":      g["max_day"],
        })

    # Summary stats
    total_contacts = sum(r["contacts"] for r in result)
    total_active   = sum(1 for r in result if r["status"] == "Active")
    avg_reply      = round(
        sum(r["reply_rate"] for r in result) / len(result), 1
    ) if result else 0

    return {
        "sequences": result,
        "total": len(result),
        "stats": {
            "total_sequences": len(result),
            "active_sequences": total_active,
            "total_contacts": total_contacts,
            "avg_reply_rate": avg_reply,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class SequenceCreate(BaseModel):
    name: str                        # expo_name value to set
    lead_type: str                   # bulk_liquid | private_label | general
    followup_date: str               # YYYY-MM-DD — Day 1 fires on this date
    contact_ids: list[str]           # HubSpot contact IDs to assign
    expo_source: Optional[str] = ""  # expo_source dropdown value


@app.post("/api/sequences")
def create_sequence(payload: SequenceCreate):
    """
    Creates a new sequence by updating HubSpot contacts:
    - Sets expo_name, lead_type, expo_followup_date on each contact
    - Resets email_sequence_day to 0 so the scheduler picks them up
    """
    try:
        import hubspot_crm as crm
        client = crm.get_client()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"HubSpot connection failed: {e}")

    updated = []
    failed  = []
    props_to_set = {
        "expo_name":           payload.name,
        "lead_type":           payload.lead_type,
        "expo_followup_date":  payload.followup_date,
        "email_sequence_day":  "0",
        "email_sequence_complete": "false",
        "email_replied":       "false",
    }
    if payload.expo_source:
        props_to_set["expo_source"] = payload.expo_source

    for cid in payload.contact_ids:
        try:
            from hubspot.crm.contacts.models import SimplePublicObjectInput
            client.crm.contacts.basic_api.update(
                contact_id=cid,
                simple_public_object_input=SimplePublicObjectInput(properties=props_to_set),
            )
            updated.append(cid)
        except Exception as e:
            log.warning(f"Failed to update contact {cid}: {e}")
            failed.append(cid)

    return {
        "status": "ok",
        "sequence_name": payload.name,
        "lead_type": payload.lead_type,
        "followup_date": payload.followup_date,
        "updated": len(updated),
        "failed": len(failed),
        "failed_ids": failed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Templates API ─────────────────────────────────────────────────────────────

TEMPLATES_FILE = ROOT / "backend" / "core" / "email_templates.py"

# In-memory store: key = "day{d}_{type}", value = {subject, body}
_template_overrides: dict = {}

def _load_template_preview(day: int, lead_type: str) -> dict:
    """Return subject+body for a given day/type using current Python templates."""
    try:
        import importlib, email_templates as et
        importlib.reload(et)
        subject, body = et.get_template(day, lead_type, {
            "firstname": "{{first_name}}",
            "expo_name": "{{expo_name}}",
        })
        return {"subject": subject, "body": body}
    except Exception as e:
        return {"subject": "", "body": f"Error loading template: {e}"}


@app.get("/api/templates")
def get_templates():
    """Return all 12 sequence templates (4 days × 3 lead types) + stalled."""
    days = [1, 3, 7, 14]
    types = ["bulk_liquid", "private_label", "general"]
    result = []
    for day in days:
        for lt in types:
            key = f"day{day}_{lt}"
            if key in _template_overrides:
                tpl = _template_overrides[key]
            else:
                tpl = _load_template_preview(day, lt)
            result.append({
                "key": key,
                "day": day,
                "lead_type": lt,
                "subject": tpl.get("subject", ""),
                "body": tpl.get("body", ""),
            })
    # stalled re-engage
    key = "stalled_reengage"
    if key in _template_overrides:
        tpl = _template_overrides[key]
    else:
        try:
            import importlib, email_templates as et
            importlib.reload(et)
            subject, body = et.stalled_reengage({"firstname": "{{first_name}}"})
            tpl = {"subject": subject, "body": body}
        except Exception as e:
            tpl = {"subject": "", "body": str(e)}
    result.append({
        "key": key,
        "day": None,
        "lead_type": "all",
        "subject": tpl.get("subject", ""),
        "body": tpl.get("body", ""),
    })
    return {"templates": result, "total": len(result)}


class TemplateUpdate(BaseModel):
    subject: str
    body: str


@app.put("/api/templates/{key}")
def update_template(key: str, payload: TemplateUpdate):
    """
    Save an edited template (in-memory for this session).
    The frontend can display and edit; changes persist until server restart
    unless you also write back to email_templates.py.
    """
    _template_overrides[key] = {
        "subject": payload.subject,
        "body": payload.body,
    }
    return {
        "status": "saved",
        "key": key,
        "subject": payload.subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/templates/{key}/reset")
def reset_template(key: str):
    """Reset a template override back to the Python default."""
    _template_overrides.pop(key, None)
    return {"status": "reset", "key": key}


@app.get("/api/templates/{key}/preview")
def preview_template(key: str, firstname: str = "Alex", expo_name: str = "the expo"):
    """Preview a template with real substitution values."""
    if key in _template_overrides:
        tpl = _template_overrides[key]
        subject = tpl["subject"].replace("{{first_name}}", firstname).replace("{{expo_name}}", expo_name)
        body    = tpl["body"].replace("{{first_name}}", firstname).replace("{{expo_name}}", expo_name)
        return {"subject": subject, "body": body}
    # parse key
    try:
        import email_templates as et
        props = {"firstname": firstname, "expo_name": expo_name}
        if key == "stalled_reengage":
            subject, body = et.stalled_reengage(props)
        else:
            parts = key.split("_", 1)  # day1, bulk_liquid
            day = int(parts[0].replace("day", ""))
            lt  = parts[1]
            subject, body = et.get_template(day, lt, props)
        return {"subject": subject, "body": body}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/activity")
def get_activity():
    """
    Returns two datasets for the Activity page:
    1. activity_feed  – per-contact events (Sent / Reply / Stalled / Complete)
                        sorted by last_modified descending.
    2. recent_items   – the 4 most-recently-modified contacts + deals,
                        formatted as cards (type, name, status, last_modified).
    """
    try:
        contacts = _get_hubspot_contacts()
    except Exception as e:
        log.warning(f"/api/activity contacts fetch failed: {e}")
        contacts = []

    # ── Build activity feed ───────────────────────────────────────────────────
    feed = []
    for c in contacts:
        fmt = _format_contact(c)
        status = fmt["status"]

        # Map contact status → activity type
        if status == "Replied":
            act_type = "Reply"
        elif status == "Stalled":
            act_type = "Stalled"
        elif status == "Complete":
            act_type = "Complete"
        else:
            act_type = "Sent"

        # Build a pseudo subject from lead_type + expo_name
        lead_type = (fmt.get("lead_type") or "general").replace("_", " ").title()
        expo = fmt.get("expo_name") or ""
        if expo:
            subject = f"{lead_type} outreach — {expo}"
        else:
            subject = f"{lead_type} outreach"

        feed.append({
            "id":           fmt["id"],
            "contact_name": fmt["name"],
            "email":        fmt["email"],
            "type":         act_type,
            "subject":      subject,
            "lead_type":    fmt.get("lead_type", ""),
            "sequence_day": fmt.get("sequence_day", 0),
            "expo_name":    fmt.get("expo_name", ""),
            "timestamp":    fmt.get("last_modified") or datetime.now(timezone.utc).isoformat(),
        })

    # Sort by timestamp descending
    feed.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    # ── Build recent items (cards) ────────────────────────────────────────────
    # Contacts sorted by last_modified
    contact_items = []
    for c in contacts:
        fmt = _format_contact(c)
        # Use hs_lead_status as badge if available, else fall back to derived status
        badge = (fmt.get("lead_status") or "").strip() or fmt["status"]
        contact_items.append({
            "id":            fmt["id"],
            "type":          "contact",
            "name":          fmt["name"],
            "status":        badge,
            "last_modified": fmt.get("last_modified") or "",
        })
    contact_items.sort(key=lambda x: x["last_modified"] or "", reverse=True)

    # Deals
    deal_items = []
    try:
        import hubspot_crm as crm
        client = crm.get_client()
        result = client.crm.deals.basic_api.get_page(
            limit=20,
            properties=["dealname", "dealstage", "hs_lastmodifieddate"],
            archived=False,
        )
        for d in (result.results or []):
            p = d.properties or {}
            # Use SDK's updated_at since hs_lastmodifieddate property is None
            deal_ts = p.get("hs_lastmodifieddate") or ""
            if not deal_ts:
                updated = getattr(d, "updated_at", None)
                if updated:
                    deal_ts = updated.isoformat()
            # Clean up deal stage display name
            raw_stage = (p.get("dealstage") or "")
            stage_display = raw_stage.replace("_", " ").replace("appointmentscheduled", "Appointment Scheduled").replace("qualifiedtobuy", "Qualified to Buy").replace("presentationscheduled", "Presentation Scheduled").replace("decisionmakerboughtin", "Decision Maker Bought In").replace("contractsent", "Contract Sent").replace("closedwon", "Closed Won").replace("closedlost", "Closed Lost")
            if stage_display == raw_stage:
                # fallback: title-case
                stage_display = raw_stage.replace("_", " ").title()
            deal_items.append({
                "id":            d.id,
                "type":          "deal",
                "name":          p.get("dealname") or "Unnamed Deal",
                "status":        stage_display or None,
                "last_modified": deal_ts,
            })
        deal_items.sort(key=lambda x: x["last_modified"] or "", reverse=True)
    except Exception as e:
        log.warning(f"/api/activity deals fetch failed: {e}")

    # Merge contacts + deals, sort, take top 4
    all_recent = contact_items[:8] + deal_items[:4]
    all_recent.sort(key=lambda x: x["last_modified"] or "", reverse=True)
    recent_items = all_recent[:4]

    return {
        "activity_feed":  feed,
        "recent_items":   recent_items,
        "total_feed":     len(feed),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/contact/{contact_id}")
def get_contact(contact_id: str):
    """Get a single contact by HubSpot ID."""
    try:
        import hubspot_crm as crm
        client = crm.get_client()
        result = client.crm.contacts.basic_api.get_by_id(
            contact_id=contact_id,
            properties=crm.CONTACT_PROPS,
        )
        props = dict(result.properties or {})
        props["hs_object_id"] = result.id
        return _format_contact(props)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
