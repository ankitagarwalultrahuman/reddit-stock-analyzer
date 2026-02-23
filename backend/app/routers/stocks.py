"""Stocks router - wraps stock_history.py for price data and technicals."""

import pandas as pd
from fastapi import APIRouter, Query

from stock_history import (
    fetch_stock_history,
    get_stock_with_technicals,
    fetch_multiple_stocks,
)

router = APIRouter()


def _df_to_records(df):
    """Convert a DataFrame to a list of dicts with dates as strings."""
    if df is None or df.empty:
        return []
    df = df.copy()
    # Handle both DatetimeIndex and RangeIndex (Date as column)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")
    else:
        df.index = df.index.strftime("%Y-%m-%d")
        return df.reset_index().to_dict(orient="records")


# NOTE: /multiple must be defined BEFORE /{ticker} to avoid path capture
@router.get("/multiple")
async def multiple_stocks(
    tickers: str = Query(..., description="Comma-separated tickers"),
    days: int = Query(30, ge=1, le=365),
):
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    results = fetch_multiple_stocks(ticker_list, days=days)
    return {ticker: _df_to_records(df) for ticker, df in results.items()}


@router.get("/{ticker}/history")
async def stock_history(ticker: str, days: int = Query(30, ge=1, le=365)):
    df = fetch_stock_history(ticker, days=days)
    return _df_to_records(df)


@router.get("/{ticker}/technicals")
async def stock_technicals(ticker: str, days: int = Query(60, ge=1, le=365)):
    result = get_stock_with_technicals(ticker, days=days)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Failed to fetch data")}
    # Convert technicals dataclass to dict if needed
    technicals = result.get("technicals", {})
    if hasattr(technicals, "__dict__"):
        technicals = {k: v for k, v in technicals.__dict__.items() if not k.startswith("_")}
    return {
        "success": True,
        "ticker": ticker,
        "current_price": result.get("current_price"),
        "technicals": technicals,
        "history": _df_to_records(result.get("history")),
    }
