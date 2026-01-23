"""
Stock Movement Analyzer - Analyzes why stocks moved and sends SMS alerts.

Features:
- Monitors portfolio stocks for significant price changes (>2%)
- Uses Perplexity AI to analyze WHY the stock moved (real-time web search)
- Combines news, Reddit sentiment, and technicals for analysis
- Sends concise SMS summaries via Twilio
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Import API keys from config (supports both Streamlit secrets and .env)
from config import PERPLEXITY_API_KEY

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER")

# Movement threshold (percentage)
MOVEMENT_THRESHOLD = 1.0  # Alert if stock moves more than 1%


@dataclass
class StockMovement:
    """Represents a significant stock price movement."""
    ticker: str
    current_price: float
    previous_price: float
    change_percent: float
    direction: str  # "up" or "down"
    volume_ratio: float  # Current vs average volume
    timestamp: datetime


@dataclass
class MovementAnalysis:
    """Analysis result for a stock movement."""
    ticker: str
    change_percent: float
    direction: str
    summary: str  # Short explanation (SMS-friendly)
    detailed_reason: str  # Longer explanation
    confidence: str  # "high", "medium", "low"
    sources: list  # What data sources contributed


def get_twilio_client():
    """Initialize Twilio client."""
    try:
        from twilio.rest import Client
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except ImportError:
        print("Twilio not installed. Run: pip install twilio")
    return None


def is_twilio_configured() -> bool:
    """Check if Twilio is properly configured."""
    return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, USER_PHONE_NUMBER])


def send_sms(message: str, to_number: str = None) -> bool:
    """
    Send SMS via Twilio.

    Args:
        message: Message to send (will be split if >1600 chars)
        to_number: Recipient phone number (defaults to USER_PHONE_NUMBER)

    Returns:
        True if sent successfully
    """
    client = get_twilio_client()
    if not client:
        print("Twilio client not available")
        return False

    to_number = to_number or USER_PHONE_NUMBER
    if not to_number:
        print("No recipient phone number configured")
        return False

    try:
        # Split long messages (SMS limit is ~160 chars, but Twilio handles up to 1600)
        if len(message) > 1600:
            messages = [message[i:i+1600] for i in range(0, len(message), 1600)]
        else:
            messages = [message]

        for msg in messages:
            client.messages.create(
                body=msg,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )

        print(f"SMS sent to {to_number}")
        return True

    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return False


def detect_significant_movements(
    tickers: list[str],
    threshold: float = MOVEMENT_THRESHOLD
) -> list[StockMovement]:
    """
    Detect stocks with significant price movements.

    Args:
        tickers: List of stock symbols to check
        threshold: Minimum percentage change to be considered significant

    Returns:
        List of StockMovement objects for stocks that moved significantly
    """
    from stock_history import get_current_price, fetch_stock_history
    from portfolio_analyzer import normalize_ticker

    movements = []

    for ticker in tickers:
        try:
            normalized = normalize_ticker(ticker)

            # Use get_current_price for real-time prices (not EOD historical data)
            price_data = get_current_price(normalized)

            if not price_data.get("success"):
                print(f"Could not get price for {ticker}: {price_data.get('error')}")
                continue

            current_price = price_data["current_price"]
            previous_price = price_data["previous_close"]
            change_percent = price_data["change_percent"]

            if previous_price == 0:
                continue

            # Check if movement exceeds threshold
            if abs(change_percent) >= threshold:
                # Calculate volume ratio from historical data
                volume_ratio = 1.0
                try:
                    df = fetch_stock_history(normalized, days=10)
                    if not df.empty and 'Volume' in df.columns:
                        current_vol = price_data.get("volume") or float(df['Volume'].iloc[-1])
                        avg_vol = float(df['Volume'].mean())
                        if avg_vol > 0:
                            volume_ratio = current_vol / avg_vol
                except Exception:
                    pass

                movements.append(StockMovement(
                    ticker=normalized,
                    current_price=current_price,
                    previous_price=previous_price,
                    change_percent=round(change_percent, 2),
                    direction="up" if change_percent > 0 else "down",
                    volume_ratio=round(volume_ratio, 2),
                    timestamp=datetime.now()
                ))

        except Exception as e:
            print(f"Error checking {ticker}: {e}")
            continue

    # Sort by absolute change (biggest movers first)
    movements.sort(key=lambda x: abs(x.change_percent), reverse=True)

    return movements


def get_stock_context(ticker: str) -> dict:
    """
    Gather context about a stock for analysis.

    Returns dict with:
    - reddit_sentiment: Recent sentiment from Reddit
    - technicals: Technical indicators
    - news_headlines: Recent news (if available)
    - sector_performance: How the sector is doing
    """
    context = {
        "ticker": ticker,
        "reddit_sentiment": None,
        "technicals": None,
        "sector": None,
        "sector_performance": None,
    }

    # Get technical analysis
    try:
        from stock_history import get_stock_with_technicals
        data = get_stock_with_technicals(ticker, days=30)
        if data.get("success"):
            context["technicals"] = data.get("technicals", {})
    except Exception as e:
        print(f"Could not get technicals for {ticker}: {e}")

    # Get sector info
    try:
        from watchlist_manager import get_sector_for_stock
        sector = get_sector_for_stock(ticker)
        if sector:
            context["sector"] = sector

            # Get sector performance
            from sector_tracker import analyze_sector
            sector_metrics = analyze_sector(sector, max_workers=2)
            context["sector_performance"] = {
                "momentum": sector_metrics.momentum_score,
                "trend": sector_metrics.momentum_trend,
                "avg_return_1d": sector_metrics.avg_return_1d,
            }
    except Exception as e:
        print(f"Could not get sector info for {ticker}: {e}")

    # Try to get Reddit sentiment from recent report
    try:
        from pathlib import Path
        from dashboard_analytics import parse_key_insights_structured

        # Find most recent report
        output_dir = Path("output")
        if output_dir.exists():
            reports = sorted(output_dir.glob("report_*.txt"), reverse=True)
            if reports:
                with open(reports[0], 'r') as f:
                    content = f.read()

                insights = parse_key_insights_structured(content)
                for insight in insights:
                    if ticker.upper() in insight.get("ticker", "").upper():
                        context["reddit_sentiment"] = {
                            "sentiment": insight.get("sentiment", "neutral"),
                            "mentions": insight.get("total_mentions", 0),
                            "key_points": insight.get("key_points", ""),
                        }
                        break
    except Exception as e:
        print(f"Could not get Reddit sentiment for {ticker}: {e}")

    return context


def search_stock_news(ticker: str, company_name: str = None) -> list[dict]:
    """
    Search for recent news about a stock using web search.

    Returns list of news items with title and snippet.
    """
    try:
        import requests

        # Map common tickers to company names for better search
        ticker_to_company = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services TCS",
            "HDFCBANK": "HDFC Bank",
            "INFY": "Infosys",
            "ICICIBANK": "ICICI Bank",
            "SBIN": "State Bank of India SBI",
            "BHARTIARTL": "Bharti Airtel",
            "HINDUNILVR": "Hindustan Unilever HUL",
            "ITC": "ITC Limited",
            "KOTAKBANK": "Kotak Mahindra Bank",
            "LT": "Larsen & Toubro L&T",
            "AXISBANK": "Axis Bank",
            "BAJFINANCE": "Bajaj Finance",
            "MARUTI": "Maruti Suzuki",
            "TATAMOTORS": "Tata Motors",
            "TATASTEEL": "Tata Steel",
            "SUNPHARMA": "Sun Pharma",
            "WIPRO": "Wipro",
            "HCLTECH": "HCL Tech",
            "ADANIENT": "Adani Enterprises",
            "ADANIPORTS": "Adani Ports",
            "ONGC": "ONGC Oil",
            "NTPC": "NTPC Power",
            "POWERGRID": "Power Grid Corporation",
            "COALINDIA": "Coal India",
            "JSWSTEEL": "JSW Steel",
            "HINDALCO": "Hindalco",
            "ULTRACEMCO": "UltraTech Cement",
            "GRASIM": "Grasim Industries",
            "TITAN": "Titan Company",
            "NESTLEIND": "Nestle India",
            "ASIANPAINT": "Asian Paints",
            "BAJAJFINSV": "Bajaj Finserv",
            "TECHM": "Tech Mahindra",
            "DRREDDY": "Dr Reddy's Labs",
            "CIPLA": "Cipla Pharma",
            "BPCL": "BPCL Oil",
            "EICHERMOT": "Eicher Motors",
            "BRITANNIA": "Britannia Industries",
            "DIVISLAB": "Divi's Labs",
            "APOLLOHOSP": "Apollo Hospitals",
            "TATACONSUM": "Tata Consumer",
            "HEROMOTOCO": "Hero MotoCorp",
            "SHRIRAMFIN": "Shriram Finance",
            "M&M": "Mahindra & Mahindra",
            "INDUSINDBK": "IndusInd Bank",
            "SBILIFE": "SBI Life Insurance",
            "HDFCLIFE": "HDFC Life Insurance",
            "BEL": "Bharat Electronics BEL",
            "TRENT": "Trent Westside",
        }

        search_name = company_name or ticker_to_company.get(ticker, ticker)

        # Return empty for now - news will be fetched via Claude's web search
        return []

    except Exception as e:
        print(f"News search failed: {e}")
        return []


def analyze_movement_with_ai(movement: StockMovement, context: dict) -> MovementAnalysis:
    """
    Use Perplexity AI to analyze why a stock moved by searching real-time news.

    Perplexity has built-in web search capability for up-to-date information.

    Args:
        movement: The stock movement to analyze
        context: Additional context (sentiment, technicals, etc.)

    Returns:
        MovementAnalysis with explanation
    """
    # Check if API key is configured
    if not PERPLEXITY_API_KEY:
        print("Perplexity API key not configured")
        raise ValueError("PERPLEXITY_API_KEY not set")

    try:
        from openai import OpenAI

        # Perplexity uses OpenAI-compatible API
        client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )

        # Build the prompt
        direction = "UP" if movement.direction == "up" else "DOWN"
        direction_word = "rose" if movement.direction == "up" else "fell"

        # Map ticker to company name for better search
        company_names = {
            "RELIANCE": "Reliance Industries",
            "TCS": "Tata Consultancy Services",
            "HDFCBANK": "HDFC Bank",
            "INFY": "Infosys",
            "ICICIBANK": "ICICI Bank",
            "SBIN": "State Bank of India",
            "BHARTIARTL": "Bharti Airtel",
            "HINDUNILVR": "Hindustan Unilever",
            "ITC": "ITC Limited",
            "KOTAKBANK": "Kotak Mahindra Bank",
            "AXISBANK": "Axis Bank",
            "BAJFINANCE": "Bajaj Finance",
            "TATAMOTORS": "Tata Motors",
            "SUNPHARMA": "Sun Pharma",
            "WIPRO": "Wipro",
            "ADANIENT": "Adani Enterprises",
            "TITAN": "Titan Company",
            "M&M": "Mahindra and Mahindra",
            "MARUTI": "Maruti Suzuki",
            "LT": "Larsen and Toubro",
            "HCLTECH": "HCL Technologies",
            "TECHM": "Tech Mahindra",
            "ULTRACEMCO": "UltraTech Cement",
            "NESTLEIND": "Nestle India",
            "ASIANPAINT": "Asian Paints",
            "JSWSTEEL": "JSW Steel",
            "TATASTEEL": "Tata Steel",
            "POWERGRID": "Power Grid Corporation",
            "NTPC": "NTPC Limited",
            "ONGC": "Oil and Natural Gas Corporation",
            "COALINDIA": "Coal India",
            "BPCL": "Bharat Petroleum",
            "IOC": "Indian Oil Corporation",
            "GAIL": "GAIL India",
            "HINDALCO": "Hindalco Industries",
            "VEDL": "Vedanta Limited",
            "DRREDDY": "Dr Reddy's Laboratories",
            "CIPLA": "Cipla",
            "DIVISLAB": "Divi's Laboratories",
            "APOLLOHOSP": "Apollo Hospitals",
            "BRITANNIA": "Britannia Industries",
            "DABUR": "Dabur India",
            "MARICO": "Marico",
            "PIDILITIND": "Pidilite Industries",
            "BERGEPAINT": "Berger Paints",
            "HAVELLS": "Havells India",
            "SIEMENS": "Siemens India",
            "ABB": "ABB India",
            "INDUSINDBK": "IndusInd Bank",
            "BANDHANBNK": "Bandhan Bank",
            "FEDERALBNK": "Federal Bank",
            "IDFCFIRSTB": "IDFC First Bank",
            "PNB": "Punjab National Bank",
            "BANKBARODA": "Bank of Baroda",
            "CANBK": "Canara Bank",
            "SBILIFE": "SBI Life Insurance",
            "HDFCLIFE": "HDFC Life Insurance",
            "ICICIGI": "ICICI Lombard",
            "BAJAJFINSV": "Bajaj Finserv",
            "CHOLAFIN": "Cholamandalam Finance",
            "MUTHOOTFIN": "Muthoot Finance",
            "IRFC": "Indian Railway Finance Corporation",
            "IRCTC": "IRCTC",
            "HAL": "Hindustan Aeronautics",
            "BEL": "Bharat Electronics",
            "BHEL": "Bharat Heavy Electricals",
        }

        company_name = company_names.get(movement.ticker, movement.ticker)

        # Get sector info from context
        sector_info = ""
        if context.get("sector"):
            sector_info = f"- Sector: {context['sector']}"
            if context.get("sector_performance"):
                sp = context["sector_performance"]
                sector_info += f" (Sector momentum: {sp.get('momentum', 'N/A')}, Trend: {sp.get('trend', 'N/A')})"

        # Get technical context
        tech_info = ""
        if context.get("technicals"):
            tech = context["technicals"]
            tech_info = f"""
TECHNICAL INDICATORS:
- RSI: {tech.get('rsi', 'N/A')}
- MACD: {tech.get('macd_crossover', 'N/A')}
- Technical Bias: {tech.get('technical_bias', 'N/A')}
- Price vs 50 EMA: {tech.get('price_vs_ema50', 'N/A')}"""

        prompt = f"""{company_name} ({movement.ticker}) on NSE India {direction_word} {abs(movement.change_percent):.1f}% today.

- Previous Close: ₹{movement.previous_price:.2f}
- Current Price: ₹{movement.current_price:.2f}
- Change: {movement.change_percent:+.2f}%
- Volume: {movement.volume_ratio:.1f}x average
{sector_info}

Give me a ONE LINE summary (under 160 characters) explaining why this stock moved, based on news and coverage from the past 72 hours. Just the reason, no preamble."""

        print(f"Calling Perplexity API for {movement.ticker}...")

        # Use Perplexity's sonar-pro model with web search
        response = client.chat.completions.create(
            model="sonar-pro",  # Using sonar-pro for better search results
            messages=[
                {
                    "role": "system",
                    "content": "You are an experienced trader in Indian stock markets, with strong technical and fundamental analysis background. Give a one line summary behind the movement in stock prices by analysing the news and coverage on this stock or related sector and stocks from the past 72 hours. Be direct and concise - no introductions, no formatting, just the key reason in one line."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.1  # Very low temperature for concise factual responses
        )

        # Parse response - expecting a simple one-liner
        response_text = response.choices[0].message.content.strip()
        print(f"Perplexity response received for {movement.ticker}")

        # Clean up the response - remove any markdown, citations, or extra formatting
        # Take the first meaningful line if multiple lines returned
        lines = [l.strip() for l in response_text.split("\n") if l.strip()]

        # Get the main analysis line (skip any that start with "Based on" or similar preambles)
        analysis_line = response_text
        for line in lines:
            # Skip preamble lines
            if line.lower().startswith(("based on", "according to", "here's", "here is", "the ")):
                continue
            # Skip citation-only lines like [1], [2]
            if line.startswith("[") and line.endswith("]"):
                continue
            analysis_line = line
            break

        # Remove citation markers like [1], [2] from the text
        import re
        analysis_line = re.sub(r'\[\d+\]', '', analysis_line).strip()

        # Truncate to 160 chars for SMS
        sms_summary = analysis_line[:160] if analysis_line else f"{movement.ticker} moved {movement.change_percent:+.1f}% today"

        # Use the full response as detailed (cleaned up)
        detailed = re.sub(r'\[\d+\]', '', response_text).strip()

        sources = ["perplexity_search"]
        if context.get("technicals"):
            sources.append("technicals")
        if context.get("reddit_sentiment"):
            sources.append("reddit")
        if context.get("sector_performance"):
            sources.append("sector")

        return MovementAnalysis(
            ticker=movement.ticker,
            change_percent=movement.change_percent,
            direction=movement.direction,
            summary=sms_summary,
            detailed_reason=detailed,
            confidence="high",  # Perplexity with web search is generally reliable
            sources=sources
        )

    except Exception as e:
        error_msg = str(e)
        print(f"AI analysis failed for {movement.ticker}: {error_msg}")
        import traceback
        traceback.print_exc()

        # Provide more helpful error message
        direction_text = "up" if movement.direction == "up" else "down"
        volume_note = "on high volume" if movement.volume_ratio > 1.5 else ""

        # Check for specific error types
        if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
            error_detail = "API key issue - please check PERPLEXITY_API_KEY in secrets"
        elif "rate" in error_msg.lower() or "429" in error_msg:
            error_detail = "Rate limited - try again in a few minutes"
        elif "model" in error_msg.lower() or "404" in error_msg:
            error_detail = "Model not found - API may have changed"
        else:
            error_detail = f"Error: {error_msg[:100]}"

        return MovementAnalysis(
            ticker=movement.ticker,
            change_percent=movement.change_percent,
            direction=movement.direction,
            summary=f"{movement.ticker} {direction_text} {abs(movement.change_percent):.1f}% {volume_note}".strip(),
            detailed_reason=f"Stock moved {movement.change_percent:+.1f}% from ₹{movement.previous_price:.2f} to ₹{movement.current_price:.2f}. {error_detail}. Check moneycontrol.com or economictimes.com for news.",
            confidence="low",
            sources=[]
        )


def analyze_portfolio_movements(
    portfolio_tickers: list[str] = None,
    threshold: float = MOVEMENT_THRESHOLD,
    send_alerts: bool = True
) -> list[MovementAnalysis]:
    """
    Analyze significant movements in portfolio stocks.

    Args:
        portfolio_tickers: List of tickers to check (or fetches from Groww if None)
        threshold: Minimum % change to analyze
        send_alerts: Whether to send SMS alerts

    Returns:
        List of MovementAnalysis results
    """
    # Get portfolio tickers if not provided
    if portfolio_tickers is None:
        try:
            from groww_integration import GrowwClient
            client = GrowwClient()
            if client.is_configured():
                holdings = client.get_holdings()
                portfolio_tickers = [h.trading_symbol for h in holdings]
            else:
                print("Groww not configured. Provide tickers manually.")
                return []
        except Exception as e:
            print(f"Could not fetch portfolio: {e}")
            return []

    if not portfolio_tickers:
        print("No tickers to analyze")
        return []

    print(f"Checking {len(portfolio_tickers)} stocks for significant movements...")

    # Detect significant movements
    movements = detect_significant_movements(portfolio_tickers, threshold)

    if not movements:
        print("No significant movements detected")
        return []

    print(f"Found {len(movements)} significant movements")

    # Analyze each movement
    analyses = []
    for movement in movements:
        print(f"Analyzing {movement.ticker} ({movement.change_percent:+.1f}%)...")

        context = get_stock_context(movement.ticker)
        analysis = analyze_movement_with_ai(movement, context)
        analyses.append(analysis)

    # Send SMS alerts if enabled
    if send_alerts and analyses and is_twilio_configured():
        send_movement_alerts(analyses)

    return analyses


def send_movement_alerts(analyses: list[MovementAnalysis]) -> bool:
    """
    Send SMS alerts for stock movements.

    Args:
        analyses: List of movement analyses to alert on

    Returns:
        True if all alerts sent successfully
    """
    if not analyses:
        return True

    # Build consolidated message
    lines = [f"📊 Stock Alert ({datetime.now().strftime('%H:%M')})"]

    for analysis in analyses[:5]:  # Limit to top 5 movers
        emoji = "📈" if analysis.direction == "up" else "📉"
        lines.append(f"\n{emoji} {analysis.ticker} {analysis.change_percent:+.1f}%")
        lines.append(analysis.summary)

    if len(analyses) > 5:
        lines.append(f"\n+{len(analyses) - 5} more stocks moved significantly")

    message = "\n".join(lines)

    return send_sms(message)


def run_movement_check(
    tickers: list[str] = None,
    threshold: float = MOVEMENT_THRESHOLD
) -> dict:
    """
    Run a complete movement check and analysis.

    Returns dict with results summary.
    """
    start_time = datetime.now()

    analyses = analyze_portfolio_movements(
        portfolio_tickers=tickers,
        threshold=threshold,
        send_alerts=True
    )

    return {
        "timestamp": start_time.isoformat(),
        "stocks_checked": len(tickers) if tickers else "portfolio",
        "movements_found": len(analyses),
        "analyses": [
            {
                "ticker": a.ticker,
                "change": f"{a.change_percent:+.1f}%",
                "direction": a.direction,
                "summary": a.summary,
                "confidence": a.confidence,
            }
            for a in analyses
        ],
        "alerts_sent": is_twilio_configured() and len(analyses) > 0,
    }


# Quick test function
def test_sms():
    """Send a test SMS to verify Twilio configuration."""
    if not is_twilio_configured():
        print("Twilio not configured. Set these in .env:")
        print("  TWILIO_ACCOUNT_SID")
        print("  TWILIO_AUTH_TOKEN")
        print("  TWILIO_PHONE_NUMBER")
        print("  USER_PHONE_NUMBER")
        return False

    return send_sms("📊 Test alert from Reddit Stock Analyzer - Twilio is working!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Sending test SMS...")
        test_sms()
    else:
        # Run on sample stocks
        print("Running movement analysis on NIFTY50 sample...")
        sample_tickers = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
        result = run_movement_check(sample_tickers, threshold=1.0)

        print("\nResults:")
        print(f"  Movements found: {result['movements_found']}")
        for a in result['analyses']:
            print(f"  - {a['ticker']}: {a['change']} - {a['summary']}")
