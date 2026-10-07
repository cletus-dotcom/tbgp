"""App clock. Timestamps are stored as naive Asia/Manila local time (UTC+8, no DST)."""

from datetime import datetime, timedelta, timezone

MANILA_TZ = timezone(timedelta(hours=8), "Asia/Manila")
MANILA_UTC_OFFSET_HOURS = 8


def manila_now():
    return datetime.now(MANILA_TZ).replace(tzinfo=None)


def manila_today():
    return manila_now().date()
