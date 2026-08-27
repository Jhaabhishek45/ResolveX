import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

# Vercel's deployed filesystem is read-only.
# /tmp is writable but temporary, so use it only on Vercel.
if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp/resolvex")
else:
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "campus.db"

APP_NAME = "ResolveX"
APP_TAGLINE = "Smart Campus Issue Resolution"

SECRET_KEY = os.environ.get(
    "RESOLVEX_SECRET_KEY",
    "development-only-resolvex-key",
)

VALID_ROLES = {
    "reporter",
    "technician",
    "admin",
}

VALID_STATUSES = {
    "REPORTED",
    "TRIAGED",
    "ASSIGNED",
    "IN_PROGRESS",
    "RESOLVED",
    "VERIFIED",
    "CLOSED",
    "REOPENED",
}

VALID_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

PRIORITY_TARGET_HOURS = {
    "LOW": 240,
    "MEDIUM": 120,
    "HIGH": 48,
    "CRITICAL": 24,
}

RECURRING_ISSUE_WINDOW_DAYS = 14
RECURRING_ISSUE_THRESHOLD = 5