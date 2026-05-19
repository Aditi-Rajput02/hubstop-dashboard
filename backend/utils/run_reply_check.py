"""
Run reply check manually — detects replies from contacts and marks them in HubSpot.

Usage (from CRM root):
    venv\Scripts\python backend\run_reply_check.py
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
from pathlib import Path

# Allow running from CRM root OR from backend/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # backend/
sys.path.insert(0, str(ROOT))                   # CRM/

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import hubspot_crm as crm
import sequence_runner as runner

print("=" * 60)
print("Running reply check...")
print("=" * 60)

client = crm.get_client()
count = runner.run_reply_check(client)

print(f"\n✅ Reply check complete — {count} new replies detected")
if count > 0:
    print("   Contacts marked as replied in HubSpot (sequence stopped)")
print("=" * 60)
