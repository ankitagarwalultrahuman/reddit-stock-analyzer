"""Configuration settings for Reddit Stock Analyzer."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


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


# Claude API Configuration
ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Reddit Configuration
SUBREDDITS = [
    "IndianStreetBets",
    "IndianStockMarket",
    "DalalStreetTalks",
    "IndiaInvestments",
]

# Scraping limits
POSTS_PER_SUBREDDIT = 15  # Top posts to fetch per subreddit (before filtering)
COMMENTS_PER_POST = 10     # Top comments to fetch per post
REQUEST_DELAY = 6          # Seconds between requests (rate limiting)
MAX_POST_AGE_HOURS = 48    # Only include posts from the last N hours

# Reddit API endpoints (no auth required)
REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Output settings
OUTPUT_DIR = "output"
SAVE_RAW_DATA = True  # Save scraped data to JSON for debugging

# Dashboard settings
DASHBOARD_CACHE_TTL = 3600  # Cache TTL in seconds (1 hour)
WEEKLY_SUMMARY_DAYS = 7  # Number of days for weekly summary

# Stock History settings
STOCK_HISTORY_DAYS = 30  # Default days of price history
STOCK_CACHE_TTL_HOURS = 24  # Cache expiration for stock data

# News API Configuration
FINNHUB_API_KEY = get_secret("FINNHUB_API_KEY")
NEWS_FETCH_HOURS = 48  # Hours of news to fetch
NEWS_CACHE_TTL = 1800  # 30 minutes cache
NEWS_MAX_ARTICLES = 20  # Max articles to analyze
NEWS_ENABLED = True  # Feature flag for news section

# Session Configuration (AM/PM reports)
SESSION_AM = "AM"
SESSION_PM = "PM"
AM_CUTOFF_HOUR_IST = 12  # Before 12 PM IST is considered morning session
IST_UTC_OFFSET_HOURS = 5.5  # IST is UTC+5:30
VOLUME_CHANGE_THRESHOLD = 20  # Percentage change threshold for volume changes
