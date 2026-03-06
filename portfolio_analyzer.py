"""
Portfolio Analyzer Module

Analyzes your portfolio holdings against Reddit sentiment data.

PORTFOLIO INPUT OPTIONS:
1. CSV Upload - Export from Groww/Zerodha and upload
2. Manual Entry - Add holdings via the dashboard
3. Zerodha Kite API - Automated sync (requires Kite Connect subscription)

Note: Groww doesn't offer a public API for retail users.
You'll need to manually export your portfolio as CSV.
"""

import os
import re
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from config import OUTPUT_DIR
from dashboard_analytics import parse_key_insights_structured, parse_stock_mentions, parse_caution_flags

PORTFOLIO_FILE = "portfolio.json"
PORTFOLIO_CSV_FOLDER = "portfolio_imports"
DEFAULT_RISK_LIMITS = {
    "max_single_position_pct": 12.0,
    "max_sector_exposure_pct": 30.0,
    "max_positions": 12,
    "earnings_buffer_days": 7,
}


# Common ticker mappings (Groww names -> NSE symbols)
TICKER_MAPPINGS = {
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE IND": "RELIANCE",
    "RIL": "RELIANCE",
    "TATA CONSULTANCY": "TCS",
    "TATA CONSULTANCY SERVICES": "TCS",
    "HDFC BANK LTD": "HDFCBANK",
    "HDFC BANK": "HDFCBANK",
    "ICICI BANK LTD": "ICICIBANK",
    "ICICI BANK": "ICICIBANK",
    "INFOSYS LTD": "INFY",
    "INFOSYS": "INFY",
    "TATA MOTORS": "TATAMOTORS",
    "TATA POWER": "TATAPOWER",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJAJ FINSERV": "BAJAJFINSV",
    "STATE BANK OF INDIA": "SBIN",
    "SBI": "SBIN",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "HUL": "HINDUNILVR",
    "BHARTI AIRTEL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
    "KOTAK MAHINDRA BANK": "KOTAKBANK",
    "KOTAK BANK": "KOTAKBANK",
    "LARSEN & TOUBRO": "LT",
    "L&T": "LT",
    "ASIAN PAINTS": "ASIANPAINT",
    "MARUTI SUZUKI": "MARUTI",
    "AXIS BANK": "AXISBANK",
    "ITC LTD": "ITC",
    "WIPRO LTD": "WIPRO",
    "WIPRO": "WIPRO",
    "HCLTECH": "HCLTECH",
    "HCL TECHNOLOGIES": "HCLTECH",
    "TECHM": "TECHM",
    "TECH MAHINDRA": "TECHM",
    "ADANI ENTERPRISES": "ADANIENT",
    "ADANI PORTS": "ADANIPORTS",
    "ZOMATO": "ZOMATO",
    "ETERNAL": "ZOMATO",  # Zomato renamed to Eternal
    "NIFTY 50": "NIFTY50",
    "NIFTY50 ETF": "NIFTY50",
    "SILVER ETF": "SILVER",
    "SILVERBEES": "SILVER",
    "GOLD ETF": "GOLD",
    "GOLDBEES": "GOLD",
}


def normalize_ticker(name: str) -> str:
    """Normalize stock name to standard ticker symbol."""
    name_upper = name.upper().strip()

    # Check direct mapping
    if name_upper in TICKER_MAPPINGS:
        return TICKER_MAPPINGS[name_upper]

    # Check if already a ticker
    if len(name_upper) <= 15 and name_upper.isalnum():
        return name_upper

    # Try partial match
    for key, value in TICKER_MAPPINGS.items():
        if key in name_upper or name_upper in key:
            return value

    # Return cleaned version
    return re.sub(r'[^A-Z0-9]', '', name_upper)[:15]


def load_portfolio() -> list[dict]:
    """Load portfolio from JSON file."""
    portfolio_path = Path(PORTFOLIO_FILE)
    if not portfolio_path.exists():
        return []

    try:
        with open(portfolio_path, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_portfolio(holdings: list[dict]):
    """Save portfolio to JSON file."""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(holdings, f, indent=2)


def _merge_risk_limits(risk_limits: Optional[dict] = None) -> dict:
    merged = dict(DEFAULT_RISK_LIMITS)
    if risk_limits:
        merged.update({k: v for k, v in risk_limits.items() if v is not None})
    return merged


def _get_live_price(ticker: str, fallback_price: float = 0) -> float:
    try:
        from stock_history import get_current_price

        quote = get_current_price(ticker)
        if quote.get("success") and quote.get("current_price"):
            return float(quote["current_price"])
    except Exception:
        pass
    return float(fallback_price or 0)


def enrich_holdings_with_market_data(
    holdings: Optional[list[dict]] = None,
    earnings_buffer_days: int = 7,
) -> list[dict]:
    holdings = holdings if holdings is not None else load_portfolio()
    if not holdings:
        return []

    from event_risk import get_event_risk_map
    from watchlist_manager import get_sector_for_stock

    event_map = get_event_risk_map(
        [holding["ticker"] for holding in holdings],
        lookahead_days=max(earnings_buffer_days, 14),
    )

    enriched = []
    for holding in holdings:
        ticker = normalize_ticker(holding.get("ticker", ""))
        quantity = int(holding.get("quantity") or 0)
        avg_price = float(holding.get("avg_price") or 0)
        current_price = _get_live_price(ticker, fallback_price=avg_price)
        invested_value = round(quantity * avg_price, 2)
        market_value = round(quantity * current_price, 2)
        pnl = round(market_value - invested_value, 2)
        pnl_percent = round((pnl / invested_value) * 100, 2) if invested_value > 0 else 0.0
        event_risk = event_map.get(ticker)

        enriched.append({
            **holding,
            "ticker": ticker,
            "sector": get_sector_for_stock(ticker) or "Unknown",
            "current_price": round(current_price, 2),
            "invested_value": invested_value,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "event_risk": event_risk.__dict__ if event_risk else None,
        })

    return enriched


def calculate_portfolio_risk(
    holdings: Optional[list[dict]] = None,
    risk_limits: Optional[dict] = None,
) -> dict:
    limits = _merge_risk_limits(risk_limits)
    enriched = enrich_holdings_with_market_data(
        holdings=holdings,
        earnings_buffer_days=int(limits["earnings_buffer_days"]),
    )
    if not enriched:
        return {
            "summary": {
                "total_value": 0,
                "position_count": 0,
                "largest_position_pct": 0,
                "largest_sector_pct": 0,
                "concentration_hhi": 0,
                "earnings_risk_positions": 0,
            },
            "holdings": [],
            "sector_exposure": [],
            "warnings": [],
            "limits": limits,
        }

    total_value = sum(holding["market_value"] for holding in enriched) or 0.0
    sector_values: dict[str, float] = defaultdict(float)

    for holding in enriched:
        weight = (holding["market_value"] / total_value) * 100 if total_value > 0 else 0.0
        holding["weight_pct"] = round(weight, 2)
        holding["is_overweight"] = weight > float(limits["max_single_position_pct"])
        event_risk = holding.get("event_risk") or {}
        holding["has_earnings_risk"] = bool(
            event_risk.get("days_to_event") is not None
            and event_risk.get("days_to_event") <= int(limits["earnings_buffer_days"])
        )
        sector_values[holding["sector"]] += holding["market_value"]

    sector_rows = []
    for sector, value in sector_values.items():
        exposure_pct = (value / total_value) * 100 if total_value > 0 else 0.0
        sector_rows.append({
            "sector": sector,
            "market_value": round(value, 2),
            "exposure_pct": round(exposure_pct, 2),
            "is_overweight": exposure_pct > float(limits["max_sector_exposure_pct"]),
        })
    sector_rows.sort(key=lambda row: row["exposure_pct"], reverse=True)

    hhi = sum((holding["weight_pct"] / 100) ** 2 for holding in enriched) * 10000
    largest_position_pct = max((holding["weight_pct"] for holding in enriched), default=0)
    largest_sector_pct = max((sector["exposure_pct"] for sector in sector_rows), default=0)
    earnings_risk_positions = sum(1 for holding in enriched if holding["has_earnings_risk"])

    warnings = []
    if largest_position_pct > float(limits["max_single_position_pct"]):
        warnings.append(
            f"Largest position is {largest_position_pct:.1f}% vs cap {float(limits['max_single_position_pct']):.1f}%"
        )
    if largest_sector_pct > float(limits["max_sector_exposure_pct"]):
        warnings.append(
            f"Largest sector is {largest_sector_pct:.1f}% vs cap {float(limits['max_sector_exposure_pct']):.1f}%"
        )
    if len(enriched) > int(limits["max_positions"]):
        warnings.append(f"Portfolio has {len(enriched)} positions vs max {int(limits['max_positions'])}")
    if earnings_risk_positions:
        warnings.append(
            f"{earnings_risk_positions} holding(s) have earnings/event risk inside {int(limits['earnings_buffer_days'])} days"
        )
    if hhi >= 1800:
        warnings.append(f"Portfolio concentration is elevated (HHI {hhi:.0f})")

    return {
        "summary": {
            "total_value": round(total_value, 2),
            "position_count": len(enriched),
            "largest_position_pct": round(largest_position_pct, 2),
            "largest_sector_pct": round(largest_sector_pct, 2),
            "concentration_hhi": round(hhi, 0),
            "earnings_risk_positions": earnings_risk_positions,
        },
        "holdings": sorted(enriched, key=lambda row: row["weight_pct"], reverse=True),
        "sector_exposure": sector_rows,
        "warnings": warnings,
        "limits": limits,
    }


def evaluate_new_position(
    ticker: str,
    proposed_allocation_pct: float,
    portfolio_risk: Optional[dict] = None,
    risk_limits: Optional[dict] = None,
) -> dict:
    limits = _merge_risk_limits(risk_limits)
    snapshot = portfolio_risk or calculate_portfolio_risk(risk_limits=limits)
    from event_risk import get_earnings_event_risk
    from watchlist_manager import get_sector_for_stock

    normalized = normalize_ticker(ticker)
    sector = get_sector_for_stock(normalized) or "Unknown"
    current_holding = next((row for row in snapshot.get("holdings", []) if row["ticker"] == normalized), None)
    current_position_pct = float(current_holding["weight_pct"]) if current_holding else 0.0
    sector_row = next((row for row in snapshot.get("sector_exposure", []) if row["sector"] == sector), None)
    current_sector_pct = float(sector_row["exposure_pct"]) if sector_row else 0.0
    event_risk = get_earnings_event_risk(normalized, lookahead_days=int(limits["earnings_buffer_days"]))

    remaining_name_capacity = max(float(limits["max_single_position_pct"]) - current_position_pct, 0.0)
    remaining_sector_capacity = max(float(limits["max_sector_exposure_pct"]) - current_sector_pct, 0.0)
    recommended_allocation_pct = min(proposed_allocation_pct, remaining_name_capacity, remaining_sector_capacity)

    flags = []
    action = "allow"

    if event_risk.should_avoid_new_entries:
        flags.append(event_risk.flag)
        action = "avoid"
    if current_position_pct >= float(limits["max_single_position_pct"]):
        flags.append(f"Existing position already at {current_position_pct:.1f}%")
        action = "avoid"
    elif proposed_allocation_pct > remaining_name_capacity:
        flags.append(f"Single-name cap leaves {remaining_name_capacity:.1f}% capacity")
        action = "trim"

    if current_sector_pct >= float(limits["max_sector_exposure_pct"]):
        flags.append(f"{sector} exposure already at {current_sector_pct:.1f}%")
        action = "avoid"
    elif proposed_allocation_pct > remaining_sector_capacity:
        flags.append(f"{sector} sector cap leaves {remaining_sector_capacity:.1f}% capacity")
        action = "trim" if action != "avoid" else action

    if snapshot.get("summary", {}).get("position_count", 0) >= int(limits["max_positions"]) and current_holding is None:
        flags.append(f"Portfolio already has {int(snapshot['summary']['position_count'])} positions")
        action = "trim" if action != "avoid" else action

    return {
        "ticker": normalized,
        "sector": sector,
        "portfolio_action": action,
        "portfolio_flags": flags,
        "recommended_allocation_pct": round(max(recommended_allocation_pct, 0.0), 2),
        "current_position_pct": round(current_position_pct, 2),
        "sector_exposure_pct": round(current_sector_pct, 2),
        "event_risk": event_risk.__dict__,
        "limits": limits,
    }


def import_from_csv(csv_path: str) -> list[dict]:
    """
    Import portfolio from CSV file.

    Expected columns (flexible matching):
    - Stock Name / Symbol / Ticker
    - Quantity / Qty / Units
    - Avg Price / Average Price / Buy Price
    - Current Value (optional)
    """
    df = pd.read_csv(csv_path)

    # Normalize column names
    df.columns = [col.lower().strip() for col in df.columns]

    # Find relevant columns
    name_cols = ['stock name', 'symbol', 'ticker', 'name', 'stock', 'scrip']
    qty_cols = ['quantity', 'qty', 'units', 'shares']
    price_cols = ['avg price', 'average price', 'buy price', 'avg', 'price']
    value_cols = ['current value', 'value', 'market value', 'current']

    def find_column(candidates):
        for col in candidates:
            if col in df.columns:
                return col
            for df_col in df.columns:
                if col in df_col:
                    return df_col
        return None

    name_col = find_column(name_cols)
    qty_col = find_column(qty_cols)
    price_col = find_column(price_cols)
    value_col = find_column(value_cols)

    if not name_col:
        raise ValueError("Could not find stock name column in CSV")

    holdings = []
    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() == 'nan':
            continue

        holding = {
            "name": name,
            "ticker": normalize_ticker(name),
            "quantity": int(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0,
            "avg_price": float(row[price_col]) if price_col and pd.notna(row[price_col]) else 0,
            "current_value": float(row[value_col]) if value_col and pd.notna(row[value_col]) else 0,
            "imported_at": datetime.now().isoformat(),
        }
        holdings.append(holding)

    return holdings


def add_holding(ticker: str, quantity: int, avg_price: float) -> dict:
    """Add a single holding to portfolio."""
    holding = {
        "name": ticker,
        "ticker": normalize_ticker(ticker),
        "quantity": quantity,
        "avg_price": avg_price,
        "current_value": 0,
        "added_at": datetime.now().isoformat(),
    }

    portfolio = load_portfolio()

    # Update if exists, otherwise add
    existing = next((h for h in portfolio if h["ticker"] == holding["ticker"]), None)
    if existing:
        existing.update(holding)
    else:
        portfolio.append(holding)

    save_portfolio(portfolio)
    return holding


def remove_holding(ticker: str) -> bool:
    """Remove a holding from portfolio."""
    portfolio = load_portfolio()
    normalized = normalize_ticker(ticker)

    new_portfolio = [h for h in portfolio if h["ticker"] != normalized]
    if len(new_portfolio) == len(portfolio):
        return False

    save_portfolio(new_portfolio)
    return True


def analyze_portfolio_against_sentiment(report_content: str) -> dict:
    """
    Analyze portfolio holdings against today's Reddit sentiment.

    Returns:
        dict with keys:
        - holdings_analysis: list of holdings with sentiment match
        - alerts: holdings that appear in caution flags
        - opportunities: holdings with bullish sentiment
        - concerns: holdings with bearish sentiment
        - not_discussed: holdings not mentioned in report
    """
    portfolio = load_portfolio()
    if not portfolio:
        return {
            "holdings_analysis": [],
            "alerts": [],
            "opportunities": [],
            "concerns": [],
            "not_discussed": [],
            "summary": "No portfolio loaded. Import your holdings first.",
        }

    # Parse report data
    insights = parse_key_insights_structured(report_content)
    stocks = parse_stock_mentions(report_content)
    caution_flags = parse_caution_flags(report_content)

    # Create lookup for discussed stocks
    discussed = {}
    for insight in insights:
        ticker = normalize_ticker(insight["ticker"])
        discussed[ticker] = {
            "sentiment": insight.get("sentiment", "neutral"),
            "mentions": insight.get("total_mentions", 0),
            "key_points": insight.get("key_points", ""),
            "source": "insights",
        }

    for stock in stocks:
        ticker = normalize_ticker(stock["ticker"])
        if ticker not in discussed:
            discussed[ticker] = {
                "sentiment": stock.get("sentiment", "neutral"),
                "mentions": stock.get("total_mentions", 0),
                "key_points": "",
                "source": "stocks",
            }

    # Extract caution tickers
    caution_tickers = set()
    caution_reasons = {}
    for flag in caution_flags:
        combined = (flag["title"] + " " + flag["description"]).upper()
        for ticker in discussed.keys():
            if ticker in combined:
                caution_tickers.add(ticker)
                caution_reasons[ticker] = flag["title"]

    # Analyze each holding
    holdings_analysis = []
    alerts = []
    opportunities = []
    concerns = []
    not_discussed = []

    for holding in portfolio:
        ticker = holding["ticker"]

        analysis = {
            "ticker": ticker,
            "name": holding["name"],
            "quantity": holding["quantity"],
            "avg_price": holding["avg_price"],
        }

        if ticker in discussed:
            data = discussed[ticker]
            analysis["sentiment"] = data["sentiment"]
            analysis["mentions"] = data["mentions"]
            analysis["key_points"] = data["key_points"]
            analysis["discussed"] = True

            if ticker in caution_tickers:
                analysis["alert"] = True
                analysis["alert_reason"] = caution_reasons.get(ticker, "Mentioned in caution flags")
                alerts.append(analysis)
            elif data["sentiment"] == "bullish":
                opportunities.append(analysis)
            elif data["sentiment"] == "bearish":
                concerns.append(analysis)
        else:
            analysis["sentiment"] = "unknown"
            analysis["mentions"] = 0
            analysis["discussed"] = False
            not_discussed.append(analysis)

        holdings_analysis.append(analysis)

    # Generate summary
    summary_parts = []
    if alerts:
        summary_parts.append(f"⚠️ {len(alerts)} holding(s) flagged in caution alerts")
    if opportunities:
        summary_parts.append(f"📈 {len(opportunities)} holding(s) showing bullish sentiment")
    if concerns:
        summary_parts.append(f"📉 {len(concerns)} holding(s) showing bearish sentiment")
    if not_discussed:
        summary_parts.append(f"➖ {len(not_discussed)} holding(s) not discussed today")

    return {
        "holdings_analysis": holdings_analysis,
        "alerts": alerts,
        "opportunities": opportunities,
        "concerns": concerns,
        "not_discussed": not_discussed,
        "summary": " | ".join(summary_parts) if summary_parts else "Portfolio analysis complete.",
        "analyzed_at": datetime.now().isoformat(),
    }


def get_portfolio_recommendations(report_content: str) -> list[dict]:
    """
    Generate personalized recommendations based on portfolio and sentiment.

    Returns list of recommendations with action, ticker, reason.
    """
    analysis = analyze_portfolio_against_sentiment(report_content)
    recommendations = []

    # Alert-based recommendations (high priority)
    for holding in analysis["alerts"]:
        recommendations.append({
            "priority": "HIGH",
            "action": "REVIEW",
            "ticker": holding["ticker"],
            "reason": f"⚠️ {holding.get('alert_reason', 'Flagged in caution alerts')}. Review your position.",
            "current_holding": f"{holding['quantity']} shares @ ₹{holding['avg_price']:.2f}",
        })

    # Bearish holdings
    for holding in analysis["concerns"]:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "MONITOR",
            "ticker": holding["ticker"],
            "reason": f"📉 Bearish sentiment detected. {holding.get('key_points', 'Consider setting stop-loss.')}",
            "current_holding": f"{holding['quantity']} shares @ ₹{holding['avg_price']:.2f}",
        })

    # Bullish holdings (opportunities to add)
    for holding in analysis["opportunities"]:
        recommendations.append({
            "priority": "LOW",
            "action": "CONSIDER ADDING",
            "ticker": holding["ticker"],
            "reason": f"📈 Bullish sentiment. {holding.get('key_points', 'Community is optimistic.')}",
            "current_holding": f"{holding['quantity']} shares @ ₹{holding['avg_price']:.2f}",
        })

    return recommendations


# Zerodha Kite Connect Integration (placeholder)
class KiteConnectIntegration:
    """
    Zerodha Kite Connect API Integration.

    Requirements:
    - Kite Connect subscription (₹2000/month)
    - API key and secret from Kite Developer Console

    Setup:
    1. Sign up at https://developers.kite.trade/
    2. Create an app and get API credentials
    3. Set KITE_API_KEY and KITE_API_SECRET in .env
    """

    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.api_secret = os.getenv("KITE_API_SECRET")
        self.access_token = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def get_holdings(self) -> list[dict]:
        """
        Fetch holdings from Zerodha.

        Note: Requires kiteconnect package: pip install kiteconnect
        """
        if not self.is_configured():
            raise ValueError("Kite Connect not configured. Set KITE_API_KEY and KITE_API_SECRET in .env")

        try:
            from kiteconnect import KiteConnect

            kite = KiteConnect(api_key=self.api_key)
            # Note: You need to handle login flow to get access_token
            # This is a simplified placeholder

            if not self.access_token:
                raise ValueError("Access token not set. Complete login flow first.")

            kite.set_access_token(self.access_token)
            holdings = kite.holdings()

            return [
                {
                    "name": h["tradingsymbol"],
                    "ticker": h["tradingsymbol"],
                    "quantity": h["quantity"],
                    "avg_price": h["average_price"],
                    "current_value": h["last_price"] * h["quantity"],
                    "pnl": h["pnl"],
                }
                for h in holdings
            ]
        except ImportError:
            raise ValueError("kiteconnect package not installed. Run: pip install kiteconnect")


if __name__ == "__main__":
    # Test the module
    print("Portfolio Analyzer Module")
    print("=" * 40)

    # Example: Add some test holdings
    add_holding("RELIANCE", 10, 1450.00)
    add_holding("TCS", 5, 3800.00)
    add_holding("SILVERBEES", 100, 85.00)

    portfolio = load_portfolio()
    print(f"\nLoaded {len(portfolio)} holdings:")
    for h in portfolio:
        print(f"  - {h['ticker']}: {h['quantity']} @ ₹{h['avg_price']}")
