"""
Event risk utilities for Indian equities.

Provides a cached earnings-event lookup so the swing screener and portfolio
risk views can flag stocks with near-term result risk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    yf = None

from portfolio_analyzer import normalize_ticker
from stock_history import get_nse_symbol

EVENT_RISK_CACHE_FILE = Path("event_risk_cache.json")
EVENT_RISK_CACHE_TTL_HOURS = 12


@dataclass
class EventRisk:
    ticker: str
    event_type: str = "earnings"
    risk_level: str = "unknown"
    risk_score: int = 0
    flag: str = "No data"
    event_date: Optional[str] = None
    days_to_event: Optional[int] = None
    should_avoid_new_entries: bool = False
    fetched_at: str = ""
    source: str = "yfinance"
    error: Optional[str] = None


def _load_cache() -> dict:
    if not EVENT_RISK_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(EVENT_RISK_CACHE_FILE.read_text())
    except Exception:
        return {}


def _save_cache(cache: dict):
    try:
        EVENT_RISK_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass


def _cache_fresh(entry: dict, ttl_hours: int = EVENT_RISK_CACHE_TTL_HOURS) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return False
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except Exception:
        return False
    return datetime.now() - fetched < timedelta(hours=ttl_hours)


def _as_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().replace(tzinfo=None)
        except Exception:
            return None

    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        try:
            items = value.tolist()
        except Exception:
            items = None
        if isinstance(items, list):
            for item in items:
                parsed = _as_datetime(item)
                if parsed:
                    return parsed

    if isinstance(value, (list, tuple)):
        for item in value:
            parsed = _as_datetime(item)
            if parsed:
                return parsed

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None

    normalized = text.replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            parsed = parser(normalized)
            return parsed.replace(tzinfo=None)
        except Exception:
            continue

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%b %d, %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _extract_event_date_from_calendar(calendar) -> Optional[datetime]:
    if calendar is None:
        return None

    if isinstance(calendar, dict):
        for key, value in calendar.items():
            if "earn" in str(key).lower():
                parsed = _as_datetime(value)
                if parsed:
                    return parsed
        return None

    if hasattr(calendar, "index") and hasattr(calendar, "columns"):
        try:
            for idx in getattr(calendar, "index", []):
                if "earn" in str(idx).lower():
                    row = calendar.loc[idx]
                    if hasattr(row, "iloc"):
                        for item in row.tolist():
                            parsed = _as_datetime(item)
                            if parsed:
                                return parsed
            for column in getattr(calendar, "columns", []):
                if "earn" in str(column).lower():
                    series = calendar[column]
                    if hasattr(series, "dropna"):
                        for item in series.dropna().tolist():
                            parsed = _as_datetime(item)
                            if parsed:
                                return parsed
        except Exception:
            return None
    return None


def _extract_event_date_from_earnings_dates(earnings_dates) -> Optional[datetime]:
    if earnings_dates is None:
        return None
    now = datetime.now()

    if hasattr(earnings_dates, "index"):
        try:
            for idx in earnings_dates.index:
                parsed = _as_datetime(idx)
                if parsed and parsed >= now - timedelta(days=1):
                    return parsed
        except Exception:
            return None

    if isinstance(earnings_dates, (list, tuple)):
        future_dates = [dt for dt in (_as_datetime(item) for item in earnings_dates) if dt and dt >= now - timedelta(days=1)]
        if future_dates:
            return min(future_dates)
    return None


def _flag_from_days(days_to_event: Optional[int]) -> tuple[str, int, str, bool]:
    if days_to_event is None:
        return ("unknown", 0, "No earnings date available", False)
    if days_to_event < 0:
        return ("recent", 15, "Recent results event", False)
    if days_to_event == 0:
        return ("critical", 95, "Results due today", True)
    if days_to_event <= 2:
        return ("high", 85, f"Results due in {days_to_event} day(s)", True)
    if days_to_event <= 5:
        return ("elevated", 65, f"Results due in {days_to_event} day(s)", True)
    if days_to_event <= 10:
        return ("watch", 40, f"Results due in {days_to_event} day(s)", False)
    if days_to_event <= 21:
        return ("monitor", 20, f"Results due in {days_to_event} day(s)", False)
    return ("none", 0, "No near-term results risk", False)


def get_earnings_event_risk(
    ticker: str,
    lookahead_days: int = 14,
    force_refresh: bool = False,
) -> EventRisk:
    normalized = normalize_ticker(ticker)
    cache = _load_cache()
    cached = cache.get(normalized)
    if cached and not force_refresh and _cache_fresh(cached):
        days = cached.get("days_to_event")
        if days is None or days <= lookahead_days or cached.get("risk_level") in {"none", "monitor", "watch", "unknown"}:
            return EventRisk(**cached)

    if yf is None:
        return EventRisk(ticker=normalized, error="yfinance not installed", risk_level="unknown", flag="No event data")

    result = EventRisk(ticker=normalized, fetched_at=datetime.now().isoformat())
    try:
        yf_symbol = get_nse_symbol(normalized)
        instrument = yf.Ticker(yf_symbol)

        event_date = None
        try:
            calendar = instrument.calendar
            event_date = _extract_event_date_from_calendar(calendar)
        except Exception:
            event_date = None

        if event_date is None:
            try:
                earnings_dates = getattr(instrument, "earnings_dates", None)
                if callable(earnings_dates):
                    earnings_dates = earnings_dates
                event_date = _extract_event_date_from_earnings_dates(earnings_dates)
            except Exception:
                event_date = None

        days_to_event = None
        if event_date is not None:
            days_to_event = (event_date.date() - datetime.now().date()).days

        risk_level, risk_score, flag, avoid = _flag_from_days(days_to_event)
        result.event_date = event_date.date().isoformat() if event_date else None
        result.days_to_event = days_to_event
        result.risk_level = risk_level
        result.risk_score = risk_score
        result.flag = flag
        result.should_avoid_new_entries = avoid and (days_to_event is not None and days_to_event <= lookahead_days)
    except Exception as exc:
        result.error = str(exc)
        result.risk_level = "unknown"
        result.flag = "Event data unavailable"

    cache[normalized] = result.__dict__
    _save_cache(cache)
    return result


def get_event_risk_map(
    tickers: list[str],
    lookahead_days: int = 14,
    force_refresh: bool = False,
) -> dict[str, EventRisk]:
    return {
        normalize_ticker(ticker): get_earnings_event_risk(
            ticker,
            lookahead_days=lookahead_days,
            force_refresh=force_refresh,
        )
        for ticker in tickers
    }
