"""Vercel entry point for the existing FastAPI application.

The application is unchanged; this module only puts backend/ on the import path and
points the SQLite file at the one writable directory a serverless function has. That
filesystem is per-instance and not durable, so accounts created here survive the
instance and no longer, which is the honest limit of this hosting target.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("SCC_DATABASE_PATH", "/tmp/scc.db")

from app.demo.main import app  # noqa: E402

__all__ = ["app"]
