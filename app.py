"""
Top-level entry point for Render / Railway / Heroku deployment.

Render start command:
    uvicorn app:app --host 0.0.0.0 --port $PORT

This file simply imports the FastAPI `app` object from backend/main.py.
Running from the repo root means Python can find both `app` (this file)
and the `backend` package without any PYTHONPATH tricks.
"""

import sys
import os
from pathlib import Path

# Ensure repo root is on sys.path so `backend` package is importable
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Re-export the FastAPI app object
from backend.main import app  # noqa: F401, E402

__all__ = ["app"]
