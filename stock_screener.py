"""
Stock Screener - Scans watchlists for technical setups and trading opportunities.

Provides:
- Scan watchlists for stocks meeting technical criteria
- Pre-built screening strategies (Oversold + MACD, Breakout, etc.)
- Custom filter support
- Parallel scanning for speed
"""

import concurrent.futures
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from watchlist_manager import get_watchlist, get_stocks_from_watchlist, NIFTY50_STOCKS
from stock_history import fetch_stock_history
from technical_analysis import get_technical_analysis, TechnicalSignals


@dataclass
class ScreenerResult:
    """Result from screening a single stock."""
    ticker: str
    current_price: float
    matched_criteria: list[str]
    score: int  # Higher = more criteria matched
    signals: Optional[TechnicalSignals] = None

    # Key metrics for quick view
    rsi: Optional[float] = None
    macd_trend: Optional[str] = None
    ma_trend: Optional[str] = None
    volume_signal: Optional[str] = None
    technical_bias: Optional[str] = None


@dataclass
class ScreenerStrategy:
    """Defines a screening strategy."""
    name: str
    description: str
    filters: list[Callable[[TechnicalSignals], tuple[bool, str]]]  # Returns (matched, reason)


# =============================================================================
# BUILT-IN SCREENING STRATEGIES
# =============================================================================

def filter_rsi_oversold(signals: TechnicalSignals) -> tuple[bool, str]:
    """RSI below 35 (oversold territory)."""
    if signals.rsi and signals.rsi < 35:
        return True, f"RSI oversold ({signals.rsi})"
    return False, ""


def filter_rsi_overbought(signals: TechnicalSignals) -> tuple[bool, str]:
    """RSI above 65 (overbought territory)."""
    if signals.rsi and signals.rsi > 65:
        return True, f"RSI overbought ({signals.rsi})"
    return False, ""


def filter_macd_bullish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MACD showing bullish signal."""
    if signals.macd_trend in ("bullish", "bullish_crossover"):
        return True, f"MACD {signals.macd_trend}"
    return False, ""


def filter_macd_bearish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MACD showing bearish signal."""
    if signals.macd_trend in ("bearish", "bearish_crossover"):
        return True, f"MACD {signals.macd_trend}"
    return False, ""


def filter_macd_crossover_bullish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MACD bullish crossover (strong signal)."""
    if signals.macd_trend == "bullish_crossover":
        return True, "MACD bullish crossover"
    return False, ""


def filter_macd_crossover_bearish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MACD bearish crossover (strong signal)."""
    if signals.macd_trend == "bearish_crossover":
        return True, "MACD bearish crossover"
    return False, ""


def filter_price_above_ema50(signals: TechnicalSignals) -> tuple[bool, str]:
    """Price above 50 EMA (uptrend)."""
    if signals.price_vs_ema50 == "above":
        return True, "Price above 50 EMA"
    return False, ""


def filter_price_below_ema50(signals: TechnicalSignals) -> tuple[bool, str]:
    """Price below 50 EMA (downtrend)."""
    if signals.price_vs_ema50 == "below":
        return True, "Price below 50 EMA"
    return False, ""


def filter_ma_trend_bullish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MA alignment bullish (20 > 50 > 200)."""
    if signals.ma_trend == "bullish":
        return True, "MA trend bullish (20>50>200)"
    return False, ""


def filter_ma_trend_bearish(signals: TechnicalSignals) -> tuple[bool, str]:
    """MA alignment bearish (20 < 50 < 200)."""
    if signals.ma_trend == "bearish":
        return True, "MA trend bearish (20<50<200)"
    return False, ""


def filter_high_volume(signals: TechnicalSignals) -> tuple[bool, str]:
    """Volume above 1.3x average."""
    if signals.volume_ratio and signals.volume_ratio > 1.3:
        return True, f"High volume ({signals.volume_ratio}x avg)"
    return False, ""


def filter_low_volatility(signals: TechnicalSignals) -> tuple[bool, str]:
    """Low volatility (ATR < 2%)."""
    if signals.atr_percent and signals.atr_percent < 2:
        return True, f"Low volatility ({signals.atr_percent}%)"
    return False, ""


def filter_high_volatility(signals: TechnicalSignals) -> tuple[bool, str]:
    """High volatility (ATR > 4%)."""
    if signals.atr_percent and signals.atr_percent > 4:
        return True, f"High volatility ({signals.atr_percent}%)"
    return False, ""


def filter_near_bollinger_lower(signals: TechnicalSignals) -> tuple[bool, str]:
    """Price near lower Bollinger Band."""
    if signals.bb_position in ("near_lower", "below_lower"):
        return True, "Near lower Bollinger Band"
    return False, ""


def filter_near_bollinger_upper(signals: TechnicalSignals) -> tuple[bool, str]:
    """Price near upper Bollinger Band."""
    if signals.bb_position in ("near_upper", "above_upper"):
        return True, "Near upper Bollinger Band"
    return False, ""


def filter_technical_bullish(signals: TechnicalSignals) -> tuple[bool, str]:
    """Overall technical bias bullish (score > 60)."""
    if signals.technical_score and signals.technical_score > 60:
        return True, f"Technical score {signals.technical_score}/100"
    return False, ""


def filter_technical_bearish(signals: TechnicalSignals) -> tuple[bool, str]:
    """Overall technical bias bearish (score < 40)."""
    if signals.technical_score and signals.technical_score < 40:
        return True, f"Technical score {signals.technical_score}/100"
    return False, ""


# =============================================================================
# PRE-BUILT STRATEGIES
# =============================================================================

STRATEGIES = {
    "oversold_reversal": ScreenerStrategy(
        name="Oversold Reversal",
        description="RSI oversold + MACD turning bullish - potential bounce",
        filters=[filter_rsi_oversold, filter_macd_bullish],
    ),
    "strong_buy": ScreenerStrategy(
        name="Strong Buy Setup",
        description="RSI oversold + MACD bullish crossover + high volume",
        filters=[filter_rsi_oversold, filter_macd_crossover_bullish, filter_high_volume],
    ),
    "trend_following": ScreenerStrategy(
        name="Trend Following",
        description="MA trend bullish + price above 50 EMA + MACD bullish",
        filters=[filter_ma_trend_bullish, filter_price_above_ema50, filter_macd_bullish],
    ),
    "breakout": ScreenerStrategy(
        name="Breakout Setup",
        description="Near upper Bollinger + high volume + bullish MACD",
        filters=[filter_near_bollinger_upper, filter_high_volume, filter_macd_bullish],
    ),
    "oversold_bounce": ScreenerStrategy(
        name="Oversold Bounce",
        description="Near lower Bollinger + RSI oversold",
        filters=[filter_near_bollinger_lower, filter_rsi_oversold],
    ),
    "overbought_warning": ScreenerStrategy(
        name="Overbought Warning",
        description="RSI overbought + MACD turning bearish - potential correction",
        filters=[filter_rsi_overbought, filter_macd_bearish],
    ),
    "downtrend": ScreenerStrategy(
        name="Downtrend",
        description="MA trend bearish + price below 50 EMA",
        filters=[filter_ma_trend_bearish, filter_price_below_ema50],
    ),
    "high_momentum": ScreenerStrategy(
        name="High Momentum",
        description="Technical score > 60 + high volume",
        filters=[filter_technical_bullish, filter_high_volume],
    ),
    "low_risk_entry": ScreenerStrategy(
        name="Low Risk Entry",
        description="Low volatility + RSI oversold + bullish MA trend",
        filters=[filter_low_volatility, filter_rsi_oversold, filter_ma_trend_bullish],
    ),
}


def get_available_strategies() -> dict[str, ScreenerStrategy]:
    """Get all available screening strategies."""
    return STRATEGIES


def get_strategy(name: str) -> Optional[ScreenerStrategy]:
    """Get a specific strategy by name."""
    return STRATEGIES.get(name)


# =============================================================================
# SCREENING ENGINE
# =============================================================================

def scan_stock(ticker: str, filters: list[Callable]) -> Optional[ScreenerResult]:
    """
    Scan a single stock against filters.

    Args:
        ticker: Stock ticker
        filters: List of filter functions

    Returns:
        ScreenerResult if any filter matches, None otherwise
    """
    try:
        # Fetch price data
        df = fetch_stock_history(ticker, days=60)
        if df.empty:
            return None

        # Get technical analysis
        signals = get_technical_analysis(df, ticker)
        if signals.current_price == 0:
            return None

        # Apply filters
        matched = []
        for filter_func in filters:
            is_match, reason = filter_func(signals)
            if is_match:
                matched.append(reason)

        if not matched:
            return None

        return ScreenerResult(
            ticker=ticker,
            current_price=signals.current_price,
            matched_criteria=matched,
            score=len(matched),
            signals=signals,
            rsi=signals.rsi,
            macd_trend=signals.macd_trend,
            ma_trend=signals.ma_trend,
            volume_signal=signals.volume_signal,
            technical_bias=signals.technical_bias,
        )

    except Exception as e:
        print(f"Error scanning {ticker}: {e}")
        return None


def scan_watchlist(
    watchlist_name: str,
    strategy_name: str = None,
    custom_filters: list[Callable] = None,
    min_matches: int = 1,
    max_workers: int = 5,
) -> list[ScreenerResult]:
    """
    Scan all stocks in a watchlist.

    Args:
        watchlist_name: Name of watchlist to scan
        strategy_name: Name of pre-built strategy (optional)
        custom_filters: Custom filter functions (optional)
        min_matches: Minimum number of filter matches required
        max_workers: Max parallel workers for scanning

    Returns:
        List of ScreenerResult for stocks matching criteria
    """
    # Get stocks from watchlist
    stocks = get_stocks_from_watchlist(watchlist_name)
    if not stocks:
        print(f"Watchlist '{watchlist_name}' not found or empty")
        return []

    # Get filters
    if strategy_name:
        strategy = get_strategy(strategy_name)
        if strategy:
            filters = strategy.filters
        else:
            print(f"Strategy '{strategy_name}' not found")
            return []
    elif custom_filters:
        filters = custom_filters
    else:
        # Default: scan for any bullish technical signal
        filters = [filter_technical_bullish]

    # Scan stocks in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(scan_stock, ticker, filters): ticker
            for ticker in stocks
        }

        for future in concurrent.futures.as_completed(future_to_ticker):
            result = future.result()
            if result and result.score >= min_matches:
                results.append(result)

    # Sort by score (most matches first)
    results.sort(key=lambda x: x.score, reverse=True)

    return results


def scan_stocks(
    stocks: list[str],
    strategy_name: str = None,
    custom_filters: list[Callable] = None,
    min_matches: int = 1,
    max_workers: int = 5,
) -> list[ScreenerResult]:
    """
    Scan a list of stocks directly.

    Args:
        stocks: List of stock tickers
        strategy_name: Name of pre-built strategy (optional)
        custom_filters: Custom filter functions (optional)
        min_matches: Minimum number of filter matches required
        max_workers: Max parallel workers

    Returns:
        List of ScreenerResult for matching stocks
    """
    # Get filters
    if strategy_name:
        strategy = get_strategy(strategy_name)
        if strategy:
            filters = strategy.filters
        else:
            return []
    elif custom_filters:
        filters = custom_filters
    else:
        filters = [filter_technical_bullish]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(scan_stock, ticker, filters): ticker
            for ticker in stocks
        }

        for future in concurrent.futures.as_completed(future_to_ticker):
            result = future.result()
            if result and result.score >= min_matches:
                results.append(result)

    results.sort(key=lambda x: x.score, reverse=True)
    return results


def quick_scan_nifty50(strategy_name: str = "oversold_reversal") -> list[ScreenerResult]:
    """Quick scan of NIFTY50 stocks with a strategy."""
    return scan_stocks(NIFTY50_STOCKS, strategy_name=strategy_name)


def get_top_opportunities(
    watchlist_name: str = "NIFTY100",
    limit: int = 10,
) -> list[ScreenerResult]:
    """
    Get top trading opportunities from a watchlist.

    Scans for multiple bullish setups and returns the best ones.
    """
    stocks = get_stocks_from_watchlist(watchlist_name)
    if not stocks:
        stocks = NIFTY50_STOCKS

    # Combined bullish filters
    filters = [
        filter_rsi_oversold,
        filter_macd_bullish,
        filter_ma_trend_bullish,
        filter_high_volume,
        filter_near_bollinger_lower,
    ]

    results = scan_stocks(stocks, custom_filters=filters, min_matches=2)
    return results[:limit]


def get_risk_alerts(
    watchlist_name: str = "NIFTY100",
    limit: int = 10,
) -> list[ScreenerResult]:
    """
    Get stocks showing warning signs.

    Scans for overbought/bearish setups that might correct.
    """
    stocks = get_stocks_from_watchlist(watchlist_name)
    if not stocks:
        stocks = NIFTY50_STOCKS

    # Bearish/warning filters
    filters = [
        filter_rsi_overbought,
        filter_macd_bearish,
        filter_ma_trend_bearish,
        filter_near_bollinger_upper,
    ]

    results = scan_stocks(stocks, custom_filters=filters, min_matches=2)
    return results[:limit]


def format_screener_results(results: list[ScreenerResult]) -> str:
    """Format screener results for display."""
    if not results:
        return "No stocks match the criteria."

    lines = [f"Found {len(results)} stocks:\n"]

    for i, r in enumerate(results, 1):
        stars = "" * min(r.score, 5)
        lines.append(f"{i}. {r.ticker} {stars}")
        lines.append(f"   Price: {r.current_price}")
        lines.append(f"   RSI: {r.rsi} | MACD: {r.macd_trend} | MA: {r.ma_trend}")
        lines.append(f"   Matched: {', '.join(r.matched_criteria)}")
        lines.append("")

    return "\n".join(lines)
