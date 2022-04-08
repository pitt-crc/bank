"""Reusable values are defined purly for convenience."""

from datetime import datetime, timedelta

TODAY = datetime.now().date()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)
DAY_AFTER_TOMORROW = TODAY + timedelta(days=2)
DAY_BEFORE_YESTERDAY = TODAY - timedelta(days=2)
