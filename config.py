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


# Reddit Configuration
SUBREDDITS = [
    "IndianStreetBets",
    "IndianStockMarket",
    "DalalStreetTalks",
    "IndiaInvestments",
    "Indiantradingbets",
    "StockMarketIndia",
    "IndiaStocks"
]

# Scraping limits
POSTS_PER_SUBREDDIT = 15  # Top posts to fetch per subreddit (before filtering)
COMMENTS_PER_POST = 10     # Top comments to fetch per post
REQUEST_DELAY = 8          # Seconds between requests (increased for cloud servers)
MAX_POST_AGE_HOURS = 48    # Only include posts from the last N hours

# Reddit API endpoints (no auth required)
# Using old.reddit.com as it's less restrictive for scraping
REDDIT_BASE_URL = "https://old.reddit.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

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

# Technical Analysis Configuration
TECHNICAL_ANALYSIS_ENABLED = True  # Enable/disable technical analysis features
TECHNICAL_HISTORY_DAYS = 250  # Days of price history for indicator calculations (needs 200+ for EMA-200)

# RSI settings
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_NEAR_OVERSOLD = 40
RSI_NEAR_OVERBOUGHT = 60

# Screener-specific RSI (wider bands to catch more swing candidates early)
SCREENER_RSI_OVERSOLD = 35
SCREENER_RSI_OVERBOUGHT = 65

# MACD settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Moving Average settings
EMA_SHORT = 20
EMA_MEDIUM = 50
EMA_LONG = 200

# Bollinger Bands settings
BB_PERIOD = 20
BB_STD_DEV = 2.0

# ATR settings
ATR_PERIOD = 14

# Volume thresholds
VOLUME_SIGNAL_HIGH = 1.5  # Threshold for "high" volume signal classification

# ADX (Average Directional Index) settings
ADX_PERIOD = 14
ADX_STRONG_TREND = 25  # ADX above this = strong trend
ADX_WEAK_TREND = 20    # ADX below this = no clear trend

# Stochastic RSI settings
STOCH_RSI_PERIOD = 14
STOCH_RSI_OVERSOLD = 20
STOCH_RSI_OVERBOUGHT = 80

# Fibonacci retracement levels
FIBONACCI_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]

# Confluence Signal settings
MIN_CONFLUENCE_SCORE = 2  # Minimum score to consider a signal
STRONG_CONFLUENCE_SCORE = 4  # Score for "strong" signals
MIN_MENTIONS_FOR_SIGNAL = 5  # Minimum Reddit mentions to analyze

# Signal Tracking settings
SIGNAL_TRACKING_ENABLED = True  # Enable signal storage and accuracy tracking
SIGNAL_RETENTION_DAYS = 90  # Days to keep signal history

# Watchlist Scanner settings
DEFAULT_WATCHLIST = "NIFTY50"  # Default watchlist for scanning
SCREENER_MAX_WORKERS = 5  # Parallel workers for scanning
SCREENER_MIN_MATCHES = 2  # Default minimum criteria matches

# Sector Tracker settings
SECTOR_ANALYSIS_ENABLED = True
SECTOR_CACHE_TTL = 600  # 10 minutes

# Telegram Alerts
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")
TELEGRAM_ALERTS_ENABLED = True  # Enable/disable Telegram notifications

# Perplexity AI (for real-time news search in movement analysis)
PERPLEXITY_API_KEY = get_secret("PERPLEXITY_API_KEY")

# Swing Trading Configuration
SWING_TRADING_ENABLED = True
SWING_LOOKBACK_PERIOD = 20  # Days for S/R detection
SWING_MIN_CONFLUENCE = 2    # Minimum signals for trade
SWING_RISK_REWARD_MIN = 1.5  # Minimum R:R ratio
SWING_VOLUME_THRESHOLD = 1.3  # Volume multiplier for breakouts

# Support/Resistance Settings
SR_PIVOT_PERIOD = 10
SR_TOUCH_COUNT_MIN = 2  # Zone strength
SR_CLUSTER_THRESHOLD_PCT = 1.5  # % range to cluster nearby S/R levels

# Relative Strength Settings
RS_LOOKBACK_DAYS = 20
RS_BENCHMARK = "^NSEI"  # NIFTY 50 index
