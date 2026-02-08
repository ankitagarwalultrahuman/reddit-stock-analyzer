"""
Financial News Fetcher Module

Fetches and analyzes financial news for stocks mentioned in Reddit analysis.
Primary API: Finnhub (for general financial news)
Note: Finnhub has limited direct support for Indian stocks,
so we use keyword-based filtering for India-related news.
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
import json
import re
import hashlib
import threading

from openai import OpenAI

from config import get_secret, PERPLEXITY_API_KEY

# Perplexity API configuration
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar"

# News API Configuration
FINNHUB_API_KEY = get_secret("FINNHUB_API_KEY")
NEWS_FETCH_HOURS = 48
NEWS_MAX_ARTICLES_PER_STOCK = 5
NEWS_CACHE_TTL = 1800  # 30 minutes
NEWS_MAX_TOTAL_ARTICLES = 20


@dataclass
class NewsArticle:
    """Represents a single news article."""
    headline: str
    summary: str
    source: str
    url: str
    published_at: datetime
    related_tickers: list = field(default_factory=list)
    sentiment_score: float = 0.0  # -1 to 1
    category: str = "general"


class NewsCache:
    """Thread-safe in-memory cache for news articles."""
    _cache = {}
    _timestamps = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, key: str) -> Optional[list]:
        with cls._lock:
            if key in cls._cache:
                if time.time() - cls._timestamps.get(key, 0) < NEWS_CACHE_TTL:
                    return cls._cache[key]
        return None

    @classmethod
    def set(cls, key: str, value: list):
        with cls._lock:
            cls._cache[key] = value
            cls._timestamps[key] = time.time()

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache = {}
            cls._timestamps = {}


class FinnhubClient:
    """Finnhub API client for financial news."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or FINNHUB_API_KEY
        self.session = requests.Session()

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_market_news(self, category: str = "general") -> list[dict]:
        """
        Fetch general market news.

        Args:
            category: News category (general, forex, crypto, merger)

        Returns:
            List of news articles
        """
        if not self.is_configured():
            return []

        try:
            url = f"{self.BASE_URL}/news"
            params = {
                "category": category,
                "token": self.api_key,
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Finnhub market news error: {e}")
            return []

    def get_company_news(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
        """
        Fetch company-specific news.

        Args:
            symbol: Stock symbol (e.g., "AAPL" for US stocks)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of news articles

        Note: Finnhub primarily supports US stocks. For Indian stocks,
        use get_market_news with keyword filtering instead.
        """
        if not self.is_configured():
            return []

        try:
            url = f"{self.BASE_URL}/company-news"
            params = {
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
                "token": self.api_key,
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Finnhub company news error: {e}")
            return []

    def search_news(self, query: str) -> list[dict]:
        """
        Search for news by query.

        Note: This is a premium feature on Finnhub.
        For free tier, use market news with filtering.
        """
        # Market news with keyword filtering
        all_news = self.get_market_news("general")
        query_lower = query.lower()

        filtered = []
        for article in all_news:
            headline = article.get("headline", "").lower()
            summary = article.get("summary", "").lower()

            if query_lower in headline or query_lower in summary:
                filtered.append(article)

        return filtered


# Indian market keywords for filtering
INDIAN_MARKET_KEYWORDS = [
    "india", "indian", "nse", "bse", "sensex", "nifty",
    "mumbai", "sebi", "rbi", "rupee", "inr",
    "reliance", "tata", "hdfc", "icici", "infosys", "wipro",
    "bharti", "airtel", "sbi", "kotak", "adani", "zomato",
    "bajaj", "maruti", "asian paints", "hindustan unilever",
]


def filter_india_news(articles: list[dict]) -> list[dict]:
    """Filter articles related to Indian markets."""
    filtered = []

    for article in articles:
        headline = article.get("headline", "").lower()
        summary = article.get("summary", "").lower()
        combined = headline + " " + summary

        # Check if any Indian keyword is present
        for keyword in INDIAN_MARKET_KEYWORDS:
            if keyword in combined:
                filtered.append(article)
                break

    return filtered


def fetch_news_for_stocks(
    stock_tickers: list[str],
    portfolio_tickers: list[str] = None,
    include_general: bool = True
) -> list[NewsArticle]:
    """
    Main entry point: Fetch news for given stock tickers.

    Args:
        stock_tickers: Tickers from Reddit analysis (e.g., ['RELIANCE', 'TCS'])
        portfolio_tickers: User's portfolio tickers for priority
        include_general: Include general Indian market news

    Returns:
        List of NewsArticle objects, sorted by relevance/recency
    """
    # Check cache
    ticker_str = '-'.join(sorted(stock_tickers))
    cache_key = f"news_{hashlib.md5(ticker_str.encode()).hexdigest()[:12]}"
    cached = NewsCache.get(cache_key)
    if cached:
        return cached

    articles = []
    finnhub = FinnhubClient()

    if not finnhub.is_configured():
        print("Finnhub API not configured. Set FINNHUB_API_KEY in .env")
        return []

    # Fetch general market news
    if include_general:
        general_news = finnhub.get_market_news("general")

        # Filter for India-related news
        india_news = filter_india_news(general_news)

        for item in india_news[:NEWS_MAX_TOTAL_ARTICLES]:
            article = NewsArticle(
                headline=item.get("headline", ""),
                summary=item.get("summary", "")[:500],
                source=item.get("source", "Unknown"),
                url=item.get("url", ""),
                published_at=datetime.fromtimestamp(item.get("datetime", 0)),
                category=item.get("category", "general"),
                sentiment_score=0.0,  # Will be analyzed by Claude
            )

            # Try to match tickers
            headline_upper = article.headline.upper()
            summary_upper = article.summary.upper()
            combined = headline_upper + " " + summary_upper

            for ticker in stock_tickers + (portfolio_tickers or []):
                pattern = r'\b' + re.escape(ticker.upper()) + r'\b'
                if re.search(pattern, combined):
                    article.related_tickers.append(ticker)

            articles.append(article)

    # Sort by published date (most recent first)
    articles.sort(key=lambda x: x.published_at, reverse=True)

    # Limit to max articles
    articles = articles[:NEWS_MAX_TOTAL_ARTICLES]

    # Cache results
    NewsCache.set(cache_key, articles)

    return articles


def format_news_for_analysis(articles: list[NewsArticle]) -> str:
    """Format news articles for Claude analysis."""
    if not articles:
        return "No recent news articles found."

    lines = []
    for i, article in enumerate(articles[:15], 1):
        tickers_str = ", ".join(article.related_tickers) if article.related_tickers else "General"
        lines.append(f"""
{i}. **{article.headline}**
   Source: {article.source} | Date: {article.published_at.strftime('%Y-%m-%d %H:%M')}
   Related: {tickers_str}
   Summary: {article.summary[:300]}...
""")

    return "\n".join(lines)


def format_reddit_sentiment(reddit_stocks: list[dict]) -> str:
    """Format Reddit sentiment data for Claude analysis."""
    if not reddit_stocks:
        return "No Reddit sentiment data available."

    lines = []
    for stock in reddit_stocks[:10]:
        ticker = stock.get("ticker", "Unknown")
        sentiment = stock.get("sentiment", "neutral")
        mentions = stock.get("total_mentions", stock.get("mentions", 0))

        lines.append(f"- {ticker}: {sentiment.upper()} ({mentions} mentions)")

    return "\n".join(lines)


def get_news_analysis_prompt(
    news_articles: list[NewsArticle],
    reddit_stocks: list[dict],
    portfolio_stocks: list[str] = None
) -> str:
    """Generate the news analysis prompt for Claude."""
    news_text = format_news_for_analysis(news_articles)
    reddit_text = format_reddit_sentiment(reddit_stocks)

    portfolio_context = ""
    if portfolio_stocks:
        portfolio_context = f"\n**USER'S PORTFOLIO:** {', '.join(portfolio_stocks[:10])}\nPrioritize news affecting these holdings.\n"

    return f"""You are a financial news analyst specializing in the Indian stock market. Analyze the following news articles from the last 48 hours and compare them with Reddit community sentiment.
{portfolio_context}
## NEWS ARTICLES (Last 48 hours):
{news_text}

## REDDIT SENTIMENT DATA:
{reddit_text}

Provide your analysis in the following JSON format (respond ONLY with valid JSON):

{{
    "highlights": [
        {{
            "headline": "Brief headline (max 100 chars)",
            "tickers": ["RELIANCE", "TCS"],
            "news_sentiment": "bullish|bearish|neutral",
            "news_impact": "high|medium|low",
            "source": "Source Name",
            "summary": "2-3 sentence summary of the news and its market impact",
            "reddit_alignment": "aligned|divergent|not_discussed",
            "reddit_sentiment": "bullish|bearish|neutral|unknown"
        }}
    ],
    "sentiment_divergences": [
        {{
            "ticker": "STOCK",
            "news_sentiment": "bullish",
            "reddit_sentiment": "bearish",
            "note": "Brief explanation of why sentiments differ"
        }}
    ],
    "market_summary": "One paragraph summary of overall news sentiment for Indian markets",
    "key_alerts": [
        "Alert 1: Important news affecting portfolio or market",
        "Alert 2: Sentiment divergence warning"
    ]
}}

Requirements:
1. Include maximum 5 highlights, sorted by impact/relevance
2. Highlight any sentiment divergences between news and Reddit
3. Flag news affecting user's portfolio stocks (if provided)
4. Focus on actionable insights for Indian market investors
5. If no relevant news found, return empty arrays for highlights and divergences
"""


def analyze_news_with_perplexity(
    news_articles: list[NewsArticle],
    reddit_stocks: list[dict],
    portfolio_stocks: list[str] = None
) -> dict:
    """
    Send news to Perplexity for analysis and comparison with Reddit sentiment.

    Args:
        news_articles: List of NewsArticle objects
        reddit_stocks: List of stock dicts with sentiment data
        portfolio_stocks: Optional list of portfolio ticker symbols

    Returns:
        dict with: highlights, sentiment_divergences, market_summary, key_alerts
    """
    if not PERPLEXITY_API_KEY:
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": "API key not configured.",
            "key_alerts": [],
            "error": "PERPLEXITY_API_KEY not set"
        }

    if not news_articles:
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": "No recent news articles found for analysis.",
            "key_alerts": [],
        }

    prompt = get_news_analysis_prompt(news_articles, reddit_stocks, portfolio_stocks)

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
                    "content": """You are a financial news analyst specializing in the Indian stock market.
Analyze the provided news articles and Reddit sentiment data.
Also search for any additional recent news about the mentioned stocks to provide comprehensive coverage.
Respond ONLY with valid JSON in the exact format requested."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2048,
            temperature=0.2
        )

        response_text = response.choices[0].message.content

        # Parse JSON response
        # Find JSON in response (in case there's extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return result

        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": response_text[:500],
            "key_alerts": [],
            "error": "Could not parse JSON response"
        }

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": "Error parsing analysis response.",
            "key_alerts": [],
            "error": str(e)
        }
    except Exception as e:
        print(f"Perplexity API error: {e}")
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": f"API error: {e}",
            "key_alerts": [],
            "error": str(e)
        }


# Backward compatible alias
def analyze_news_with_claude(
    news_articles: list[NewsArticle],
    reddit_stocks: list[dict],
    portfolio_stocks: list[str] = None
) -> dict:
    """Backward compatible alias - now uses Perplexity."""
    return analyze_news_with_perplexity(news_articles, reddit_stocks, portfolio_stocks)


def get_news_highlights(report_content: str, portfolio_stocks: list[str] = None) -> dict:
    """
    High-level function to get news analysis for dashboard.

    Args:
        report_content: Reddit report content string
        portfolio_stocks: Optional list of portfolio tickers

    Returns:
        Analysis dict ready for dashboard display
    """
    from dashboard_analytics import parse_stock_mentions, parse_key_insights_structured

    # Parse stocks from report
    stocks = parse_stock_mentions(report_content)
    insights = parse_key_insights_structured(report_content)

    # Get stock tickers
    stock_tickers = [s["ticker"] for s in stocks[:10]]
    insight_tickers = [i["ticker"] for i in insights[:10]]

    all_tickers = list(set(stock_tickers + insight_tickers))

    if not all_tickers and not portfolio_stocks:
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": "No stocks identified for news lookup.",
            "key_alerts": [],
        }

    # Fetch news
    news_articles = fetch_news_for_stocks(all_tickers, portfolio_stocks)

    if not news_articles:
        return {
            "highlights": [],
            "sentiment_divergences": [],
            "market_summary": "No recent news found for the discussed stocks.",
            "key_alerts": [],
        }

    # Combine stocks data for sentiment
    reddit_stocks = []
    for s in stocks:
        reddit_stocks.append({
            "ticker": s["ticker"],
            "sentiment": s.get("sentiment", "neutral"),
            "mentions": s.get("total_mentions", 0),
        })

    # Analyze with Claude
    analysis = analyze_news_with_claude(news_articles, reddit_stocks, portfolio_stocks)

    return analysis


if __name__ == "__main__":
    # Test the module
    print("Testing News Fetcher...")

    finnhub = FinnhubClient()

    if finnhub.is_configured():
        print("Finnhub API configured")

        # Fetch market news
        news = finnhub.get_market_news("general")
        print(f"Fetched {len(news)} general news articles")

        # Filter for India
        india_news = filter_india_news(news)
        print(f"Filtered to {len(india_news)} India-related articles")

        if india_news:
            print("\nSample India news:")
            for article in india_news[:3]:
                print(f"  - {article.get('headline', '')[:80]}...")
    else:
        print("Finnhub API not configured. Set FINNHUB_API_KEY in .env")
