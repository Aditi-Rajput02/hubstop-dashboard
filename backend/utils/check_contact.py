"""
Check a specific contact's properties in HubSpot.

Usage (from CRM root):
    venv\Scripts\python backend\check_contact.py test.contacted.web@yopmail.com
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

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))  # backend/
sys.path.insert(0, str(ROOT))                   # CRM/

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.WARNING)

import hubspot_crm as crm

# Accept email as CLI arg or use default
email = sys.argv[1] if len(sys.argv) > 1 else "test.contacted.web@yopmail.com"

client = crm.get_client()
contact = crm.get_contact_by_email(client, email)

if not contact:
    print(f"Contact NOT found in HubSpot: {email}")
else:
    print(f"Contact found: {email}")
    print("-" * 60)
    for key, val in sorted(contact.items()):
        if val:
            print(f"  {key:35s} = {val}")
