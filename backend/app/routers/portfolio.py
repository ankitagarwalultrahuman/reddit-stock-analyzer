"""Portfolio router - wraps portfolio_analyzer.py and groww_integration.py."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_analyzer import (
    load_portfolio,
    add_holding,
    remove_holding,
    analyze_portfolio_against_sentiment,
)
from dashboard_analytics import get_report_for_date, get_available_dates

router = APIRouter()


class HoldingInput(BaseModel):
    ticker: str
    quantity: int
    avg_price: float


@router.get("/holdings")
async def get_holdings():
    return load_portfolio()


@router.post("/holdings")
async def create_holding(body: HoldingInput):
    result = add_holding(body.ticker, body.quantity, body.avg_price)
    return result


@router.delete("/holdings/{ticker}")
async def delete_holding(ticker: str):
    success = remove_holding(ticker)
    if not success:
        raise HTTPException(status_code=404, detail=f"Holding {ticker} not found")
    return {"success": True}


@router.get("/analysis")
async def portfolio_analysis():
    """Analyze portfolio against latest report sentiment."""
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="No reports available")
    report = get_report_for_date(dates[0])
    if not report or not report.get("content"):
        raise HTTPException(status_code=404, detail="No report content")
    result = analyze_portfolio_against_sentiment(report["content"])
    return result


@router.get("/groww/holdings")
async def groww_holdings():
    try:
        from groww_integration import GrowwClient
        client = GrowwClient()
        if not client.is_configured():
            raise HTTPException(status_code=400, detail="Groww API not configured")
        holdings = client.get_holdings_with_prices()
        return [
            {
                "trading_symbol": h.trading_symbol,
                "quantity": h.quantity,
                "average_price": h.average_price,
                "current_price": h.current_price,
                "pnl": h.pnl,
                "pnl_percent": h.pnl_percent,
                "current_value": h.current_value,
                "invested_value": h.invested_value,
            }
            for h in holdings
        ]
    except ImportError:
        raise HTTPException(status_code=400, detail="Groww integration not available")


@router.get("/groww/analysis")
async def groww_analysis():
    try:
        from groww_integration import GrowwClient
        client = GrowwClient()
        if not client.is_configured():
            raise HTTPException(status_code=400, detail="Groww API not configured")
        holdings = client.get_holdings_with_prices()
        dates = get_available_dates()
        if not dates:
            raise HTTPException(status_code=404, detail="No reports available")
        report = get_report_for_date(dates[0])
        if not report:
            raise HTTPException(status_code=404, detail="No report content")
        tickers = [h.trading_symbol for h in holdings]
        analysis = analyze_portfolio_against_sentiment(report["content"])
        return analysis
    except ImportError:
        raise HTTPException(status_code=400, detail="Groww integration not available")
