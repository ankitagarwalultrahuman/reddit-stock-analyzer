"""Signals router - wraps signal_tracker.py and dashboard_analytics.py."""

from datetime import date

from fastapi import APIRouter, Query

from signal_tracker import get_accuracy_stats, get_recent_signals
from dashboard_analytics import get_top_confluence_signals, get_report_for_date

router = APIRouter()


@router.get("/confluence")
async def confluence_signals(
    report_date: date = Query(None),
    limit: int = Query(5, ge=1, le=20),
):
    if report_date is None:
        from dashboard_analytics import get_available_dates
        dates = get_available_dates()
        if not dates:
            return []
        report_date = dates[0]
    report = get_report_for_date(report_date)
    if not report or not report.get("content"):
        return []
    return get_top_confluence_signals(report["content"], limit=limit)


@router.get("/accuracy")
async def accuracy_stats(days: int = Query(30, ge=1, le=365)):
    return get_accuracy_stats(days=days)


@router.get("/recent")
async def recent_signals(
    days: int = Query(7, ge=1, le=90),
    min_confluence: int = Query(0, ge=0),
):
    return get_recent_signals(days=days, min_confluence=min_confluence)
