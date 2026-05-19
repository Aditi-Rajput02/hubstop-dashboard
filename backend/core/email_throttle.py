"""
Email Throttle & Send-Window Guard — Phase 3

Rules enforced here:
  1. Business hours only  — 9 am–5 pm in SENDER_TIMEZONE (from .env)
  2. No weekends          — Monday–Friday only
  3. Daily cap            — starts at MAX_EMAILS_PER_DAY (env), ramps up
  4. Randomised intervals — random sleep between sends to look human
  5. Warmup ramp          — week 1: 100/day, week 2: 150/day, week 3+: 300/day

All state (emails sent today, warmup start date) is persisted in
  logs/throttle_state.json
so it survives restarts.
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
import json
import time
import random
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from pathlib import Path as _Path
load_dotenv(_Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

# ── Config from .env ──────────────────────────────────────────────────────────
SENDER_TZ          = ZoneInfo(os.getenv("SENDER_TIMEZONE", "America/Chicago"))
BIZ_START          = int(os.getenv("BUSINESS_HOURS_START", 9))   # 9 am
BIZ_END            = int(os.getenv("BUSINESS_HOURS_END",   17))  # 5 pm
MAX_PER_DAY        = int(os.getenv("MAX_EMAILS_PER_DAY",   150))

# Warmup schedule: {week_number: daily_cap}
# Week 1 = first 7 days after warmup_start_date
WARMUP_CAPS = {
    1: 100,
    2: 150,
    3: 300,
}
WARMUP_MAX = 300   # cap after warmup period ends

# Randomised delay between sends (seconds)
SEND_DELAY_MIN = 45    # minimum seconds between emails
SEND_DELAY_MAX = 180   # maximum seconds between emails

STATE_FILE = Path(__file__).parent.parent / "logs" / "throttle_state.json"


# ── State persistence ─────────────────────────────────────────────────────────

def _load_state() -> dict:
    """Load throttle state from disk. Creates defaults if missing."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Default state — warmup starts today
    state = {
        "warmup_start_date": date.today().isoformat(),
        "sent_today":        0,
        "last_send_date":    "",
    }
    _save_state(state)
    return state


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _reset_daily_counter_if_new_day(state: dict) -> dict:
    """Resets sent_today to 0 if it's a new calendar day (sender timezone)."""
    today_str = _today_str()
    if state.get("last_send_date") != today_str:
        state["sent_today"]     = 0
        state["last_send_date"] = today_str
        _save_state(state)
    return state


# ── Daily cap calculation ─────────────────────────────────────────────────────

def _get_daily_cap(state: dict) -> int:
    """
    Returns today's email cap based on warmup week.
    Week 1 (days 1-7)  → 100
    Week 2 (days 8-14) → 150
    Week 3+ (day 15+)  → 300
    Also respects MAX_EMAILS_PER_DAY from .env as an absolute ceiling.
    """
    warmup_start = date.fromisoformat(state["warmup_start_date"])
    days_elapsed = (date.today() - warmup_start).days + 1  # 1-indexed

    if days_elapsed <= 7:
        cap = WARMUP_CAPS[1]
    elif days_elapsed <= 14:
        cap = WARMUP_CAPS[2]
    else:
        cap = WARMUP_MAX

    return min(cap, MAX_PER_DAY)


# ── Business-hours / weekend guard ───────────────────────────────────────────

def is_send_window_open() -> bool:
    """
    Returns True if it is currently a weekday AND within business hours
    in the sender's timezone.
    """
    now = datetime.now(SENDER_TZ)
    if now.weekday() >= 5:          # 5=Saturday, 6=Sunday
        return False
    if now.hour < BIZ_START or now.hour >= BIZ_END:
        return False
    return True


def seconds_until_next_window() -> int:
    """
    Returns the number of seconds until the next send window opens.
    Used by the scheduler to sleep instead of busy-waiting.
    """
    now = datetime.now(SENDER_TZ)
    weekday = now.weekday()

    # If it's a weekend, advance to Monday
    if weekday == 5:   # Saturday
        days_ahead = 2
    elif weekday == 6: # Sunday
        days_ahead = 1
    else:
        days_ahead = 0

    target = now.replace(hour=BIZ_START, minute=0, second=0, microsecond=0)
    target = target + timedelta(days=days_ahead)

    # If we're past today's window, move to next business day
    if days_ahead == 0 and now.hour >= BIZ_END:
        if weekday == 4:  # Friday → Monday
            target += timedelta(days=3)
        else:
            target += timedelta(days=1)

    delta = (target - now).total_seconds()
    return max(0, int(delta))


# ── Main throttle interface ───────────────────────────────────────────────────

def can_send_now() -> tuple[bool, str]:
    """
    Returns (True, "") if an email can be sent right now.
    Returns (False, reason) if sending should be blocked.

    Checks:
      1. Business hours / weekday
      2. Daily cap not exceeded
    """
    if not is_send_window_open():
        now = datetime.now(SENDER_TZ)
        return False, (
            f"Outside business hours "
            f"({now.strftime('%A %H:%M')} {SENDER_TZ})"
        )

    state = _load_state()
    state = _reset_daily_counter_if_new_day(state)
    cap   = _get_daily_cap(state)

    if state["sent_today"] >= cap:
        return False, f"Daily cap reached ({state['sent_today']}/{cap})"

    return True, ""


def record_send() -> None:
    """
    Call this immediately after a successful send.
    Increments the daily counter and persists state.
    """
    state = _load_state()
    state = _reset_daily_counter_if_new_day(state)
    state["sent_today"] += 1
    _save_state(state)
    log.debug(f"Throttle: sent_today={state['sent_today']}")


def random_delay() -> None:
    """
    Sleeps for a random interval between SEND_DELAY_MIN and SEND_DELAY_MAX
    seconds. Call this between consecutive sends to avoid burst patterns.
    """
    delay = random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX)
    log.debug(f"Throttle: sleeping {delay:.1f}s before next send")
    time.sleep(delay)


def get_status() -> dict:
    """Returns a human-readable status dict for logging / debugging."""
    state = _load_state()
    state = _reset_daily_counter_if_new_day(state)
    cap   = _get_daily_cap(state)
    warmup_start = date.fromisoformat(state["warmup_start_date"])
    days_elapsed = (date.today() - warmup_start).days + 1

    return {
        "window_open":      is_send_window_open(),
        "sent_today":       state["sent_today"],
        "daily_cap":        cap,
        "remaining_today":  max(0, cap - state["sent_today"]),
        "warmup_day":       days_elapsed,
        "warmup_start":     state["warmup_start_date"],
        "sender_time":      datetime.now(SENDER_TZ).strftime("%Y-%m-%d %H:%M %Z"),
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _today_str() -> str:
    return datetime.now(SENDER_TZ).strftime("%Y-%m-%d")
