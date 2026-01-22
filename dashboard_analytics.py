"""Dashboard analytics module - generates 7-day AI summary using Claude API."""

import os
import re
from datetime import datetime, date
from pathlib import Path

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, OUTPUT_DIR, WEEKLY_SUMMARY_DAYS


def load_reports_by_date() -> dict[date, dict]:
    """
    Scan output folder for report files and group by date.

    Returns:
        dict with date as key, report data (content, metadata) as value.
        Only the latest report per day is included.
    """
    reports = {}
    output_path = Path(OUTPUT_DIR)

    if not output_path.exists():
        return reports

    # Find all report files
    report_files = list(output_path.glob("report_*.txt"))

    for report_file in report_files:
        # Extract timestamp from filename: report_YYYYMMDD_HHMMSS.txt
        match = re.match(r"report_(\d{8})_(\d{6})\.txt", report_file.name)
        if not match:
            continue

        date_str = match.group(1)
        time_str = match.group(2)

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

        # Keep only the latest report per day
        if report_date not in reports or reports[report_date]["timestamp"] < report_time:
            reports[report_date] = {
                "content": content,
                "timestamp": report_time,
                "filename": report_file.name,
                "metadata": metadata,
            }

    return reports


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
    if not ANTHROPIC_API_KEY:
        return "API key not configured. Please set ANTHROPIC_API_KEY in your .env file."

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

    prompt = f"""You are an expert financial analyst. Analyze the following {len(reports)} daily reports from an Indian stock market Reddit analyzer and provide a comprehensive 7-day summary.

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
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = ""
        for block in message.content:
            if hasattr(block, 'text'):
                response_text += block.text

        return response_text

    except anthropic.APIError as e:
        return f"Claude API error: {e}"
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
