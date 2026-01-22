#!/usr/bin/env python3
"""
Comparison Generator for AM/PM Reddit Stock Analysis Reports

Compares morning (AM) and evening (PM) reports to generate:
- New stocks appearing in PM
- Stocks that dropped off in PM
- Sentiment changes
- Volume changes (mention count differences)
- Market mood shift description
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import (
    OUTPUT_DIR, SESSION_AM, SESSION_PM,
    IST_UTC_OFFSET_HOURS, VOLUME_CHANGE_THRESHOLD
)
from dashboard_analytics import (
    parse_stock_mentions,
    parse_key_insights_structured,
    _determine_market_mood,
    _normalize_sentiment,
)


def get_ist_today() -> str:
    """Get today's date string in YYYYMMDD format based on IST."""
    ist = timezone(timedelta(hours=IST_UTC_OFFSET_HOURS))
    return datetime.now(ist).strftime('%Y%m%d')


def load_report(date_str: str, session: str) -> dict | None:
    """
    Load a report file for a specific date and session.

    Args:
        date_str: Date in YYYYMMDD format
        session: Either 'AM' or 'PM'

    Returns:
        dict with 'content' and 'path' keys, or None if not found
    """
    filename = f"report_{date_str}_{session}.txt"
    filepath = Path(OUTPUT_DIR) / filename

    if not filepath.exists():
        return None

    try:
        content = filepath.read_text(encoding='utf-8')
        return {
            'content': content,
            'path': str(filepath),
            'session': session,
            'date': date_str,
        }
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None


def extract_stocks_data(content: str) -> dict:
    """
    Extract stock data from report content.

    Returns:
        dict mapping ticker -> {sentiment, mentions, post_count, comment_count}
    """
    stocks = {}

    # Get data from MOST DISCUSSED STOCKS section
    stock_mentions = parse_stock_mentions(content)
    for stock in stock_mentions:
        ticker = stock['ticker']
        stocks[ticker] = {
            'sentiment': stock['sentiment'],
            'mentions': stock['total_mentions'],
            'post_count': stock['post_count'],
            'comment_count': stock['comment_count'],
        }

    # Also get data from KEY INSIGHTS (may have additional stocks)
    insights = parse_key_insights_structured(content)
    for insight in insights:
        ticker = insight['ticker']
        if ticker not in stocks:
            stocks[ticker] = {
                'sentiment': insight['sentiment'],
                'mentions': insight['total_mentions'],
                'post_count': insight['post_count'],
                'comment_count': insight['comment_count'],
            }
        else:
            # Update with insight data if it has more info
            if insight['total_mentions'] > stocks[ticker]['mentions']:
                stocks[ticker]['mentions'] = insight['total_mentions']

    return stocks


def compare_reports(am_report: dict, pm_report: dict) -> dict:
    """
    Generate comparison data between AM and PM reports.

    Args:
        am_report: Morning report dict with 'content' key
        pm_report: Evening report dict with 'content' key

    Returns:
        Comparison data dict
    """
    am_content = am_report['content']
    pm_content = pm_report['content']
    date_str = am_report['date']

    # Extract stock data from both reports
    am_stocks = extract_stocks_data(am_content)
    pm_stocks = extract_stocks_data(pm_content)

    am_tickers = set(am_stocks.keys())
    pm_tickers = set(pm_stocks.keys())

    # Find new stocks in PM
    new_stocks_pm = []
    for ticker in pm_tickers - am_tickers:
        stock_data = pm_stocks[ticker]
        new_stocks_pm.append({
            'ticker': ticker,
            'sentiment': stock_data['sentiment'],
            'mentions': stock_data['mentions'],
        })
    new_stocks_pm.sort(key=lambda x: x['mentions'], reverse=True)

    # Find stocks that dropped off in PM
    removed_stocks_pm = []
    for ticker in am_tickers - pm_tickers:
        stock_data = am_stocks[ticker]
        removed_stocks_pm.append({
            'ticker': ticker,
            'sentiment': stock_data['sentiment'],
            'mentions': stock_data['mentions'],
        })
    removed_stocks_pm.sort(key=lambda x: x['mentions'], reverse=True)

    # Find sentiment changes
    sentiment_changes = []
    common_tickers = am_tickers & pm_tickers
    for ticker in common_tickers:
        am_sentiment = am_stocks[ticker]['sentiment']
        pm_sentiment = pm_stocks[ticker]['sentiment']

        if am_sentiment != pm_sentiment:
            change_direction = _get_sentiment_change_direction(am_sentiment, pm_sentiment)
            sentiment_changes.append({
                'ticker': ticker,
                'am_sentiment': am_sentiment,
                'pm_sentiment': pm_sentiment,
                'change_direction': change_direction,
            })
    sentiment_changes.sort(key=lambda x: x['ticker'])

    # Find volume changes (mention count changes > threshold)
    volume_changes = []
    for ticker in common_tickers:
        am_mentions = am_stocks[ticker]['mentions']
        pm_mentions = pm_stocks[ticker]['mentions']

        if am_mentions > 0:
            change_percent = ((pm_mentions - am_mentions) / am_mentions) * 100
        elif pm_mentions > 0:
            change_percent = 100.0  # New mentions from 0
        else:
            continue

        if abs(change_percent) >= VOLUME_CHANGE_THRESHOLD:
            volume_changes.append({
                'ticker': ticker,
                'am_mentions': am_mentions,
                'pm_mentions': pm_mentions,
                'change_percent': round(change_percent, 1),
            })
    volume_changes.sort(key=lambda x: abs(x['change_percent']), reverse=True)

    # Determine market mood shift
    am_insights = parse_key_insights_structured(am_content)
    pm_insights = parse_key_insights_structured(pm_content)
    am_mood = _determine_market_mood(am_content, am_insights)
    pm_mood = _determine_market_mood(pm_content, pm_insights)

    mood_shift = {
        'am_mood': am_mood,
        'pm_mood': pm_mood,
        'shift_description': _generate_mood_shift_description(am_mood, pm_mood),
    }

    # Format date for output
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    comparison = {
        'date': formatted_date,
        'summary': {
            'total_new_stocks': len(new_stocks_pm),
            'total_removed_stocks': len(removed_stocks_pm),
            'total_sentiment_changes': len(sentiment_changes),
            'total_volume_changes': len(volume_changes),
        },
        'new_stocks_pm': new_stocks_pm,
        'removed_stocks_pm': removed_stocks_pm,
        'sentiment_changes': sentiment_changes,
        'volume_changes': volume_changes,
        'market_mood_shift': mood_shift,
    }

    return comparison


def _get_sentiment_change_direction(am_sentiment: str, pm_sentiment: str) -> str:
    """Determine if sentiment change is improving, declining, or neutral."""
    sentiment_rank = {
        'bearish': 1,
        'mixed': 2,
        'neutral': 3,
        'bullish': 4,
    }

    am_rank = sentiment_rank.get(am_sentiment, 2)
    pm_rank = sentiment_rank.get(pm_sentiment, 2)

    if pm_rank > am_rank:
        return 'improving'
    elif pm_rank < am_rank:
        return 'declining'
    else:
        return 'stable'


def _generate_mood_shift_description(am_mood: str, pm_mood: str) -> str:
    """Generate human-readable description of mood shift."""
    if am_mood == pm_mood:
        return f"Market sentiment remained {am_mood} throughout the day"

    mood_descriptions = {
        ('bearish', 'neutral'): "Market recovered from morning concerns",
        ('bearish', 'bullish'): "Significant recovery - market turned bullish from morning bearishness",
        ('neutral', 'bullish'): "Market gained positive momentum during the day",
        ('neutral', 'bearish'): "Market turned cautious as the day progressed",
        ('bullish', 'neutral'): "Morning optimism cooled down to neutral by evening",
        ('bullish', 'bearish'): "Sharp reversal - market turned bearish from morning optimism",
    }

    return mood_descriptions.get(
        (am_mood, pm_mood),
        f"Market sentiment shifted from {am_mood} to {pm_mood}"
    )


def save_comparison(comparison: dict, date_str: str) -> str:
    """
    Save comparison data to JSON file.

    Args:
        comparison: Comparison data dict
        date_str: Date in YYYYMMDD format

    Returns:
        Path to saved file
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{OUTPUT_DIR}/comparison_{date_str}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    return filename


def generate_comparison_for_date(date_str: str) -> dict | None:
    """
    Generate comparison for a specific date.

    Args:
        date_str: Date in YYYYMMDD format

    Returns:
        Comparison dict if both reports exist, None otherwise
    """
    am_report = load_report(date_str, SESSION_AM)
    pm_report = load_report(date_str, SESSION_PM)

    if not am_report:
        print(f"AM report not found for {date_str}")
        return None

    if not pm_report:
        print(f"PM report not found for {date_str}")
        return None

    print(f"Comparing reports for {date_str}:")
    print(f"  AM: {am_report['path']}")
    print(f"  PM: {pm_report['path']}")

    comparison = compare_reports(am_report, pm_report)
    return comparison


def main():
    """Main entry point for comparison generator."""
    parser = argparse.ArgumentParser(
        description="Generate AM vs PM comparison for Reddit Stock Analysis reports"
    )
    parser.add_argument(
        "--date",
        help="Date to compare in YYYYMMDD format (default: today in IST)",
        default=None
    )
    args = parser.parse_args()

    date_str = args.date or get_ist_today()

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║         AM vs PM COMPARISON GENERATOR                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    print(f"Target date: {date_str}")

    comparison = generate_comparison_for_date(date_str)

    if comparison is None:
        print("\nComparison could not be generated. Ensure both AM and PM reports exist.")
        return

    # Save comparison
    output_file = save_comparison(comparison, date_str)
    print(f"\nComparison saved to: {output_file}")

    # Print summary
    summary = comparison['summary']
    mood = comparison['market_mood_shift']

    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"  New stocks in PM:       {summary['total_new_stocks']}")
    print(f"  Removed stocks in PM:   {summary['total_removed_stocks']}")
    print(f"  Sentiment changes:      {summary['total_sentiment_changes']}")
    print(f"  Volume changes (>{VOLUME_CHANGE_THRESHOLD}%): {summary['total_volume_changes']}")
    print(f"\n  Market Mood: {mood['am_mood'].upper()} -> {mood['pm_mood'].upper()}")
    print(f"  {mood['shift_description']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
