"""
Scheduler — Phase 3 Entry Point
Runs the email sequence on a schedule using APScheduler.

Schedule:
  Every 30 minutes during business hours → sequence_runner.run_all()
  Every 5 minutes outside business hours → reply/stalled checks only (no sends)

Usage:
  venv\\Scripts\\python scheduler.py              # run continuously (recommended)
  venv\\Scripts\\python scheduler.py --run-now    # fire one cycle immediately and exit
  venv\\Scripts\\python scheduler.py --status     # print throttle status and exit

Keep this process running on your server (use systemd, screen, or pm2).
Alternatively, use the cron alternative at the bottom of this file.
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
import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

import hubspot_crm    as crm
import email_throttle as throttle
import sequence_runner as runner

load_dotenv(__import__("pathlib").Path(__file__).parent.parent.parent / ".env")

# ── Logging setup ─────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("scheduler")


# ── Shared HubSpot client (reused across runs) ────────────────────────────────
_hs_client = None

def _get_hs_client():
    global _hs_client
    if _hs_client is None:
        _hs_client = crm.get_client()
    return _hs_client


# ── Scheduled job ─────────────────────────────────────────────────────────────

def scheduled_job():
    """
    Main job fired by APScheduler every 30 minutes.
    Delegates entirely to sequence_runner.run_all().
    """
    try:
        runner.run_all(hs_client=_get_hs_client())
    except Exception as e:
        log.error(f"Unhandled error in scheduled_job: {e}", exc_info=True)


# ── APScheduler event listeners ───────────────────────────────────────────────

def _on_job_executed(event):
    log.debug(f"Job executed: {event.job_id} at {datetime.now(timezone.utc).isoformat()}")


def _on_job_error(event):
    log.error(f"Job failed: {event.job_id} — {event.exception}")


# ── Graceful shutdown ─────────────────────────────────────────────────────────

def _handle_signal(sig, frame):
    log.info(f"Signal {sig} received — shutting down scheduler gracefully...")
    sys.exit(0)


# ── CLI modes ─────────────────────────────────────────────────────────────────

def cmd_status():
    """Print current throttle status and exit."""
    status = throttle.get_status()
    print("\n── Throttle Status ──────────────────────────────────")
    print(f"  Sender time   : {status['sender_time']}")
    print(f"  Window open   : {'✅ YES' if status['window_open'] else '❌ NO'}")
    print(f"  Sent today    : {status['sent_today']} / {status['daily_cap']}")
    print(f"  Remaining     : {status['remaining_today']}")
    print(f"  Warmup day    : {status['warmup_day']} (started {status['warmup_start']})")
    if not status['window_open']:
        secs = throttle.seconds_until_next_window()
        h, m = divmod(secs // 60, 60)
        print(f"  Next window   : in {h}h {m}m")
    print("─────────────────────────────────────────────────────\n")


def cmd_run_now():
    """Fire one full sequence cycle immediately and exit."""
    log.info("--run-now: firing one cycle immediately")
    runner.run_all(hs_client=_get_hs_client())
    log.info("--run-now: done")


def cmd_scheduler():
    """Start the APScheduler loop (runs indefinitely)."""
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    scheduler = BlockingScheduler(timezone="UTC")

    # Main job: every 30 minutes
    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(minutes=30),
        id="sequence_runner",
        name="Email Sequence Runner",
        max_instances=1,          # never run two cycles in parallel
        coalesce=True,            # if missed, run once (not multiple times)
        misfire_grace_time=300,   # 5-minute grace window for misfires
    )

    scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(_on_job_error,    EVENT_JOB_ERROR)

    log.info("=" * 60)
    log.info("APScheduler started — sequence runs every 30 minutes")
    log.info("Press Ctrl+C to stop")
    log.info("=" * 60)

    # Fire once immediately on startup so we don't wait 30 minutes
    log.info("Firing initial run on startup...")
    scheduled_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--status" in args:
        cmd_status()

    elif "--run-now" in args:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        cmd_run_now()

    else:
        cmd_scheduler()


# ══════════════════════════════════════════════════════════════════════════════
# CRON ALTERNATIVE (if you prefer cron over APScheduler)
# ══════════════════════════════════════════════════════════════════════════════
#
# Instead of running scheduler.py continuously, you can add this to crontab:
#
#   crontab -e
#
# Add these lines (adjust paths to your actual venv and project directory):
#
#   # Run sequence every 30 minutes, Mon-Fri, 9am-5pm (server must be in sender TZ)
#   */30 9-16 * * 1-5 /path/to/CRM/venv/bin/python /path/to/CRM/scheduler.py --run-now >> /path/to/CRM/logs/cron.log 2>&1
#
#   # Reply/stalled check every hour outside business hours (catches overnight replies)
#   0 * * * * /path/to/CRM/venv/bin/python /path/to/CRM/scheduler.py --run-now >> /path/to/CRM/logs/cron.log 2>&1
#
# On Windows, use Task Scheduler instead:
#   Action: venv\Scripts\python.exe scheduler.py --run-now
#   Trigger: Daily, repeat every 30 minutes, between 09:00 and 17:00
# ══════════════════════════════════════════════════════════════════════════════
