"""News router - wraps news_fetcher.py."""

from fastapi import APIRouter

from news_fetcher import get_news_highlights
from dashboard_analytics import get_available_dates, get_report_for_date

router = APIRouter()


@router.get("/highlights")
async def news_highlights():
    dates = get_available_dates()
    if not dates:
        return {"highlights": [], "market_summary": "", "key_alerts": []}
    report = get_report_for_date(dates[0])
    content = report.get("content", "") if report else ""
    return get_news_highlights(content)
