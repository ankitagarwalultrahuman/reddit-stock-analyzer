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


def get_secret(key: str, default: str = None) -> Optional[str]:
    """
    Get secret from either Streamlit Cloud secrets or environment variables.
    Supports both local development (.env) and Streamlit Cloud deployment.
    """
    # First try Streamlit secrets (for Streamlit Cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # Not running in Streamlit or secrets not available

    # Fall back to environment variables (for local development)
    return os.getenv(key, default)


# Groww API Configuration
# Note: Credentials are loaded lazily in GrowwClient.__init__() to ensure
# Streamlit secrets are available (they aren't accessible at import time)
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
        # Load credentials lazily at runtime (not at import time)
        # This ensures Streamlit secrets are available when running on Streamlit Cloud
        self.api_token = api_token or get_secret("GROWW_API_TOKEN")
        self.api_secret = api_secret or get_secret("GROWW_API_SECRET")
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
# Top holdings for popular mutual fund categories
MF_CATEGORY_HOLDINGS = {
    # Nifty 50 Index Funds - top 20 holdings by weight
    "NIFTY50": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "BHARTIARTL", "SBIN", "KOTAKBANK", "LT",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "AXISBANK", "ITC",
        "WIPRO", "HCLTECH", "TECHM", "ADANIENT", "ADANIPORTS"
    ],
    # Large Cap Funds - typical top holdings
    "LARGE_CAP": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "BHARTIARTL", "SBIN", "KOTAKBANK", "LT",
        "BAJFINANCE", "ITC", "AXISBANK", "MARUTI", "TITAN"
    ],
    # Mid Cap Funds - typical top holdings
    "MID_CAP": [
        "TATAPOWER", "TATAELXSI", "PERSISTENT", "POLYCAB", "ASTRAL",
        "DIXON", "MPHASIS", "COFORGE", "LTIM", "ZOMATO",
        "VOLTAS", "PAGEIND", "JUBLFOOD", "MUTHOOTFIN", "CROMPTON"
    ],
    # Small Cap Funds - typical top holdings
    "SMALL_CAP": [
        "TANLA", "KPITTECH", "ROUTE", "DATAPATTNS", "KAYNES",
        "FINEORG", "RATNAMANI", "CAMPUS", "HAPPSTMNDS", "SONACOMS",
        "CERA", "RKFORGE", "RADICO", "GRINDWELL", "AMBER"
    ],
    # Flexi Cap / Multi Cap Funds
    "FLEXI_CAP": [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
        "BAJFINANCE", "BHARTIARTL", "SBIN", "LT", "KOTAKBANK",
        "TATAPOWER", "TATAELXSI", "POLYCAB", "PERSISTENT", "ZOMATO"
    ],
    # IT Sector Funds
    "IT_SECTOR": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
        "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "TATAELXSI"
    ],
    # Banking & Financial Services Funds
    "BANKING_FINANCE": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
        "BAJFINANCE", "BAJAJFINSV", "HDFC", "INDUSINDBK", "FEDERALBNK"
    ],
    # Pharma & Healthcare Funds
    "PHARMA_HEALTHCARE": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
        "FORTIS", "MAXHEALTH", "BIOCON", "TORNTPHARM", "LUPIN"
    ],
    # Infrastructure Funds
    "INFRASTRUCTURE": [
        "LT", "ADANIPORTS", "ADANIENT", "NTPC", "POWERGRID",
        "GRASIM", "ULTRACEMCO", "JSWSTEEL", "TATASTEEL", "HINDALCO"
    ],
    # Consumption / FMCG Funds
    "CONSUMPTION_FMCG": [
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
        "MARICO", "COLPAL", "GODREJCP", "TATACONSUM", "TITAN"
    ],
}

# Popular mutual fund name to category mapping
MF_NAME_TO_CATEGORY = {
    # Nifty 50 Index Funds
    "UTI NIFTY 50 INDEX": "NIFTY50",
    "HDFC NIFTY 50 INDEX": "NIFTY50",
    "SBI NIFTY INDEX": "NIFTY50",
    "ICICI NIFTY 50 INDEX": "NIFTY50",
    "NIPPON NIFTY 50 INDEX": "NIFTY50",
    "AXIS NIFTY 50 INDEX": "NIFTY50",
    # Large Cap
    "MIRAE ASSET LARGE CAP": "LARGE_CAP",
    "AXIS BLUECHIP": "LARGE_CAP",
    "SBI BLUECHIP": "LARGE_CAP",
    "ICICI BLUECHIP": "LARGE_CAP",
    "HDFC TOP 100": "LARGE_CAP",
    "CANARA ROBECO BLUECHIP": "LARGE_CAP",
    "NIPPON LARGE CAP": "LARGE_CAP",
    # Mid Cap
    "AXIS MIDCAP": "MID_CAP",
    "KOTAK EMERGING EQUITY": "MID_CAP",
    "PGIM INDIA MIDCAP": "MID_CAP",
    "SBI MAGNUM MIDCAP": "MID_CAP",
    "HDFC MID CAP OPPORTUNITIES": "MID_CAP",
    "DSP MIDCAP": "MID_CAP",
    # Small Cap
    "AXIS SMALL CAP": "SMALL_CAP",
    "SBI SMALL CAP": "SMALL_CAP",
    "NIPPON SMALL CAP": "SMALL_CAP",
    "KOTAK SMALL CAP": "SMALL_CAP",
    "HDFC SMALL CAP": "SMALL_CAP",
    "QUANT SMALL CAP": "SMALL_CAP",
    # Flexi / Multi Cap
    "PARAG PARIKH FLEXI CAP": "FLEXI_CAP",
    "UTI FLEXI CAP": "FLEXI_CAP",
    "SBI FLEXI CAP": "FLEXI_CAP",
    "HDFC FLEXI CAP": "FLEXI_CAP",
    "QUANT FLEXI CAP": "FLEXI_CAP",
    # Sectoral - IT
    "ICICI TECHNOLOGY": "IT_SECTOR",
    "SBI TECHNOLOGY": "IT_SECTOR",
    "TATA DIGITAL INDIA": "IT_SECTOR",
    "ADITYA BIRLA DIGITAL INDIA": "IT_SECTOR",
    # Sectoral - Banking
    "ICICI BANKING & FINANCIAL": "BANKING_FINANCE",
    "SBI BANKING & FINANCIAL": "BANKING_FINANCE",
    "NIPPON BANKING": "BANKING_FINANCE",
    "KOTAK BANKING ETF": "BANKING_FINANCE",
    # Sectoral - Pharma
    "SBI HEALTHCARE": "PHARMA_HEALTHCARE",
    "NIPPON PHARMA": "PHARMA_HEALTHCARE",
    "UTI HEALTHCARE": "PHARMA_HEALTHCARE",
    # Sectoral - Infrastructure
    "ICICI INFRASTRUCTURE": "INFRASTRUCTURE",
    "SBI INFRASTRUCTURE": "INFRASTRUCTURE",
    "HDFC INFRASTRUCTURE": "INFRASTRUCTURE",
    # Sectoral - Consumption
    "MIRAE ASSET GREAT CONSUMER": "CONSUMPTION_FMCG",
    "SBI CONSUMPTION": "CONSUMPTION_FMCG",
    "ICICI FMCG": "CONSUMPTION_FMCG",
}

# File for storing MF holdings
MF_PORTFOLIO_FILE = "mf_portfolio.json"


def get_mf_underlying_stocks(mf_name: str) -> list[str]:
    """
    Get underlying stocks for a mutual fund.

    Args:
        mf_name: Name of the mutual fund

    Returns:
        List of stock symbols that are typically held by this fund.
    """
    import json
    mf_upper = mf_name.upper().strip()

    # Check direct mapping first
    for known_name, category in MF_NAME_TO_CATEGORY.items():
        if known_name in mf_upper or mf_upper in known_name:
            return MF_CATEGORY_HOLDINGS.get(category, [])

    # Keyword-based matching
    if "NIFTY" in mf_upper and "50" in mf_upper:
        return MF_CATEGORY_HOLDINGS["NIFTY50"]
    elif "NIFTY" in mf_upper and "NEXT" in mf_upper:
        return MF_CATEGORY_HOLDINGS["LARGE_CAP"]
    elif "LARGE" in mf_upper or "BLUECHIP" in mf_upper:
        return MF_CATEGORY_HOLDINGS["LARGE_CAP"]
    elif "MID" in mf_upper and "CAP" in mf_upper:
        return MF_CATEGORY_HOLDINGS["MID_CAP"]
    elif "SMALL" in mf_upper and "CAP" in mf_upper:
        return MF_CATEGORY_HOLDINGS["SMALL_CAP"]
    elif "FLEXI" in mf_upper or "MULTI" in mf_upper:
        return MF_CATEGORY_HOLDINGS["FLEXI_CAP"]
    elif "IT" in mf_upper or "TECH" in mf_upper or "DIGITAL" in mf_upper:
        return MF_CATEGORY_HOLDINGS["IT_SECTOR"]
    elif "BANK" in mf_upper or "FINANCIAL" in mf_upper:
        return MF_CATEGORY_HOLDINGS["BANKING_FINANCE"]
    elif "PHARMA" in mf_upper or "HEALTH" in mf_upper:
        return MF_CATEGORY_HOLDINGS["PHARMA_HEALTHCARE"]
    elif "INFRA" in mf_upper:
        return MF_CATEGORY_HOLDINGS["INFRASTRUCTURE"]
    elif "FMCG" in mf_upper or "CONSUM" in mf_upper:
        return MF_CATEGORY_HOLDINGS["CONSUMPTION_FMCG"]

    # Default to large cap (most common)
    return MF_CATEGORY_HOLDINGS["LARGE_CAP"]


def load_mf_portfolio() -> list[dict]:
    """Load mutual fund portfolio from JSON file."""
    import json
    from pathlib import Path

    portfolio_path = Path(MF_PORTFOLIO_FILE)
    if not portfolio_path.exists():
        return []

    try:
        with open(portfolio_path, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_mf_portfolio(holdings: list[dict]):
    """Save mutual fund portfolio to JSON file."""
    import json

    with open(MF_PORTFOLIO_FILE, 'w') as f:
        json.dump(holdings, f, indent=2)


def add_mf_holding(name: str, invested_amount: float, current_value: float = 0) -> dict:
    """Add a mutual fund holding to portfolio."""
    holding = {
        "name": name,
        "category": _detect_mf_category(name),
        "invested_amount": invested_amount,
        "current_value": current_value if current_value > 0 else invested_amount,
        "added_at": datetime.now().isoformat(),
    }

    portfolio = load_mf_portfolio()

    # Update if exists, otherwise add
    existing = next((h for h in portfolio if h["name"].upper() == name.upper()), None)
    if existing:
        existing.update(holding)
    else:
        portfolio.append(holding)

    save_mf_portfolio(portfolio)
    return holding


def remove_mf_holding(name: str) -> bool:
    """Remove a mutual fund holding from portfolio."""
    portfolio = load_mf_portfolio()
    name_upper = name.upper()

    new_portfolio = [h for h in portfolio if h["name"].upper() != name_upper]
    if len(new_portfolio) == len(portfolio):
        return False

    save_mf_portfolio(new_portfolio)
    return True


def _detect_mf_category(mf_name: str) -> str:
    """Detect mutual fund category from name."""
    mf_upper = mf_name.upper()

    for known_name, category in MF_NAME_TO_CATEGORY.items():
        if known_name in mf_upper or mf_upper in known_name:
            return category

    # Keyword matching
    if "NIFTY" in mf_upper and "50" in mf_upper:
        return "NIFTY50"
    elif "LARGE" in mf_upper or "BLUECHIP" in mf_upper:
        return "LARGE_CAP"
    elif "MID" in mf_upper:
        return "MID_CAP"
    elif "SMALL" in mf_upper:
        return "SMALL_CAP"
    elif "FLEXI" in mf_upper or "MULTI" in mf_upper:
        return "FLEXI_CAP"
    elif "IT" in mf_upper or "TECH" in mf_upper:
        return "IT_SECTOR"
    elif "BANK" in mf_upper:
        return "BANKING_FINANCE"
    elif "PHARMA" in mf_upper or "HEALTH" in mf_upper:
        return "PHARMA_HEALTHCARE"
    elif "INFRA" in mf_upper:
        return "INFRASTRUCTURE"

    return "FLEXI_CAP"


def analyze_mf_against_sentiment(mf_holdings: list[dict], report_content: str) -> list[dict]:
    """
    Analyze mutual fund holdings against Reddit sentiment.

    Returns:
        List of MF holdings with underlying stock sentiment analysis.
    """
    from portfolio_analyzer import normalize_ticker
    from dashboard_analytics import parse_key_insights_structured, parse_stock_mentions

    # Parse report data
    insights = parse_key_insights_structured(report_content)
    stocks = parse_stock_mentions(report_content)

    # Build sentiment lookup
    discussed_stocks = {}
    for item in insights + stocks:
        ticker = normalize_ticker(item.get("ticker", ""))
        if ticker and ticker not in discussed_stocks:
            discussed_stocks[ticker] = {
                "sentiment": item.get("sentiment", "neutral"),
                "mentions": item.get("total_mentions", 0),
            }

    # Analyze each MF
    analyzed = []
    for mf in mf_holdings:
        underlying = get_mf_underlying_stocks(mf["name"])

        # Count sentiments
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        not_discussed_count = 0
        total_mentions = 0

        underlying_analysis = []
        for stock in underlying:
            normalized = normalize_ticker(stock)
            if normalized in discussed_stocks:
                data = discussed_stocks[normalized]
                sentiment = data["sentiment"]
                mentions = data["mentions"]

                if sentiment == "bullish":
                    bullish_count += 1
                elif sentiment == "bearish":
                    bearish_count += 1
                else:
                    neutral_count += 1

                total_mentions += mentions
                underlying_analysis.append({
                    "stock": stock,
                    "sentiment": sentiment,
                    "mentions": mentions,
                })
            else:
                not_discussed_count += 1
                underlying_analysis.append({
                    "stock": stock,
                    "sentiment": "not_discussed",
                    "mentions": 0,
                })

        # Calculate overall sentiment
        if bullish_count > bearish_count * 2:
            overall_sentiment = "bullish"
        elif bearish_count > bullish_count * 2:
            overall_sentiment = "bearish"
        elif bullish_count > bearish_count:
            overall_sentiment = "slightly_bullish"
        elif bearish_count > bullish_count:
            overall_sentiment = "slightly_bearish"
        else:
            overall_sentiment = "neutral"

        # Calculate risk level
        if bearish_count >= 3:
            risk_level = "HIGH"
        elif bearish_count >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # P&L calculation
        invested = mf.get("invested_amount", 0)
        current = mf.get("current_value", invested)
        pnl = current - invested
        pnl_percent = (pnl / invested * 100) if invested > 0 else 0

        analyzed.append({
            "name": mf["name"],
            "category": mf.get("category", "Unknown"),
            "invested_amount": invested,
            "current_value": current,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "underlying_count": len(underlying),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "not_discussed_count": not_discussed_count,
            "total_mentions": total_mentions,
            "overall_sentiment": overall_sentiment,
            "risk_level": risk_level,
            "underlying_analysis": underlying_analysis,
        })

    return analyzed


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
