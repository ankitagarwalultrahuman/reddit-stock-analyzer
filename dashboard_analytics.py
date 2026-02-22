"""Dashboard analytics module - generates 7-day AI summary using Perplexity API."""

import json
import os
import re
from datetime import datetime, date
from pathlib import Path

from openai import OpenAI
from config import (
    PERPLEXITY_API_KEY, OUTPUT_DIR, WEEKLY_SUMMARY_DAYS,
    SESSION_AM, SESSION_PM
)

# Perplexity API configuration
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar"


def load_reports_by_date() -> dict[date, dict]:
    """
    Scan output folder for report files and group by date.

    Supports both legacy format (report_YYYYMMDD_HHMMSS.txt) and
    new session format (report_YYYYMMDD_AM.txt, report_YYYYMMDD_PM.txt).

    Returns:
        dict with date as key, report data (content, metadata) as value.
        Prefers PM reports over AM reports when both exist.
        Falls back to latest timestamped report for legacy files.
    """
    reports = {}
    output_path = Path(OUTPUT_DIR)

    if not output_path.exists():
        return reports

    # Find all report files
    report_files = list(output_path.glob("report_*.txt"))

    for report_file in report_files:
        # Try new session format first: report_YYYYMMDD_AM.txt or report_YYYYMMDD_PM.txt
        session_match = re.match(r"report_(\d{8})_(AM|PM)\.txt", report_file.name)
        if session_match:
            date_str = session_match.group(1)
            session = session_match.group(2)

            try:
                report_date = datetime.strptime(date_str, "%Y%m%d").date()
                # Use session time: AM = 08:00, PM = 18:00 for ordering
                session_hour = 8 if session == SESSION_AM else 18
                report_time = datetime.strptime(f"{date_str}_{session_hour:02d}0000", "%Y%m%d_%H%M%S")
            except ValueError:
                continue

            # Read the report content
            try:
                content = report_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # Parse metadata from report header
            metadata = parse_report_metadata(content)
            metadata["timestamp"] = report_time
            metadata["filename"] = report_file.name
            metadata["session"] = session

            # Prefer PM over AM, and newer over older
            if report_date not in reports or reports[report_date]["timestamp"] < report_time:
                reports[report_date] = {
                    "content": content,
                    "timestamp": report_time,
                    "filename": report_file.name,
                    "metadata": metadata,
                    "session": session,
                }
            continue

        # Try legacy format: report_YYYYMMDD_HHMMSS.txt
        legacy_match = re.match(r"report_(\d{8})_(\d{6})\.txt", report_file.name)
        if legacy_match:
            date_str = legacy_match.group(1)
            time_str = legacy_match.group(2)

            try:
                report_date = datetime.strptime(date_str, "%Y%m%d").date()
                report_time = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except ValueError:
                continue

            # Read the report content
            try:
                content = report_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # Parse metadata from report header
            metadata = parse_report_metadata(content)
            metadata["timestamp"] = report_time
            metadata["filename"] = report_file.name
            metadata["session"] = None  # Legacy reports don't have session

            # Keep only the latest report per day (session reports take priority)
            if report_date not in reports or (
                reports[report_date].get("session") is None and
                reports[report_date]["timestamp"] < report_time
            ):
                reports[report_date] = {
                    "content": content,
                    "timestamp": report_time,
                    "filename": report_file.name,
                    "metadata": metadata,
                    "session": None,
                }

    return reports


def get_am_pm_reports_for_date(report_date: date) -> dict:
    """
    Get both AM and PM reports for a specific date.

    Args:
        report_date: The date to get reports for

    Returns:
        dict with keys 'am', 'pm', 'has_both', and 'available_sessions'
        Each session key contains report data or None
    """
    output_path = Path(OUTPUT_DIR)
    date_str = report_date.strftime("%Y%m%d")

    result = {
        "am": None,
        "pm": None,
        "has_both": False,
        "available_sessions": [],
    }

    # Load AM report
    am_file = output_path / f"report_{date_str}_AM.txt"
    if am_file.exists():
        try:
            content = am_file.read_text(encoding="utf-8")
            metadata = parse_report_metadata(content)
            metadata["filename"] = am_file.name
            metadata["session"] = SESSION_AM
            result["am"] = {
                "content": content,
                "timestamp": datetime.strptime(f"{date_str}_080000", "%Y%m%d_%H%M%S"),
                "filename": am_file.name,
                "metadata": metadata,
                "session": SESSION_AM,
            }
            result["available_sessions"].append(SESSION_AM)
        except Exception:
            pass

    # Load PM report
    pm_file = output_path / f"report_{date_str}_PM.txt"
    if pm_file.exists():
        try:
            content = pm_file.read_text(encoding="utf-8")
            metadata = parse_report_metadata(content)
            metadata["filename"] = pm_file.name
            metadata["session"] = SESSION_PM
            result["pm"] = {
                "content": content,
                "timestamp": datetime.strptime(f"{date_str}_180000", "%Y%m%d_%H%M%S"),
                "filename": pm_file.name,
                "metadata": metadata,
                "session": SESSION_PM,
            }
            result["available_sessions"].append(SESSION_PM)
        except Exception:
            pass

    # Check for legacy format if no session reports found
    if not result["available_sessions"]:
        legacy_files = list(output_path.glob(f"report_{date_str}_??????.txt"))
        if legacy_files:
            # Get the latest one
            latest_file = max(legacy_files, key=lambda f: f.name)
            try:
                content = latest_file.read_text(encoding="utf-8")
                metadata = parse_report_metadata(content)
                metadata["filename"] = latest_file.name
                metadata["session"] = None
                # Store legacy as "pm" position for backwards compatibility
                result["pm"] = {
                    "content": content,
                    "timestamp": datetime.strptime(
                        latest_file.stem.replace("report_", ""),
                        "%Y%m%d_%H%M%S"
                    ),
                    "filename": latest_file.name,
                    "metadata": metadata,
                    "session": None,
                }
                result["available_sessions"].append("legacy")
            except Exception:
                pass

    result["has_both"] = result["am"] is not None and result["pm"] is not None

    return result


def load_comparison_for_date(report_date: date) -> dict | None:
    """
    Load comparison JSON for a specific date.

    Args:
        report_date: The date to load comparison for

    Returns:
        Comparison data dict or None if not found
    """
    output_path = Path(OUTPUT_DIR)
    date_str = report_date.strftime("%Y%m%d")
    comparison_file = output_path / f"comparison_{date_str}.json"

    if not comparison_file.exists():
        return None

    try:
        with open(comparison_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def parse_report_metadata(content: str) -> dict:
    """Extract metadata from report header."""
    metadata = {
        "data_sources": [],
        "time_window": "",
        "total_posts": 0,
        "total_comments": 0,
        "generated_at": None,
    }

    # Extract Generated timestamp
    gen_match = re.search(r"Generated:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", content)
    if gen_match:
        try:
            metadata["generated_at"] = datetime.strptime(gen_match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Extract Data Sources
    sources_match = re.search(r"Data Sources:\s*(.+)", content)
    if sources_match:
        sources = sources_match.group(1).strip()
        metadata["data_sources"] = [s.strip() for s in sources.split(",")]

    # Extract Time Window
    window_match = re.search(r"Time Window:\s*(.+)", content)
    if window_match:
        metadata["time_window"] = window_match.group(1).strip()

    # Extract Total Posts
    posts_match = re.search(r"Total Posts Analyzed:\s*(\d+)", content)
    if posts_match:
        metadata["total_posts"] = int(posts_match.group(1))

    # Extract Total Comments
    comments_match = re.search(r"Total Comments Analyzed:\s*(\d+)", content)
    if comments_match:
        metadata["total_comments"] = int(comments_match.group(1))

    return metadata


def parse_report_sections(content: str) -> dict[str, str]:
    """Parse report content into sections for styled display."""
    sections = {
        "key_insights": "",
        "most_discussed": "",
        "sector_trends": "",
        "sentiment_summary": "",
        "caution_flags": "",
    }

    # Remove header and footer
    main_content = content

    # Remove header (everything before first ##)
    header_end = content.find("##")
    if header_end != -1:
        main_content = content[header_end:]

    # Remove disclaimer/footer
    disclaimer_start = main_content.find("================================================================================\n                              DISCLAIMER")
    if disclaimer_start != -1:
        main_content = main_content[:disclaimer_start]

    # Extract sections using regex
    section_patterns = {
        "key_insights": r"##\s*TOP\s*\d*\s*KEY\s*INSIGHTS?\s*(.*?)(?=##|$)",
        "most_discussed": r"##\s*MOST\s*DISCUSSED\s*STOCKS?\s*(.*?)(?=##|$)",
        "sector_trends": r"##\s*SECTOR\s*TRENDS?\s*(.*?)(?=##|$)",
        "sentiment_summary": r"##\s*MARKET\s*SENTIMENT\s*SUMMARY\s*(.*?)(?=##|$)",
        "caution_flags": r"##\s*CAUTION\s*FLAGS?\s*(.*?)(?=##|$)",
    }

    for key, pattern in section_patterns.items():
        match = re.search(pattern, main_content, re.DOTALL | re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()

    return sections


def get_weekly_summary(reports: list[dict]) -> str:
    """
    Generate a 7-day AI summary using Claude API.

    Args:
        reports: List of report data dicts (content, metadata) for the last 7 days.

    Returns:
        Formatted weekly summary string.
    """
    if not PERPLEXITY_API_KEY:
        return "API key not configured. Please set PERPLEXITY_API_KEY in your .env file."

    if not reports:
        return "No reports available for weekly summary."

    # Prepare the reports data for the prompt
    reports_text = []
    for report in reports:
        date_str = report["timestamp"].strftime("%A, %B %d, %Y")
        metadata = report.get("metadata", {})
        posts = metadata.get("total_posts", "N/A")
        comments = metadata.get("total_comments", "N/A")

        reports_text.append(f"""
=== REPORT DATE: {date_str} ===
Posts Analyzed: {posts} | Comments Analyzed: {comments}

{report['content']}
""")

    combined_reports = "\n".join(reports_text)

    user_prompt = f"""Analyze the following {len(reports)} daily reports from an Indian stock market Reddit analyzer and provide a comprehensive 7-day summary.

DAILY REPORTS:
{combined_reports}

Please provide a weekly summary in the following format:

## TOP RECURRING STOCKS THIS WEEK
List the stocks that appeared most frequently across the week with:
- Stock ticker
- Number of days mentioned
- Overall sentiment trend (improving/declining/stable)
- Brief summary of weekly discussion

## OVERALL SENTIMENT TREND
- Week's starting sentiment vs ending sentiment
- Key sentiment shifts during the week
- Major events that influenced sentiment

## KEY ACTIONABLE INSIGHTS
- Top 3-5 insights for investors based on the week's discussions
- Emerging opportunities or themes
- Stocks gaining or losing community interest

## PERSISTENT RISK ALERTS
- Risks or concerns mentioned on multiple days
- Ongoing caution flags from the community
- Leverage/speculation warnings

Keep the summary concise but comprehensive. Focus on trends and patterns across the week rather than individual day details."""

    try:
        client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url=PERPLEXITY_BASE_URL
        )

        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert financial analyst specializing in the Indian stock market. Analyze the provided reports and provide a comprehensive weekly summary."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=2048,
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating weekly summary: {e}"


def get_available_dates() -> list[date]:
    """Get list of available dates with reports, sorted descending."""
    reports = load_reports_by_date()
    return sorted(reports.keys(), reverse=True)


def get_report_for_date(report_date: date) -> dict | None:
    """Get the report data for a specific date."""
    reports = load_reports_by_date()
    return reports.get(report_date)


def get_recent_reports(days: int = WEEKLY_SUMMARY_DAYS) -> list[dict]:
    """Get reports from the last N days for weekly summary."""
    reports = load_reports_by_date()
    sorted_dates = sorted(reports.keys(), reverse=True)[:days]
    return [reports[d] for d in sorted_dates]


def parse_stock_mentions(content: str) -> list[dict]:
    """
    Parse MOST DISCUSSED STOCKS section.

    Returns:
        list of dicts with keys: ticker, post_count, comment_count, sentiment, total_mentions
    """
    stocks = []

    # Find the MOST DISCUSSED STOCKS section
    pattern = r"##\s*MOST\s*DISCUSSED\s*STOCKS?\s*(.*?)(?=##|$)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        return stocks

    section = match.group(1)

    # Pattern to match: 1. **TICKER** - X posts, Y comments - Sentiment
    stock_pattern = r"\d+\.\s*\*\*([^*]+)\*\*\s*-\s*(\d+)\s*posts?,\s*(\d+)\s*comments?\s*-\s*([^\n]+)"

    for stock_match in re.finditer(stock_pattern, section, re.IGNORECASE):
        ticker = stock_match.group(1).strip()
        post_count = int(stock_match.group(2))
        comment_count = int(stock_match.group(3))
        sentiment_raw = stock_match.group(4).strip()

        # Normalize sentiment
        sentiment = _normalize_sentiment(sentiment_raw)

        stocks.append({
            "ticker": ticker,
            "post_count": post_count,
            "comment_count": comment_count,
            "sentiment": sentiment,
            "total_mentions": post_count + comment_count,
        })

    return stocks


def _normalize_sentiment(sentiment_raw: str) -> str:
    """Normalize sentiment string to standard categories."""
    sentiment_lower = sentiment_raw.lower()

    if "bullish" in sentiment_lower and "bearish" not in sentiment_lower:
        return "bullish"
    elif "bearish" in sentiment_lower and "bullish" not in sentiment_lower:
        return "bearish"
    elif "neutral" in sentiment_lower:
        return "neutral"
    elif "mixed" in sentiment_lower or ("bullish" in sentiment_lower and "bearish" in sentiment_lower):
        return "mixed"
    elif "uncertain" in sentiment_lower:
        return "mixed"
    else:
        return "neutral"


def parse_key_insights_structured(content: str) -> list[dict]:
    """
    Parse TOP 10 KEY INSIGHTS with full structure.

    Returns:
        list of dicts with keys: rank, ticker, description, post_count, comment_count, sentiment, key_points
    """
    insights = []

    # Find the KEY INSIGHTS section
    pattern = r"##\s*TOP\s*\d*\s*KEY\s*INSIGHTS?\s*(.*?)(?=##|$)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        return insights

    section = match.group(1)

    # Split by numbered items
    insight_blocks = re.split(r'\n(?=\d+\.\s*\*\*)', section)

    for block in insight_blocks:
        if not block.strip():
            continue

        # Match header: 1. **TICKER** - Description
        header_match = re.match(r'(\d+)\.\s*\*\*([^*]+)\*\*\s*-\s*([^\n]+)', block)
        if not header_match:
            continue

        rank = int(header_match.group(1))
        ticker = header_match.group(2).strip()
        description = header_match.group(3).strip()

        # Extract citations
        citations_match = re.search(r'\*\*Citations?:\s*(\d+)\s*posts?,\s*(\d+)\s*comments?\*\*', block)
        post_count = int(citations_match.group(1)) if citations_match else 0
        comment_count = int(citations_match.group(2)) if citations_match else 0

        # Extract sentiment
        sentiment_match = re.search(r'Sentiment:\s*([^\n]+)', block)
        sentiment_raw = sentiment_match.group(1).strip() if sentiment_match else "neutral"
        sentiment = _normalize_sentiment(sentiment_raw)

        # Extract key points
        key_points_match = re.search(r'Key points?:\s*([^\n]+)', block, re.IGNORECASE)
        key_points = key_points_match.group(1).strip() if key_points_match else ""

        insights.append({
            "rank": rank,
            "ticker": ticker,
            "description": description,
            "post_count": post_count,
            "comment_count": comment_count,
            "sentiment": sentiment,
            "key_points": key_points,
            "total_mentions": post_count + comment_count,
        })

    return insights


def parse_caution_flags(content: str) -> list[dict]:
    """
    Parse CAUTION FLAGS section.

    Returns:
        list of dicts with keys: title, description, severity
    """
    flags = []

    # Find the CAUTION FLAGS section
    pattern = r"##\s*CAUTION\s*FLAGS?\s*(.*?)(?=##|={10,}|$)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        return flags

    section = match.group(1)

    # Match numbered items: 1. **Title**: Description
    flag_pattern = r'\d+\.\s*\*\*([^*]+)\*\*:?\s*([^\n]+)'

    for flag_match in re.finditer(flag_pattern, section):
        title = flag_match.group(1).strip()
        description = flag_match.group(2).strip()

        # Determine severity based on keywords
        severity = _determine_severity(title, description)

        flags.append({
            "title": title,
            "description": description,
            "severity": severity,
        })

    return flags


def _determine_severity(title: str, description: str) -> str:
    """Determine severity level based on content."""
    combined = (title + " " + description).lower()

    high_risk_keywords = ["high", "extreme", "danger", "crash", "loss", "leverage", "fomo", "panic"]
    medium_risk_keywords = ["caution", "warning", "volatile", "uncertain", "risk"]

    if any(kw in combined for kw in high_risk_keywords):
        return "high"
    elif any(kw in combined for kw in medium_risk_keywords):
        return "medium"
    else:
        return "low"


def generate_todays_actions(content: str) -> dict:
    """
    Analyze report and generate actionable recommendations.

    Logic:
        - WATCH: Bullish sentiment + mentions > 30
        - CONSIDER: Neutral-to-Bullish + opportunity keywords
        - AVOID: Bearish OR mentioned in caution flags

    Returns:
        dict with keys: watch_list, consider_list, avoid_list, risk_alerts, market_mood, focus_summary
    """
    insights = parse_key_insights_structured(content)
    stocks = parse_stock_mentions(content)
    caution_flags = parse_caution_flags(content)

    watch_list = []
    consider_list = []
    avoid_list = []

    # Combine insights and stocks for analysis
    all_stocks = {s["ticker"]: s for s in stocks}
    for insight in insights:
        ticker = insight["ticker"]
        if ticker not in all_stocks:
            all_stocks[ticker] = insight
        else:
            # Merge data
            all_stocks[ticker].update({
                "description": insight.get("description", ""),
                "key_points": insight.get("key_points", ""),
            })

    # Caution flag tickers (extract from titles/descriptions)
    caution_tickers = set()
    for flag in caution_flags:
        combined = flag["title"] + " " + flag["description"]
        # Simple extraction of potential tickers
        for ticker in all_stocks.keys():
            if ticker.upper() in combined.upper():
                caution_tickers.add(ticker)

    opportunity_keywords = ["opportunity", "buy", "dip", "undervalued", "systematic", "contrarian"]

    for ticker, data in all_stocks.items():
        sentiment = data.get("sentiment", "neutral")
        total_mentions = data.get("total_mentions", 0)
        key_points = data.get("key_points", "").lower()
        description = data.get("description", "").lower()

        reason = data.get("key_points", "") or data.get("description", "")

        # AVOID: Bearish or in caution flags
        if sentiment == "bearish" or ticker in caution_tickers:
            avoid_list.append({
                "ticker": ticker,
                "sentiment": sentiment,
                "mentions": total_mentions,
                "reason": reason[:100] if reason else "High risk or bearish sentiment",
            })
        # WATCH: Bullish with high mentions
        elif sentiment == "bullish" and total_mentions > 30:
            watch_list.append({
                "ticker": ticker,
                "sentiment": sentiment,
                "mentions": total_mentions,
                "reason": reason[:100] if reason else "Strong bullish sentiment with high engagement",
            })
        # CONSIDER: Neutral-to-bullish with opportunity keywords
        elif sentiment in ("neutral", "bullish") and any(kw in key_points or kw in description for kw in opportunity_keywords):
            consider_list.append({
                "ticker": ticker,
                "sentiment": sentiment,
                "mentions": total_mentions,
                "reason": reason[:100] if reason else "Potential buying opportunity identified",
            })
        # Also add bullish stocks with lower mentions to consider
        elif sentiment == "bullish" and total_mentions > 10:
            consider_list.append({
                "ticker": ticker,
                "sentiment": sentiment,
                "mentions": total_mentions,
                "reason": reason[:100] if reason else "Bullish sentiment observed",
            })

    # Sort lists by mentions
    watch_list.sort(key=lambda x: x["mentions"], reverse=True)
    consider_list.sort(key=lambda x: x["mentions"], reverse=True)
    avoid_list.sort(key=lambda x: x["mentions"], reverse=True)

    # Extract risk alerts from caution flags
    risk_alerts = [
        {"title": f["title"], "description": f["description"][:80], "severity": f["severity"]}
        for f in caution_flags[:4]
    ]

    # Determine market mood
    market_mood = _determine_market_mood(content, insights)

    # Generate focus summary
    focus_summary = _generate_focus_summary(market_mood, watch_list, avoid_list, caution_flags)

    return {
        "watch_list": watch_list[:3],
        "consider_list": consider_list[:3],
        "avoid_list": avoid_list[:3],
        "risk_alerts": risk_alerts,
        "market_mood": market_mood,
        "focus_summary": focus_summary,
    }


def _determine_market_mood(content: str, insights: list[dict]) -> str:
    """Determine overall market mood from report."""
    content_lower = content.lower()

    # Check sentiment summary section
    if "overall sentiment: bearish" in content_lower:
        return "bearish"
    elif "overall sentiment: bullish" in content_lower:
        return "bullish"

    # Count sentiment from insights
    sentiments = [i.get("sentiment", "neutral") for i in insights]
    bullish_count = sentiments.count("bullish")
    bearish_count = sentiments.count("bearish")

    if bullish_count > bearish_count + 2:
        return "bullish"
    elif bearish_count > bullish_count + 2:
        return "bearish"
    else:
        return "neutral"


def _generate_focus_summary(market_mood: str, watch_list: list, avoid_list: list, caution_flags: list) -> str:
    """Generate a 2-3 sentence actionable daily focus summary."""
    mood_descriptions = {
        "bullish": "Market sentiment is positive with bullish undertones.",
        "bearish": "Market sentiment is cautious with bearish undertones.",
        "neutral": "Market sentiment is mixed with no clear direction.",
    }

    summary_parts = [mood_descriptions.get(market_mood, mood_descriptions["neutral"])]

    if watch_list:
        top_watch = watch_list[0]["ticker"]
        summary_parts.append(f"Keep an eye on {top_watch} which is showing strong community interest.")

    if avoid_list:
        summary_parts.append(f"Exercise caution with high-volatility plays and leveraged positions.")
    elif caution_flags:
        top_flag = caution_flags[0]["title"]
        summary_parts.append(f"Be aware of {top_flag.lower()} concerns raised by the community.")

    return " ".join(summary_parts)


def calculate_sentiment_distribution(insights: list[dict]) -> dict:
    """
    Count sentiment categories for donut chart.

    Args:
        insights: List of insight dicts with 'sentiment' key

    Returns:
        dict with keys: bullish, bearish, neutral, mixed and their counts
    """
    distribution = {"bullish": 0, "bearish": 0, "neutral": 0, "mixed": 0}

    for insight in insights:
        sentiment = insight.get("sentiment", "neutral")
        if sentiment in distribution:
            distribution[sentiment] += 1
        else:
            distribution["neutral"] += 1

    return distribution


# =============================================================================
# CONFLUENCE SIGNAL ANALYSIS
# =============================================================================

def analyze_confluence_signals(stocks: list[dict], report_content: str = "") -> list[dict]:
    """
    Analyze stocks for confluence signals (sentiment + technicals alignment).

    Args:
        stocks: List of stock dicts from parse_stock_mentions()
        report_content: Full report content for additional context

    Returns:
        List of stocks with confluence analysis
    """
    from stock_history import get_stock_with_technicals

    confluence_results = []

    for stock in stocks:
        ticker = stock.get("ticker", "")
        sentiment = stock.get("sentiment", "neutral")
        mentions = stock.get("total_mentions", 0)

        # Skip low-mention stocks
        if mentions < 5:
            continue

        # Get technical data
        stock_data = get_stock_with_technicals(ticker)

        if not stock_data.get("success") or not stock_data.get("technicals"):
            continue

        technicals = stock_data["technicals"]

        # Calculate confluence score
        confluence_score, aligned_signals = calculate_confluence_score(
            sentiment=sentiment,
            technicals=technicals,
            mentions=mentions
        )

        confluence_results.append({
            "ticker": ticker,
            "sentiment": sentiment,
            "mentions": mentions,
            "post_count": stock.get("post_count", 0),
            "comment_count": stock.get("comment_count", 0),
            "current_price": technicals.get("current_price"),
            "rsi": technicals.get("rsi"),
            "rsi_signal": technicals.get("rsi_signal"),
            "macd_trend": technicals.get("macd_trend"),
            "ma_trend": technicals.get("ma_trend"),
            "technical_score": technicals.get("technical_score"),
            "technical_bias": technicals.get("technical_bias"),
            "volume_signal": technicals.get("volume_signal"),
            "volatility_level": technicals.get("volatility_level"),
            "confluence_score": confluence_score,
            "aligned_signals": aligned_signals,
            "signal_strength": get_signal_strength(confluence_score),
        })

    # Sort by confluence score descending
    confluence_results.sort(key=lambda x: x["confluence_score"], reverse=True)

    return confluence_results


def calculate_confluence_score(sentiment: str, technicals: dict, mentions: int) -> tuple:
    """
    Calculate confluence score based on sentiment and technical alignment.

    Scoring criteria (max 5 points for bullish, min -5 for bearish):

    Bullish confluence:
    1. Sentiment is bullish (+1)
    2. RSI is oversold or near_oversold (+1)
    3. MACD is bullish or bullish_crossover (+1)
    4. MA trend is bullish (+1)
    5. Volume is high (+1)

    Bearish confluence (inverted):
    1. Sentiment is bearish (-1)
    2. RSI is overbought (-1)
    3. MACD is bearish or bearish_crossover (-1)
    4. MA trend is bearish (-1)
    5. Volume is high (confirms bearish) (-1)

    Args:
        sentiment: Reddit sentiment
        technicals: Technical analysis dict
        mentions: Number of mentions

    Returns:
        Tuple of (confluence_score 0-5, list of aligned signals)
    """
    score = 0
    aligned_signals = []

    # Determine if we're looking for bullish or bearish confluence
    is_bullish_sentiment = sentiment == "bullish"
    is_bearish_sentiment = sentiment == "bearish"

    # 1. Sentiment check
    if is_bullish_sentiment:
        score += 1
        aligned_signals.append(f"Bullish sentiment ({mentions} mentions)")
    elif is_bearish_sentiment:
        aligned_signals.append(f"Bearish sentiment ({mentions} mentions)")

    # 2. RSI check
    rsi_signal = technicals.get("rsi_signal", "")
    rsi_value = technicals.get("rsi")

    if is_bullish_sentiment:
        if rsi_signal in ("oversold", "near_oversold"):
            score += 1
            aligned_signals.append(f"RSI {rsi_value} ({rsi_signal})")
    elif is_bearish_sentiment:
        if rsi_signal in ("overbought", "near_overbought"):
            score += 1
            aligned_signals.append(f"RSI {rsi_value} ({rsi_signal})")

    # 3. MACD check
    macd_trend = technicals.get("macd_trend", "")

    if is_bullish_sentiment:
        if macd_trend in ("bullish", "bullish_crossover"):
            score += 1
            aligned_signals.append(f"MACD {macd_trend}")
    elif is_bearish_sentiment:
        if macd_trend in ("bearish", "bearish_crossover"):
            score += 1
            aligned_signals.append(f"MACD {macd_trend}")

    # 4. MA Trend check
    ma_trend = technicals.get("ma_trend", "")

    if is_bullish_sentiment and ma_trend == "bullish":
        score += 1
        aligned_signals.append("MA trend bullish (20>50>200)")
    elif is_bearish_sentiment and ma_trend == "bearish":
        score += 1
        aligned_signals.append("MA trend bearish (20<50<200)")

    # 5. Volume check (confirms the move)
    volume_signal = technicals.get("volume_signal", "")

    if volume_signal == "high":
        score += 1
        volume_ratio = technicals.get("volume_ratio", 0)
        aligned_signals.append(f"High volume ({volume_ratio}x avg)")

    return score, aligned_signals


def get_signal_strength(confluence_score: int) -> str:
    """Convert confluence score to strength label."""
    if confluence_score >= 4:
        return "Strong"
    elif confluence_score >= 3:
        return "Moderate"
    elif confluence_score >= 2:
        return "Weak"
    return "No Signal"


def get_top_confluence_signals(report_content: str, limit: int = 5) -> list[dict]:
    """
    Get top confluence signals from a report.

    Args:
        report_content: Full report content
        limit: Maximum number of signals to return

    Returns:
        List of top confluence signals
    """
    stocks = parse_stock_mentions(report_content)
    insights = parse_key_insights_structured(report_content)

    # Merge insights data into stocks
    insights_by_ticker = {i["ticker"]: i for i in insights}
    for stock in stocks:
        ticker = stock["ticker"]
        if ticker in insights_by_ticker:
            stock["description"] = insights_by_ticker[ticker].get("description", "")
            stock["key_points"] = insights_by_ticker[ticker].get("key_points", "")

    confluence_results = analyze_confluence_signals(stocks, report_content)

    # Filter to only signals with score >= 2
    strong_signals = [s for s in confluence_results if s["confluence_score"] >= 2]

    return strong_signals[:limit]


def store_signals_from_report(report_content: str, report_date: str):
    """
    Extract and store signals from a report for tracking.

    Args:
        report_content: Full report content
        report_date: Date of the report (YYYY-MM-DD)
    """
    from signal_tracker import store_signal, Signal
    import json

    stocks = parse_stock_mentions(report_content)
    confluence_results = analyze_confluence_signals(stocks, report_content)

    for result in confluence_results:
        signal = Signal(
            date=report_date,
            ticker=result["ticker"],
            sentiment=result["sentiment"],
            mention_count=result["mentions"],
            post_count=result.get("post_count", 0),
            comment_count=result.get("comment_count", 0),
            rsi=result.get("rsi"),
            rsi_signal=result.get("rsi_signal"),
            macd_trend=result.get("macd_trend"),
            ma_trend=result.get("ma_trend"),
            technical_score=result.get("technical_score"),
            technical_bias=result.get("technical_bias"),
            price_at_signal=result.get("current_price"),
            confluence_score=result["confluence_score"],
            confluence_signals=json.dumps(result["aligned_signals"]),
        )

        store_signal(signal)


def update_signal_outcomes():
    """
    Update price outcomes for signals that need updating.
    Should be called periodically (e.g., daily via cron).
    """
    from signal_tracker import get_signals_needing_price_update, update_price_outcomes
    from stock_history import get_prices_for_outcomes

    signals_to_update = get_signals_needing_price_update()

    for signal in signals_to_update:
        prices = get_prices_for_outcomes(signal["ticker"], signal["date"])
        if prices:
            update_price_outcomes(signal["ticker"], signal["date"], prices)


def generate_confluence_summary(confluence_signals: list[dict]) -> str:
    """
    Generate a human-readable summary of confluence signals.

    Args:
        confluence_signals: List of confluence signal dicts

    Returns:
        Formatted summary string
    """
    if not confluence_signals:
        return "No strong confluence signals detected today."

    lines = ["## TODAY'S CONFLUENCE SIGNALS", ""]

    strong = [s for s in confluence_signals if s["signal_strength"] == "Strong"]
    moderate = [s for s in confluence_signals if s["signal_strength"] == "Moderate"]

    if strong:
        lines.append("### STRONG SIGNALS (4-5 aligned indicators)")
        for s in strong:
            stars = "\u2b50" * s["confluence_score"]
            lines.append(f"\n**{s['ticker']}** {stars}")
            lines.append(f"  Sentiment: {s['sentiment'].title()} ({s['mentions']} mentions)")
            lines.append(f"  RSI: {s['rsi']} ({s['rsi_signal']})")
            lines.append(f"  MACD: {s['macd_trend']}")
            lines.append(f"  Technical Score: {s['technical_score']}/100")
            lines.append(f"  Aligned: {', '.join(s['aligned_signals'])}")
        lines.append("")

    if moderate:
        lines.append("### MODERATE SIGNALS (3 aligned indicators)")
        for s in moderate:
            stars = "\u2b50" * s["confluence_score"]
            lines.append(f"- **{s['ticker']}** {stars}: {s['sentiment']} sentiment, RSI {s['rsi']}, {s['macd_trend']}")
        lines.append("")

    return "\n".join(lines)
