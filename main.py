#!/usr/bin/env python3
"""
Reddit Indian Stock Market Analyzer

Scrapes top posts from Indian stock market subreddits and uses Claude AI
to generate a daily digest of key insights and recommendations.
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta

from config import (
    SUBREDDITS, OUTPUT_DIR, SAVE_RAW_DATA, MAX_POST_AGE_HOURS,
    SESSION_AM, SESSION_PM, AM_CUTOFF_HOUR_IST, IST_UTC_OFFSET_HOURS
)
from reddit_scraper import scrape_all_subreddits
from summarizer import analyze_with_claude, generate_report


def get_ist_now() -> datetime:
    """Get current time in IST."""
    ist = timezone(timedelta(hours=IST_UTC_OFFSET_HOURS))
    return datetime.now(ist)


def get_session_suffix() -> str:
    """Auto-detect AM/PM based on IST time."""
    ist_now = get_ist_now()
    if ist_now.hour < AM_CUTOFF_HOUR_IST:
        return SESSION_AM
    return SESSION_PM


def get_date_str() -> str:
    """Get current date string in YYYYMMDD format based on IST."""
    return get_ist_now().strftime('%Y%m%d')


def save_raw_data(all_data: dict, timestamp: str) -> str:
    """Save raw scraped data to JSON for debugging/archival."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{OUTPUT_DIR}/raw_data_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    return filename


def save_report(report: str, session: str) -> str:
    """
    Save the generated report to a text file with session-based naming.

    New format: report_YYYYMMDD_AM.txt or report_YYYYMMDD_PM.txt
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = get_date_str()
    filename = f"{OUTPUT_DIR}/report_{date_str}_{session}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)

    return filename


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Reddit Indian Stock Market Analyzer - Daily Digest Generator"
    )
    parser.add_argument(
        "--session",
        choices=["AM", "PM", "auto"],
        default="auto",
        help="Session type: AM (morning), PM (evening), or auto (detect based on IST time)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the Reddit Stock Analyzer."""
    args = parse_args()

    # Determine session
    if args.session == "auto":
        session = get_session_suffix()
    else:
        session = args.session

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║         REDDIT INDIAN STOCK MARKET ANALYZER                  ║
    ║         Daily Digest Generator - {session} Session                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = get_date_str()

    print(f"Session: {session}")
    print(f"Date: {date_str}")
    print(f"IST Time: {get_ist_now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Scrape Reddit data
    print("\n[1/3] SCRAPING REDDIT DATA")
    print("-" * 40)
    print(f"Target subreddits: {', '.join([f'r/{s}' for s in SUBREDDITS])}")

    all_data = scrape_all_subreddits(SUBREDDITS)

    # Count total posts and comments
    total_posts = sum(len(posts) for posts in all_data.values())
    total_comments = sum(
        len(post.get('comments', []))
        for posts in all_data.values()
        for post in posts
    )

    print(f"\nScraping complete!")
    print(f"  Total posts: {total_posts}")
    print(f"  Total comments: {total_comments}")

    # Save raw data if enabled
    if SAVE_RAW_DATA:
        raw_file = save_raw_data(all_data, timestamp)
        print(f"  Raw data saved to: {raw_file}")

    if total_posts == 0:
        print("\nNo posts found! Please check your internet connection and try again.")
        return

    # Step 2: Analyze with Claude
    print("\n[2/3] ANALYZING WITH CLAUDE AI")
    print("-" * 40)

    analysis = analyze_with_claude(all_data)

    # Step 3: Generate and save report
    print("\n[3/3] GENERATING REPORT")
    print("-" * 40)

    report = generate_report(analysis, total_posts, total_comments, SUBREDDITS, MAX_POST_AGE_HOURS)
    report_file = save_report(report, session)

    print(f"Report saved to: {report_file}")

    # Print the report
    print("\n" + "=" * 80)
    print(report)

    print(f"\nDone! {session} session report saved to: {report_file}")


if __name__ == "__main__":
    main()
