"""
Telegram Alerts Module - Sends trading alerts via Telegram bot.

Setup Instructions:
1. Create a bot via @BotFather on Telegram
2. Get your bot token
3. Start a chat with your bot and send any message
4. Get your chat ID via: https://api.telegram.org/bot<TOKEN>/getUpdates
5. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

Usage:
- send_alert("Your message") - sends to configured chat
- send_screener_alert(results) - formats and sends screener results
- send_sector_alert(signals) - formats and sends sector rotation signals
"""

import os
import requests
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Telegram API base URL
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def is_telegram_configured() -> bool:
    """Check if Telegram is properly configured."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_message(
    text: str,
    chat_id: str = None,
    parse_mode: str = "HTML",
    disable_preview: bool = True,
) -> bool:
    """
    Send a message via Telegram.

    Args:
        text: Message text (supports HTML formatting)
        chat_id: Override default chat ID
        parse_mode: "HTML" or "Markdown"
        disable_preview: Disable link previews

    Returns:
        True if sent successfully
    """
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bot token not configured")
        return False

    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not target_chat:
        print("Telegram chat ID not configured")
        return False

    url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)

    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()

        if result.get("ok"):
            return True
        else:
            print(f"Telegram API error: {result.get('description')}")
            return False

    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def send_alert(message: str, title: str = None) -> bool:
    """
    Send a simple alert message.

    Args:
        message: Alert message
        title: Optional title (will be bold)

    Returns:
        True if sent successfully
    """
    if title:
        text = f"<b>{title}</b>\n\n{message}"
    else:
        text = message

    return send_message(text)


def format_screener_results_for_telegram(results: list, strategy_name: str = "") -> str:
    """
    Format screener results for Telegram message.

    Args:
        results: List of ScreenerResult objects
        strategy_name: Name of the strategy used

    Returns:
        Formatted HTML string
    """
    if not results:
        return "No stocks match the screening criteria."

    lines = [
        f"<b>STOCK SCREENER ALERT</b>",
        f"Strategy: {strategy_name or 'Custom'}",
        f"Found: {len(results)} stocks",
        f"Time: {datetime.now().strftime('%H:%M IST')}",
        "",
        "<b>Results:</b>",
    ]

    for r in results[:10]:  # Limit to 10 results
        stars = "" * min(r.score, 5)
        bias_emoji = "" if r.technical_bias == "bullish" else "" if r.technical_bias == "bearish" else ""

        lines.append(f"\n<b>{r.ticker}</b> {stars} {bias_emoji}")
        lines.append(f"  Price: {r.current_price}")
        lines.append(f"  RSI: {r.rsi} | MACD: {r.macd_trend}")
        lines.append(f"  <i>{', '.join(r.matched_criteria[:2])}</i>")

    return "\n".join(lines)


def send_screener_alert(results: list, strategy_name: str = "") -> bool:
    """
    Send screener results as a Telegram alert.

    Args:
        results: List of ScreenerResult objects
        strategy_name: Name of the strategy

    Returns:
        True if sent successfully
    """
    if not results:
        return True  # Nothing to send

    text = format_screener_results_for_telegram(results, strategy_name)
    return send_message(text)


def format_sector_rotation_for_telegram(signals: dict) -> str:
    """
    Format sector rotation signals for Telegram.

    Args:
        signals: Dict from get_sector_rotation_signals()

    Returns:
        Formatted HTML string
    """
    lines = [
        "<b>SECTOR ROTATION ALERT</b>",
        f"Time: {datetime.now().strftime('%H:%M IST')}",
        "",
    ]

    # Gaining momentum
    gaining = signals.get("gaining_momentum", [])
    if gaining:
        lines.append("<b>Gaining Momentum:</b>")
        for sector, score, ret in gaining[:3]:
            lines.append(f"  {sector}: {score:.0f} pts ({ret:+.1f}%)")
        lines.append("")

    # Losing momentum
    losing = signals.get("losing_momentum", [])
    if losing:
        lines.append("<b>Losing Momentum:</b>")
        for sector, score, ret in losing[:3]:
            lines.append(f"  {sector}: {score:.0f} pts ({ret:+.1f}%)")
        lines.append("")

    # Recommendations
    recs = signals.get("recommendations", [])
    if recs:
        lines.append("<b>Recommendations:</b>")
        for rec in recs[:3]:
            lines.append(f"  {rec}")

    return "\n".join(lines)


def send_sector_alert(signals: dict) -> bool:
    """
    Send sector rotation signals as Telegram alert.

    Args:
        signals: Dict from get_sector_rotation_signals()

    Returns:
        True if sent successfully
    """
    text = format_sector_rotation_for_telegram(signals)
    return send_message(text)


def format_confluence_signal_for_telegram(signal: dict) -> str:
    """
    Format a single confluence signal for Telegram.

    Args:
        signal: Confluence signal dict

    Returns:
        Formatted HTML string
    """
    stars = "" * signal.get("confluence_score", 0)
    sentiment_emoji = "" if signal.get("sentiment") == "bullish" else "" if signal.get("sentiment") == "bearish" else ""

    lines = [
        f"<b>CONFLUENCE SIGNAL: {signal['ticker']}</b> {stars}",
        "",
        f"Sentiment: {signal.get('sentiment', 'N/A').title()} {sentiment_emoji}",
        f"Mentions: {signal.get('mentions', 0)}",
        f"Price: {signal.get('current_price', 'N/A')}",
        f"RSI: {signal.get('rsi', 'N/A')} ({signal.get('rsi_signal', 'N/A')})",
        f"MACD: {signal.get('macd_trend', 'N/A')}",
        f"Tech Score: {signal.get('technical_score', 'N/A')}/100",
        "",
        "<b>Aligned Signals:</b>",
    ]

    for s in signal.get("aligned_signals", []):
        lines.append(f"  {s}")

    return "\n".join(lines)


def send_confluence_alert(signal: dict) -> bool:
    """
    Send a confluence signal alert.

    Args:
        signal: Confluence signal dict

    Returns:
        True if sent successfully
    """
    text = format_confluence_signal_for_telegram(signal)
    return send_message(text)


def send_daily_summary(
    screener_results: list = None,
    sector_signals: dict = None,
    confluence_signals: list = None,
) -> bool:
    """
    Send a comprehensive daily summary.

    Args:
        screener_results: Results from stock screener
        sector_signals: Signals from sector tracker
        confluence_signals: Confluence signals from Reddit analysis

    Returns:
        True if sent successfully
    """
    lines = [
        "<b>DAILY MARKET SUMMARY</b>",
        f"{datetime.now().strftime('%A, %B %d, %Y')}",
        "",
    ]

    # Screener highlights
    if screener_results:
        lines.append("<b>Top Screener Picks:</b>")
        for r in screener_results[:5]:
            lines.append(f"  {r.ticker}: RSI {r.rsi}, {r.macd_trend}")
        lines.append("")

    # Sector highlights
    if sector_signals:
        gaining = sector_signals.get("gaining_momentum", [])
        if gaining:
            top_sector = gaining[0]
            lines.append(f"<b>Hot Sector:</b> {top_sector[0]} (+{top_sector[2]:.1f}%)")
            lines.append("")

    # Confluence highlights
    if confluence_signals:
        strong = [s for s in confluence_signals if s.get("confluence_score", 0) >= 4]
        if strong:
            lines.append("<b>Strong Confluence Signals:</b>")
            for s in strong[:3]:
                lines.append(f"  {s['ticker']}: {s['sentiment']} ({s['confluence_score']} aligned)")
            lines.append("")

    if len(lines) <= 3:
        lines.append("No significant signals today.")

    text = "\n".join(lines)
    return send_message(text)


def send_price_alert(ticker: str, current_price: float, condition: str) -> bool:
    """
    Send a price alert for a specific stock.

    Args:
        ticker: Stock ticker
        current_price: Current price
        condition: Alert condition description

    Returns:
        True if sent successfully
    """
    text = f"""<b>PRICE ALERT: {ticker}</b>

Price: {current_price}
Condition: {condition}
Time: {datetime.now().strftime('%H:%M IST')}"""

    return send_message(text)


def test_telegram_connection() -> dict:
    """
    Test Telegram connection and return bot info.

    Returns:
        Dict with bot info or error message
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"success": False, "error": "Bot token not configured"}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        if result.get("ok"):
            bot_info = result.get("result", {})
            return {
                "success": True,
                "bot_name": bot_info.get("first_name"),
                "bot_username": bot_info.get("username"),
                "chat_id_configured": bool(TELEGRAM_CHAT_ID),
            }
        else:
            return {"success": False, "error": result.get("description")}

    except Exception as e:
        return {"success": False, "error": str(e)}


# Convenience function for quick alerts
def alert(message: str) -> bool:
    """Quick alert function."""
    return send_alert(message)
