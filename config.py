"""Configuration settings for Reddit Stock Analyzer."""

import os
from dotenv import load_dotenv

load_dotenv()

# Claude API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
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
