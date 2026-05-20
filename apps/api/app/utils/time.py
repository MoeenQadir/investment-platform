"""Time helpers. Centralises UTC-now so we can swap to tz-aware datetimes later
without hunting through every call site.

Returns naive UTC for now — DB columns are `DateTime` (no timezone). Replacing
this with tz-aware values requires a coordinated migration + model change.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime, replacement for the deprecated `datetime.utcnow()`."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
