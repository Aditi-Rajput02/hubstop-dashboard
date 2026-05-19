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

token = os.getenv("HUBSPOT_API_KEY", "")
print(f"Token loaded  : {repr(token[:30])}...")
print(f"Token length  : {len(token)}")

# Test the API call
url = "https://api.hubapi.com/crm/v3/objects/contacts"
headers = {"Authorization": f"Bearer {token}"}
params = {"limit": 5, "properties": "firstname,lastname,email"}

print(f"\nCalling: {url}")
print(f"Auth header: Bearer {token[:20]}...")

response = requests.get(url, headers=headers, params=params)
print(f"\nStatus code: {response.status_code}")
print(f"Response: {response.text[:500]}")
