"""
Stock Movement Analyzer - Analyzes why stocks moved and sends SMS alerts.

Features:
- Monitors portfolio stocks for significant price changes (>2%)
- Uses Claude AI to analyze WHY the stock moved
- Combines news, Reddit sentiment, and technicals for analysis
- Sends concise SMS summaries via Twilio
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

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
    from stock_history import fetch_stock_history
    from portfolio_analyzer import normalize_ticker

    movements = []

    for ticker in tickers:
        try:
            normalized = normalize_ticker(ticker)
            df = fetch_stock_history(normalized, days=5)

            if df.empty or len(df) < 2:
                continue

            current_price = float(df['Close'].iloc[-1])
            previous_price = float(df['Close'].iloc[-2])

            if previous_price == 0:
                continue

            change_percent = ((current_price - previous_price) / previous_price) * 100

            # Check if movement exceeds threshold
            if abs(change_percent) >= threshold:
                # Calculate volume ratio if available
                volume_ratio = 1.0
                if 'Volume' in df.columns:
                    current_vol = float(df['Volume'].iloc[-1])
                    avg_vol = float(df['Volume'].mean())
                    if avg_vol > 0:
                        volume_ratio = current_vol / avg_vol

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


def analyze_movement_with_ai(movement: StockMovement, context: dict) -> MovementAnalysis:
    """
    Use Claude AI to analyze why a stock moved.

    Args:
        movement: The stock movement to analyze
        context: Additional context (sentiment, technicals, etc.)

    Returns:
        MovementAnalysis with explanation
    """
    try:
        import anthropic

        client = anthropic.Anthropic()

        # Build the prompt
        direction = "UP" if movement.direction == "up" else "DOWN"

        prompt = f"""Analyze why {movement.ticker} stock moved {direction} {abs(movement.change_percent):.1f}% today.

Stock Data:
- Current Price: ₹{movement.current_price:.2f}
- Previous Close: ₹{movement.previous_price:.2f}
- Change: {movement.change_percent:+.2f}%
- Volume: {movement.volume_ratio:.1f}x average

"""

        if context.get("technicals"):
            tech = context["technicals"]
            prompt += f"""Technical Indicators:
- RSI: {tech.get('rsi', 'N/A')}
- MACD Signal: {tech.get('macd_crossover', 'N/A')}
- Technical Bias: {tech.get('technical_bias', 'N/A')}
- Price vs 50 EMA: {tech.get('price_vs_ema50', 'N/A')}

"""

        if context.get("reddit_sentiment"):
            sent = context["reddit_sentiment"]
            prompt += f"""Reddit Sentiment:
- Sentiment: {sent.get('sentiment', 'N/A')}
- Mentions: {sent.get('mentions', 0)}
- Key Discussion: {sent.get('key_points', 'N/A')[:200]}

"""

        if context.get("sector_performance"):
            sec = context["sector_performance"]
            prompt += f"""Sector ({context.get('sector', 'Unknown')}):
- Sector Momentum: {sec.get('momentum', 'N/A')}
- Sector Trend: {sec.get('trend', 'N/A')}
- Sector 1D Return: {sec.get('avg_return_1d', 'N/A')}%

"""

        prompt += """Based on this data, provide:
1. A SHORT summary (under 150 characters) explaining the likely reason for the move - this will be sent as SMS
2. A more detailed explanation (2-3 sentences)
3. Your confidence level (high/medium/low) in this explanation

Format your response EXACTLY as:
SMS: [your short summary here]
DETAIL: [your detailed explanation here]
CONFIDENCE: [high/medium/low]
"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = response.content[0].text

        sms_summary = ""
        detailed = ""
        confidence = "medium"

        for line in response_text.split("\n"):
            if line.startswith("SMS:"):
                sms_summary = line[4:].strip()[:150]
            elif line.startswith("DETAIL:"):
                detailed = line[7:].strip()
            elif line.startswith("CONFIDENCE:"):
                conf = line[11:].strip().lower()
                if conf in ["high", "medium", "low"]:
                    confidence = conf

        # Fallback if parsing failed
        if not sms_summary:
            sms_summary = f"{movement.ticker} {direction} {abs(movement.change_percent):.1f}% - Check charts for details"

        if not detailed:
            detailed = response_text[:500]

        sources = []
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
            confidence=confidence,
            sources=sources
        )

    except Exception as e:
        print(f"AI analysis failed: {e}")

        # Provide basic analysis without AI
        direction_text = "up" if movement.direction == "up" else "down"
        volume_note = "on high volume" if movement.volume_ratio > 1.5 else ""

        return MovementAnalysis(
            ticker=movement.ticker,
            change_percent=movement.change_percent,
            direction=movement.direction,
            summary=f"{movement.ticker} {direction_text} {abs(movement.change_percent):.1f}% {volume_note}".strip(),
            detailed_reason=f"Stock moved {movement.change_percent:+.1f}% from ₹{movement.previous_price:.2f} to ₹{movement.current_price:.2f}",
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
