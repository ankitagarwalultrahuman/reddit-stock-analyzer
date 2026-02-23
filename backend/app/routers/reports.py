"""Reports router - wraps dashboard_analytics.py for report data."""

from datetime import date

from fastapi import APIRouter, HTTPException

from dashboard_analytics import (
    get_available_dates,
    get_report_for_date,
    get_recent_reports,
    get_am_pm_reports_for_date,
    load_comparison_for_date,
    generate_todays_actions,
    parse_stock_mentions,
    parse_key_insights_structured,
    parse_report_sections,
    calculate_sentiment_distribution,
    get_weekly_summary,
)

router = APIRouter()


def _serialize_date(d: date) -> str:
    return d.isoformat()


def _get_report_content(report_date: date) -> str:
    """Get report content for a date, raising 404 if not found."""
    report = get_report_for_date(report_date)
    if not report or not report.get("content"):
        raise HTTPException(status_code=404, detail=f"No report found for {report_date}")
    return report["content"]


@router.get("/dates")
async def list_dates():
    dates = get_available_dates()
    return [_serialize_date(d) for d in dates]


# NOTE: weekly-summary must be defined BEFORE {report_date} to avoid path capture
@router.get("/weekly-summary")
async def weekly_summary():
    reports = get_recent_reports()
    if not reports:
        raise HTTPException(status_code=404, detail="No recent reports available")
    summary = get_weekly_summary(reports)
    return {"summary": summary}


@router.get("/{report_date}")
async def get_report(report_date: date):
    report = get_report_for_date(report_date)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "date": _serialize_date(report_date),
        "content": report.get("content", ""),
        "metadata": report.get("metadata", {}),
        "timestamp": report.get("timestamp", ""),
    }


@router.get("/{report_date}/sessions")
async def get_sessions(report_date: date):
    sessions = get_am_pm_reports_for_date(report_date)
    return sessions


@router.get("/{report_date}/actions")
async def get_actions(report_date: date):
    content = _get_report_content(report_date)
    return generate_todays_actions(content)


@router.get("/{report_date}/stocks")
async def get_stocks(report_date: date):
    content = _get_report_content(report_date)
    return parse_stock_mentions(content)


@router.get("/{report_date}/insights")
async def get_insights(report_date: date):
    content = _get_report_content(report_date)
    return parse_key_insights_structured(content)


@router.get("/{report_date}/sections")
async def get_sections(report_date: date):
    content = _get_report_content(report_date)
    return parse_report_sections(content)


@router.get("/{report_date}/sentiment")
async def get_sentiment(report_date: date):
    content = _get_report_content(report_date)
    insights = parse_key_insights_structured(content)
    return calculate_sentiment_distribution(insights)


@router.get("/{report_date}/comparison")
async def get_comparison(report_date: date):
    comparison = load_comparison_for_date(report_date)
    if not comparison:
        return {"has_comparison": False, "content": None}
    return {"has_comparison": True, **comparison} if isinstance(comparison, dict) else {"has_comparison": True, "content": comparison}
