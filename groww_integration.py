"""
Groww API Integration Module

Fetches portfolio holdings from Groww and provides analysis against Reddit sentiment.
Documentation: https://groww.in/trade-api/docs/python-sdk/portfolio
"""

import os
from pathlib import Path
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env from the project root directory
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# Groww API Configuration
GROWW_API_TOKEN = os.getenv("GROWW_API_TOKEN")
GROWW_API_SECRET = os.getenv("GROWW_API_SECRET")
GROWW_BASE_URL = "https://api.groww.in"


@dataclass
class Holding:
    """Represents a single holding in the portfolio."""
    isin: str
    trading_symbol: str
    quantity: float
    average_price: float
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    day_change: float = 0.0
    day_change_percent: float = 0.0
    current_value: float = 0.0
    invested_value: float = 0.0


class GrowwClient:
    """Groww API client for fetching portfolio data."""

    def __init__(self, api_token: str = None, api_secret: str = None):
        self.api_token = api_token or GROWW_API_TOKEN
        self.api_secret = api_secret or GROWW_API_SECRET
        self.access_token = None
        self.session = requests.Session()
        self._setup_headers()

    def _setup_headers(self):
        """Setup request headers with authentication."""
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "RedditStockAnalyzer/1.0",
        })

    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.api_token and self.api_secret)

    def _get_access_token(self) -> str:
        """Generate fresh access token using API key and secret."""
        if not self.api_token or not self.api_secret:
            raise ValueError("Both GROWW_API_TOKEN and GROWW_API_SECRET required")

        try:
            from growwapi import GrowwAPI
            # Generate fresh access token (expires daily at 6 AM IST)
            access_token = GrowwAPI.get_access_token(
                api_key=self.api_token,
                secret=self.api_secret
            )
            self.access_token = access_token
            return access_token
        except Exception as e:
            print(f"Failed to generate access token: {e}")
            raise

    def get_holdings(self) -> list[Holding]:
        """
        Fetch equity holdings from Groww.

        Returns:
            List of Holding objects with portfolio data.
        """
        if not self.is_configured():
            raise ValueError("Groww API not configured. Set GROWW_API_TOKEN and GROWW_API_SECRET in .env")

        try:
            from growwapi import GrowwAPI

            # Generate fresh access token
            access_token = self._get_access_token()

            # Initialize client with fresh token
            groww = GrowwAPI(access_token)
            response = groww.get_holdings_for_user(timeout=10)

            holdings = []
            for h in response.get("holdings", []):
                holding = Holding(
                    isin=h.get("isin", ""),
                    trading_symbol=h.get("trading_symbol", h.get("tradingSymbol", "")),
                    quantity=float(h.get("quantity", 0)),
                    average_price=float(h.get("average_price", h.get("averagePrice", 0))),
                )
                holding.invested_value = holding.quantity * holding.average_price
                holdings.append(holding)

            return holdings

        except ImportError:
            print("growwapi package not installed. Run: pip install growwapi")
            return []
        except Exception as e:
            error_msg = str(e).lower()
            if "forbidden" in error_msg or "401" in error_msg or "403" in error_msg:
                print(f"Groww API access denied: {e}")
                print("Check your GROWW_API_TOKEN and GROWW_API_SECRET in .env")
            else:
                print(f"Error fetching holdings: {e}")
            return []

    def _get_holdings_direct(self) -> list[Holding]:
        """Direct API call without SDK."""
        url = f"{GROWW_BASE_URL}/v1/api/stocks_portfolio/v1/holdings"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            holdings = []
            for h in data.get("holdings", []):
                holding = Holding(
                    isin=h.get("isin", ""),
                    trading_symbol=h.get("trading_symbol", h.get("tradingSymbol", "")),
                    quantity=float(h.get("quantity", 0)),
                    average_price=float(h.get("average_price", h.get("averagePrice", 0))),
                )
                holding.invested_value = holding.quantity * holding.average_price
                holdings.append(holding)

            return holdings

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []

    def get_ltp(self, trading_symbol: str, exchange: str = "NSE") -> Optional[float]:
        """
        Get Last Traded Price for a symbol using get_quote.

        Args:
            trading_symbol: Stock symbol (e.g., "RELIANCE")
            exchange: Exchange (NSE or BSE)

        Returns:
            Last traded price or None if not found.
        """
        try:
            from growwapi import GrowwAPI

            # Use cached access token or generate new one
            if not self.access_token:
                self._get_access_token()

            groww = GrowwAPI(self.access_token)

            # Use get_quote which returns last_price
            quote = groww.get_quote(
                trading_symbol=trading_symbol,
                exchange=exchange,
                segment=groww.SEGMENT_CASH
            )

            if quote and "last_price" in quote:
                return float(quote["last_price"])
            return None
        except Exception as e:
            # Silently fail for LTP - not critical
            return None

    def get_holdings_with_prices(self) -> list[Holding]:
        """Fetch holdings and enrich with current prices."""
        holdings = self.get_holdings()

        if not holdings:
            return holdings

        print(f"Fetching current prices for {len(holdings)} holdings...")

        for holding in holdings:
            try:
                ltp = self.get_ltp(holding.trading_symbol)
                if ltp:
                    holding.current_price = ltp
                    holding.current_value = holding.quantity * ltp
                    holding.pnl = holding.current_value - holding.invested_value
                    if holding.invested_value > 0:
                        holding.pnl_percent = (holding.pnl / holding.invested_value) * 100
            except Exception as e:
                print(f"  Could not get price for {holding.trading_symbol}: {e}")

        return holdings


def get_portfolio_summary(holdings: list[Holding]) -> dict:
    """
    Generate portfolio summary statistics.

    Returns:
        dict with total_invested, total_current, total_pnl, pnl_percent, holdings_count
    """
    total_invested = sum(h.invested_value for h in holdings)
    total_current = sum(h.current_value for h in holdings if h.current_value > 0)

    # If we don't have current prices, use invested as current
    if total_current == 0:
        total_current = total_invested

    total_pnl = total_current - total_invested
    pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        "total_invested": total_invested,
        "total_current": total_current,
        "total_pnl": total_pnl,
        "pnl_percent": pnl_percent,
        "holdings_count": len(holdings),
        "profitable_count": sum(1 for h in holdings if h.pnl > 0),
        "loss_count": sum(1 for h in holdings if h.pnl < 0),
    }


def analyze_holdings_against_sentiment(holdings: list[Holding], report_content: str) -> list[dict]:
    """
    Analyze each holding against Reddit sentiment.

    Returns:
        List of holdings with sentiment analysis added.
    """
    from portfolio_analyzer import (
        normalize_ticker,
        parse_key_insights_structured,
        parse_stock_mentions,
        parse_caution_flags,
    )
    from dashboard_analytics import parse_key_insights_structured, parse_stock_mentions, parse_caution_flags

    # Parse report data
    insights = parse_key_insights_structured(report_content)
    stocks = parse_stock_mentions(report_content)
    caution_flags = parse_caution_flags(report_content)

    # Build lookup dictionaries
    discussed_stocks = {}

    for insight in insights:
        ticker = normalize_ticker(insight["ticker"])
        discussed_stocks[ticker] = {
            "sentiment": insight.get("sentiment", "neutral"),
            "mentions": insight.get("total_mentions", 0),
            "key_points": insight.get("key_points", ""),
            "description": insight.get("description", ""),
        }

    for stock in stocks:
        ticker = normalize_ticker(stock["ticker"])
        if ticker not in discussed_stocks:
            discussed_stocks[ticker] = {
                "sentiment": stock.get("sentiment", "neutral"),
                "mentions": stock.get("total_mentions", 0),
                "key_points": "",
                "description": "",
            }

    # Extract caution tickers
    caution_tickers = set()
    caution_reasons = {}
    for flag in caution_flags:
        combined = (flag["title"] + " " + flag["description"]).upper()
        for ticker in discussed_stocks.keys():
            if ticker in combined:
                caution_tickers.add(ticker)
                caution_reasons[ticker] = flag["title"]

    # Analyze each holding
    analyzed = []
    for holding in holdings:
        ticker = normalize_ticker(holding.trading_symbol)

        analysis = {
            "trading_symbol": holding.trading_symbol,
            "isin": holding.isin,
            "quantity": holding.quantity,
            "average_price": holding.average_price,
            "current_price": holding.current_price,
            "invested_value": holding.invested_value,
            "current_value": holding.current_value,
            "pnl": holding.pnl,
            "pnl_percent": holding.pnl_percent,
        }

        # Add sentiment data
        if ticker in discussed_stocks:
            data = discussed_stocks[ticker]
            analysis["discussed"] = True
            analysis["sentiment"] = data["sentiment"]
            analysis["mentions"] = data["mentions"]
            analysis["key_points"] = data["key_points"]
            analysis["description"] = data["description"]

            if ticker in caution_tickers:
                analysis["alert"] = True
                analysis["alert_reason"] = caution_reasons.get(ticker, "Mentioned in caution flags")
                analysis["risk_level"] = "HIGH"
            elif data["sentiment"] == "bearish":
                analysis["risk_level"] = "MEDIUM"
            elif data["sentiment"] == "bullish":
                analysis["risk_level"] = "LOW"
            else:
                analysis["risk_level"] = "MEDIUM"
        else:
            analysis["discussed"] = False
            analysis["sentiment"] = "not_discussed"
            analysis["mentions"] = 0
            analysis["risk_level"] = "UNKNOWN"

        # Add action recommendation
        analysis["action"] = _get_action_recommendation(analysis)

        analyzed.append(analysis)

    return analyzed


def _get_action_recommendation(analysis: dict) -> str:
    """Generate action recommendation based on analysis."""
    sentiment = analysis.get("sentiment", "neutral")
    pnl_percent = analysis.get("pnl_percent", 0)
    alert = analysis.get("alert", False)

    if alert:
        return "REVIEW - Risk flagged by community"

    if sentiment == "bearish":
        if pnl_percent < -10:
            return "CONSIDER EXIT - Bearish sentiment + significant loss"
        else:
            return "MONITOR - Bearish sentiment detected"

    if sentiment == "bullish":
        if pnl_percent > 20:
            return "HOLD/BOOK PARTIAL - Strong gains + bullish"
        else:
            return "HOLD - Bullish sentiment"

    if sentiment == "not_discussed":
        if pnl_percent < -15:
            return "REVIEW - Not discussed, significant loss"
        else:
            return "HOLD - No community discussion"

    return "MONITOR"


# Mutual Fund Analysis (using public data)
POPULAR_MF_HOLDINGS = {
    # Large Cap Funds typically hold
    "NIFTY50_STOCKS": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "BHARTIARTL", "SBIN", "KOTAKBANK", "LT",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "AXISBANK", "ITC",
        "WIPRO", "HCLTECH", "TECHM", "ADANIENT", "ADANIPORTS"
    ],
    # Midcap stocks commonly held
    "MIDCAP_STOCKS": [
        "TATAPOWER", "TATAELXSI", "PERSISTENT", "POLYCAB", "ASTRAL",
        "DIXON", "MPHASIS", "COFORGE", "LTIM", "ZOMATO"
    ],
}


def get_mf_underlying_stocks(mf_name: str) -> list[str]:
    """
    Get underlying stocks for a mutual fund.

    Note: This is a simplified mapping. For accurate data,
    integrate with AMFI API or MF factsheets.
    """
    mf_upper = mf_name.upper()

    if "NIFTY" in mf_upper and "50" in mf_upper:
        return POPULAR_MF_HOLDINGS["NIFTY50_STOCKS"]
    elif "LARGE" in mf_upper or "BLUECHIP" in mf_upper:
        return POPULAR_MF_HOLDINGS["NIFTY50_STOCKS"][:15]
    elif "MID" in mf_upper:
        return POPULAR_MF_HOLDINGS["MIDCAP_STOCKS"]
    elif "SMALL" in mf_upper:
        return POPULAR_MF_HOLDINGS["MIDCAP_STOCKS"]  # Placeholder
    else:
        # Default to top holdings
        return POPULAR_MF_HOLDINGS["NIFTY50_STOCKS"][:10]


if __name__ == "__main__":
    # Test the client
    print("Testing Groww Integration...")

    client = GrowwClient()

    if client.is_configured():
        print("API token configured")
        holdings = client.get_holdings()
        print(f"Found {len(holdings)} holdings")
        for h in holdings[:3]:
            print(f"  - {h.trading_symbol}: {h.quantity} @ Rs.{h.average_price}")
    else:
        print("API token not configured. Set GROWW_API_TOKEN in .env")
