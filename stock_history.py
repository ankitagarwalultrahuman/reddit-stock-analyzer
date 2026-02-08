"""
Stock History Module - Fetches historical price data for NSE stocks.

Uses yfinance for free, no-API-key data access.
Implements SQLite-based caching to minimize API calls.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

from portfolio_analyzer import normalize_ticker, TICKER_MAPPINGS

# Cache configuration
CACHE_DB = "stock_cache.db"
CACHE_TTL_HOURS = 24

# NSE suffix for yfinance
NSE_SUFFIX = ".NS"

# Additional ETF mappings for yfinance
ETF_MAPPINGS = {
    "SILVERBEES": "SILVERBEES.NS",
    "SILVER": "SILVERBEES.NS",
    "GOLDBEES": "GOLDBEES.NS",
    "GOLD": "GOLDBEES.NS",
    "NIFTYBEES": "NIFTYBEES.NS",
    "NIFTY50": "NIFTYBEES.NS",
    "BANKBEES": "BANKBEES.NS",
    "SILVER ETF": "SILVERBEES.NS",
    "GOLD ETF": "GOLDBEES.NS",
    "NIFTY 50 ETF": "NIFTYBEES.NS",
}

# Special ticker mappings for stocks with unusual symbols
SPECIAL_TICKER_MAPPINGS = {
    # Stocks with hyphens
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJAJAUTO": "BAJAJ-AUTO.NS",

    # Stocks with ampersands
    "M&M": "M&M.NS",
    "MM": "M&M.NS",
    "M&MFIN": "M&MFIN.NS",
    "L&TFH": "L&TFH.NS",

    # Tickers that need different symbols on yfinance
    "NATCOPHARMA": "NATCOPHARM.NS",
    # TATAMOTORS uses standard .NS suffix, no special mapping needed
    "MAZAGON": "MAZDOCK.NS",
    "KNR": "KNRCON.NS",
    "COCHINSHIP": "COCHINSHIP.NS",
    "GRSE": "GRSE.NS",
    "BDL": "BDL.NS",
    "IRFC": "IRFC.NS",
    "RVNL": "RVNL.NS",
    "IRCON": "IRCON.NS",
    "HAL": "HAL.NS",

    # Common alternate names
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}


def init_cache_db():
    """Initialize SQLite cache database with days-aware keying."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_cache (
            ticker TEXT NOT NULL,
            days INTEGER DEFAULT 0,
            data TEXT NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)

    # Migration: add days column if upgrading from old schema
    try:
        cursor.execute("ALTER TABLE stock_cache ADD COLUMN days INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_expires ON stock_cache(expires_at)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ticker_days ON stock_cache(ticker, days)
    """)

    conn.commit()
    conn.close()


def get_nse_symbol(ticker: str) -> str:
    """
    Convert ticker to yfinance NSE format.

    Handles:
    - Already has .NS suffix
    - ETF names (SILVERBEES, NIFTYBEES)
    - Special tickers (BAJAJ-AUTO, M&M)
    - Full company names
    - Common abbreviations
    """
    ticker_upper = ticker.upper().strip()

    # Check special ticker mappings first (BAJAJ-AUTO, M&M, etc.)
    if ticker_upper in SPECIAL_TICKER_MAPPINGS:
        return SPECIAL_TICKER_MAPPINGS[ticker_upper]

    # Check ETF mappings
    if ticker_upper in ETF_MAPPINGS:
        return ETF_MAPPINGS[ticker_upper]

    # Normalize using portfolio_analyzer mappings
    normalized = normalize_ticker(ticker_upper)

    # Check special mappings again after normalization
    if normalized in SPECIAL_TICKER_MAPPINGS:
        return SPECIAL_TICKER_MAPPINGS[normalized]

    # Check if already has suffix
    if normalized.endswith(".NS") or normalized.endswith(".BO"):
        return normalized

    # Add NSE suffix
    return f"{normalized}.NS"


def get_cached_data(ticker: str, days: int = 0) -> Optional[pd.DataFrame]:
    """Retrieve cached price data if not expired, keyed by ticker and days."""
    init_cache_db()

    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT data FROM stock_cache
        WHERE ticker = ? AND days = ? AND expires_at > datetime('now')
    """, (ticker.upper(), days))

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            from io import StringIO
            return pd.read_json(StringIO(row[0]))
        except Exception:
            return None
    return None


def cache_data(ticker: str, df: pd.DataFrame, days: int = 0):
    """Store price data in cache, keyed by ticker and days."""
    init_cache_db()

    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(hours=CACHE_TTL_HOURS)

    # Convert DataFrame to JSON string
    data_json = df.to_json(date_format='iso')

    cursor.execute("""
        INSERT OR REPLACE INTO stock_cache (ticker, days, data, fetched_at, expires_at)
        VALUES (?, ?, ?, datetime('now'), ?)
    """, (ticker.upper(), days, data_json, expires_at.isoformat()))

    conn.commit()
    conn.close()


def clear_stale_cache():
    """Remove expired cache entries."""
    init_cache_db()

    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM stock_cache WHERE expires_at < datetime('now')")

    conn.commit()
    conn.close()


def clear_all_cache():
    """Clear entire stock cache. Use when data seems stale or corrupted."""
    init_cache_db()

    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM stock_cache")

    conn.commit()
    conn.close()
    return True


def get_cache_stats() -> dict:
    """Get cache statistics."""
    init_cache_db()

    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM stock_cache")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_cache WHERE expires_at > datetime('now')")
    valid = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(fetched_at), MAX(fetched_at) FROM stock_cache")
    row = cursor.fetchone()
    oldest = row[0] if row else None
    newest = row[1] if row else None

    conn.close()

    return {
        "total_entries": total,
        "valid_entries": valid,
        "oldest_fetch": oldest,
        "newest_fetch": newest,
    }


def fetch_stock_history(ticker: str, days: int = 30, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetch historical price data for a stock.

    Args:
        ticker: NSE stock symbol (e.g., "RELIANCE", "TCS")
        days: Number of days of history (default 30)
        force_refresh: If True, bypass cache and fetch fresh data from yfinance

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Returns empty DataFrame if fetch fails
    """
    if yf is None:
        print("yfinance not installed. Run: pip install yfinance")
        return pd.DataFrame()

    # Normalize ticker
    normalized_ticker = normalize_ticker(ticker)

    # Check cache first (unless force_refresh is True)
    if not force_refresh:
        cached = get_cached_data(normalized_ticker, days)
        if cached is not None and not cached.empty:
            return cached

    # Convert to yfinance format
    yf_symbol = get_nse_symbol(ticker)

    try:
        stock = yf.Ticker(yf_symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 7)  # Extra buffer for weekends/holidays

        df = stock.history(start=start_date, end=end_date)

        if df.empty:
            # Try without .NS suffix (some ETFs)
            alt_symbol = yf_symbol.replace(".NS", "")
            stock = yf.Ticker(alt_symbol)
            df = stock.history(start=start_date, end=end_date)

        if df.empty:
            # Try BSE suffix
            bse_symbol = normalized_ticker + ".BO"
            stock = yf.Ticker(bse_symbol)
            df = stock.history(start=start_date, end=end_date)

        if not df.empty:
            # Keep only relevant columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            # Reset index to make Date a column
            df = df.reset_index()
            df = df.rename(columns={'index': 'Date'})
            cache_data(normalized_ticker, df, days)

        return df

    except Exception as e:
        print(f"Error fetching {ticker} ({yf_symbol}): {e}")
        return pd.DataFrame()


def get_current_price(ticker: str) -> dict:
    """
    Get real-time/current price for a stock using yfinance fast_info.

    This returns the latest available price (more current than history() which is EOD).

    Args:
        ticker: NSE stock symbol (e.g., "RELIANCE", "TCS")

    Returns:
        dict with:
        - current_price: Latest market price
        - previous_close: Previous day's closing price
        - change_percent: Percentage change from previous close
        - volume: Current day's volume (if available)
        - success: Whether the fetch succeeded
    """
    if yf is None:
        return {"success": False, "error": "yfinance not installed"}

    yf_symbol = get_nse_symbol(ticker)

    try:
        stock = yf.Ticker(yf_symbol)

        # Try fast_info first (faster, less data)
        try:
            info = stock.fast_info
            current_price = info.last_price
            previous_close = info.previous_close

            if current_price and previous_close and previous_close != 0:
                change_percent = ((current_price - previous_close) / previous_close) * 100
                return {
                    "success": True,
                    "ticker": ticker,
                    "current_price": round(current_price, 2),
                    "previous_close": round(previous_close, 2),
                    "change_percent": round(change_percent, 2),
                    "volume": getattr(info, 'last_volume', None),
                }
        except Exception:
            pass

        # Fallback to regular info
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')

        if current_price and previous_close and previous_close != 0:
            change_percent = ((current_price - previous_close) / previous_close) * 100
            return {
                "success": True,
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "previous_close": round(previous_close, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume'),
            }

        # Last fallback: use history with period="1d"
        df = stock.history(period="5d")
        if not df.empty:
            current_price = float(df['Close'].iloc[-1])
            previous_close = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
            change_percent = ((current_price - previous_close) / previous_close) * 100 if previous_close and previous_close != 0 else 0
            return {
                "success": True,
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "previous_close": round(previous_close, 2),
                "change_percent": round(change_percent, 2),
                "volume": int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else None,
            }

        return {"success": False, "error": "Could not fetch price data"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_multiple_stocks(tickers: list[str], days: int = 30) -> dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple stocks.

    Args:
        tickers: List of ticker symbols
        days: Number of days of history

    Returns:
        Dict mapping ticker to DataFrame
    """
    results = {}

    for ticker in tickers:
        df = fetch_stock_history(ticker, days)
        if not df.empty:
            results[normalize_ticker(ticker)] = df

    return results


def calculate_performance_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate key performance metrics from price history.

    Args:
        df: DataFrame with 'Close' column

    Returns:
        dict with:
        - total_return: Percentage return over period
        - annualized_return: Annualized return rate
        - volatility: Standard deviation of daily returns (annualized)
        - sharpe_ratio: Risk-adjusted return (assuming 6% risk-free rate)
        - max_drawdown: Maximum peak-to-trough decline
        - best_day: Best single-day return
        - worst_day: Worst single-day return
    """
    if df.empty or len(df) < 2:
        return {}

    # Ensure we have Close column
    if 'Close' not in df.columns:
        return {}

    close_prices = df['Close']

    # Calculate daily returns
    daily_returns = close_prices.pct_change().dropna()

    # Total return
    total_return = (close_prices.iloc[-1] / close_prices.iloc[0] - 1) * 100

    # Annualized return (only meaningful for periods >= 90 trading days)
    num_days = len(df)
    if num_days >= 90:
        annualized_return = ((1 + total_return/100) ** (252/num_days) - 1) * 100
    else:
        annualized_return = None  # Not meaningful for short periods

    # Volatility (annualized)
    daily_vol = daily_returns.std()
    volatility = daily_vol * (252 ** 0.5) * 100

    # Sharpe ratio (6% risk-free rate for India)
    risk_free_rate = 0.06
    if annualized_return is not None and volatility > 0:
        excess_return = annualized_return/100 - risk_free_rate
        sharpe_ratio = excess_return / (volatility/100)
    else:
        sharpe_ratio = 0

    # Max drawdown
    rolling_max = close_prices.cummax()
    drawdown = (close_prices - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    # Best/worst days
    best_day = daily_returns.max() * 100
    worst_day = daily_returns.min() * 100

    return {
        'total_return': round(total_return, 2),
        'period_return': round(total_return, 2),  # Always available regardless of period length
        'annualized_return': round(annualized_return, 2) if annualized_return is not None else None,
        'volatility': round(volatility, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'max_drawdown': round(max_drawdown, 2),
        'best_day': round(best_day, 2),
        'worst_day': round(worst_day, 2),
        'start_price': round(close_prices.iloc[0], 2),
        'end_price': round(close_prices.iloc[-1], 2),
        'high': round(df['High'].max(), 2) if 'High' in df.columns else None,
        'low': round(df['Low'].min(), 2) if 'Low' in df.columns else None,
    }


def compare_sentiment_vs_performance(
    sentiment: str,
    price_change: float,
    mentions: int = 0
) -> dict:
    """
    Analyze whether Reddit sentiment aligned with actual price movement.

    Args:
        sentiment: Reddit sentiment (bullish/bearish/neutral/mixed)
        price_change: Actual percentage price change
        mentions: Number of Reddit mentions

    Returns:
        dict with alignment_score, verdict, explanation
    """
    # Sentiment mapping to expected movement
    sentiment_expectations = {
        'bullish': 'up',
        'bearish': 'down',
        'neutral': 'flat',
        'mixed': 'volatile',
    }

    expected = sentiment_expectations.get(sentiment.lower(), 'unknown')

    # Determine actual movement
    if price_change > 2:
        actual = 'up'
    elif price_change < -2:
        actual = 'down'
    else:
        actual = 'flat'

    # Calculate alignment
    if expected == actual:
        alignment_score = 100
        verdict = "ALIGNED"
        emoji = "✅"
    elif expected == 'flat' and abs(price_change) < 5:
        alignment_score = 75
        verdict = "PARTIALLY ALIGNED"
        emoji = "🟡"
    elif expected == 'volatile':
        alignment_score = 50
        verdict = "INCONCLUSIVE"
        emoji = "🔵"
    elif expected == 'unknown':
        alignment_score = 0
        verdict = "UNKNOWN"
        emoji = "❓"
    else:
        alignment_score = 0
        verdict = "MISALIGNED"
        emoji = "❌"

    return {
        'sentiment': sentiment,
        'expected_movement': expected,
        'actual_movement': actual,
        'price_change': round(price_change, 2),
        'alignment_score': alignment_score,
        'verdict': verdict,
        'emoji': emoji,
        'mentions': mentions,
    }


def get_stock_summary(ticker: str, days: int = 30) -> dict:
    """
    Get complete stock summary including history and metrics.

    Args:
        ticker: Stock symbol
        days: Number of days of history

    Returns:
        dict with history DataFrame, metrics, and metadata
    """
    df = fetch_stock_history(ticker, days)

    if df.empty:
        return {
            'ticker': normalize_ticker(ticker),
            'success': False,
            'error': f"Could not fetch data for {ticker}",
            'history': pd.DataFrame(),
            'metrics': {},
        }

    metrics = calculate_performance_metrics(df)

    return {
        'ticker': normalize_ticker(ticker),
        'success': True,
        'history': df,
        'metrics': metrics,
        'data_points': len(df),
        'date_range': {
            'start': df['Date'].iloc[0].strftime('%Y-%m-%d') if 'Date' in df.columns else None,
            'end': df['Date'].iloc[-1].strftime('%Y-%m-%d') if 'Date' in df.columns else None,
        }
    }


def get_stock_with_technicals(ticker: str, days: int = 60) -> dict:
    """
    Get stock data with technical indicators included.

    Args:
        ticker: Stock symbol
        days: Number of days of history (default 60 for better indicator accuracy)

    Returns:
        dict with history, metrics, and technical analysis
    """
    from technical_analysis import get_technical_analysis, signals_to_dict

    df = fetch_stock_history(ticker, days)
    normalized_ticker = normalize_ticker(ticker)

    if df.empty:
        return {
            'ticker': normalized_ticker,
            'success': False,
            'error': f"Could not fetch data for {ticker}",
            'history': pd.DataFrame(),
            'metrics': {},
            'technicals': None,
        }

    # Get performance metrics
    metrics = calculate_performance_metrics(df)

    # Get technical analysis
    technical_signals = get_technical_analysis(df, normalized_ticker)
    technicals_dict = signals_to_dict(technical_signals)

    return {
        'ticker': normalized_ticker,
        'success': True,
        'history': df,
        'metrics': metrics,
        'technicals': technicals_dict,
        'data_points': len(df),
        'date_range': {
            'start': df['Date'].iloc[0].strftime('%Y-%m-%d') if 'Date' in df.columns else None,
            'end': df['Date'].iloc[-1].strftime('%Y-%m-%d') if 'Date' in df.columns else None,
        }
    }


def get_price_at_date(ticker: str, target_date: str) -> Optional[float]:
    """
    Get closing price for a stock on a specific date.

    Args:
        ticker: Stock symbol
        target_date: Date string (YYYY-MM-DD)

    Returns:
        Closing price or None if not available
    """
    # Calculate how many days we need to fetch based on target date
    target = pd.to_datetime(target_date).date()
    days_needed = (datetime.now().date() - target).days + 7  # buffer for weekends
    days_needed = max(days_needed, 30)  # minimum 30 days
    df = fetch_stock_history(ticker, days=days_needed)

    if df.empty or 'Date' not in df.columns:
        return None

    # Find the row with matching date (or closest earlier date)
    df['date_only'] = pd.to_datetime(df['Date']).dt.date

    matching = df[df['date_only'] == target]
    if not matching.empty:
        return float(matching['Close'].iloc[0])

    # Try to find the closest date before target
    earlier = df[df['date_only'] <= target]
    if not earlier.empty:
        return float(earlier['Close'].iloc[-1])

    return None


def get_prices_for_outcomes(ticker: str, signal_date: str) -> dict:
    """
    Get prices at 1, 3, 5, 10 days after signal date.

    Args:
        ticker: Stock symbol
        signal_date: Date of the signal (YYYY-MM-DD)

    Returns:
        Dict with price_1d, price_3d, price_5d, price_10d
    """
    # Calculate days needed: from signal date to now, plus 15 for outcome tracking
    signal_dt = pd.to_datetime(signal_date).date()
    days_since_signal = (datetime.now().date() - signal_dt).days
    days_needed = days_since_signal + 15  # Need signal date + up to 10 trading days after
    days_needed = max(days_needed, 30)
    df = fetch_stock_history(ticker, days=days_needed)

    if df.empty or 'Date' not in df.columns:
        return {}
    df['date_only'] = pd.to_datetime(df['Date']).dt.date

    prices = {}
    for days, key in [(1, 'price_1d'), (3, 'price_3d'), (5, 'price_5d'), (10, 'price_10d')]:
        target_date = signal_dt + timedelta(days=days)

        # Find the closest trading day on or after target
        future = df[df['date_only'] >= target_date]
        if not future.empty:
            prices[key] = float(future['Close'].iloc[0])

    return prices
