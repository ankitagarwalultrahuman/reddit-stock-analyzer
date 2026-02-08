"""
Swing Trade Screener Module

Identifies swing trading opportunities based on:
- RSI oversold/overbought conditions
- MACD crossovers and momentum
- Price near support/resistance levels
- Volume breakouts
- Consolidation breakouts
- Relative strength analysis
"""

import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from stock_history import fetch_stock_history, get_current_price
from technical_analysis import get_technical_analysis
from watchlist_manager import NIFTY50_STOCKS, NIFTY100_STOCKS, SECTOR_STOCKS, get_sector_for_stock
from config import (
    SWING_VOLUME_THRESHOLD, SWING_RISK_REWARD_MIN,
    SR_CLUSTER_THRESHOLD_PCT, SR_PIVOT_PERIOD, SR_TOUCH_COUNT_MIN,
    FIBONACCI_LEVELS, SCREENER_RSI_OVERSOLD, SCREENER_RSI_OVERBOUGHT,
    ADX_STRONG_TREND, RS_LOOKBACK_DAYS, RS_BENCHMARK,
)


class SwingSetupType(Enum):
    """Types of swing trade setups."""
    OVERSOLD_BOUNCE = "Oversold Bounce"
    PULLBACK_TO_EMA = "Pullback to EMA"
    BREAKOUT = "Breakout"
    MOMENTUM_CONTINUATION = "Momentum Continuation"
    MEAN_REVERSION = "Mean Reversion"
    BREAKDOWN = "Breakdown Warning"
    SECTOR_ROTATION = "Sector Rotation"


@dataclass
class SwingSetup:
    """A potential swing trade setup."""
    ticker: str
    sector: str
    setup_type: SwingSetupType
    current_price: float
    entry_zone: tuple[float, float]  # (low, high) for entry
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    confidence_score: int  # 1-10
    signals: list[str]  # List of bullish/bearish signals
    technical_summary: dict
    relative_strength: float


@dataclass
class ScreenerResult:
    """Result of screening a single stock."""
    ticker: str
    sector: str
    current_price: float
    week_change: float
    rsi: float
    macd_signal: str
    ma_trend: str
    volume_signal: str
    technical_bias: str
    technical_score: int
    relative_strength: float
    support: float
    resistance: float
    setups: list[SwingSetup]
    total_score: int  # Aggregate score
    # 52-week high/low data
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    pct_from_52w_high: float = 0.0
    near_52w_high: bool = False


def _cluster_levels(levels: list[float], threshold_pct: float = SR_CLUSTER_THRESHOLD_PCT) -> list[tuple[float, int]]:
    """
    Cluster nearby price levels and count touches.

    Args:
        levels: Raw price levels
        threshold_pct: Percentage range to cluster nearby levels

    Returns:
        List of (level, touch_count) sorted by touch count descending
    """
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        if abs(level - current_cluster[0]) / current_cluster[0] * 100 < threshold_pct:
            current_cluster.append(level)
        else:
            avg = sum(current_cluster) / len(current_cluster)
            clusters.append((round(avg, 2), len(current_cluster)))
            current_cluster = [level]

    # Don't forget the last cluster
    avg = sum(current_cluster) / len(current_cluster)
    clusters.append((round(avg, 2), len(current_cluster)))

    # Sort by touch count (strongest levels first)
    clusters.sort(key=lambda x: x[1], reverse=True)
    return clusters


def find_support_resistance_levels(df: pd.DataFrame, lookback: int = 30) -> tuple[list[float], list[float]]:
    """
    Find multiple support and resistance levels with clustering.

    Uses flexible pivot detection (2-5 bars) and clusters nearby levels
    within SR_CLUSTER_THRESHOLD_PCT to find the strongest zones.

    Returns:
        (support_levels, resistance_levels) - sorted lists, top 3 each
    """
    if df.empty or len(df) < lookback:
        return ([], [])

    recent_df = df.tail(lookback)
    current_price = float(recent_df['Close'].iloc[-1])

    raw_supports = []
    raw_resistances = []

    highs = recent_df['High'].values
    lows = recent_df['Low'].values

    # Flexible pivot detection with windows of 2-5 bars
    for window in [2, 3, 4, 5]:
        for i in range(window, len(recent_df) - window):
            # Local high (resistance)
            is_high = all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
                      all(highs[i] >= highs[i+j] for j in range(1, min(window+1, len(recent_df)-i)))
            if is_high:
                raw_resistances.append(float(highs[i]))

            # Local low (support)
            is_low = all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
                     all(lows[i] <= lows[i+j] for j in range(1, min(window+1, len(recent_df)-i)))
            if is_low:
                raw_supports.append(float(lows[i]))

    # Cluster nearby levels
    support_clusters = _cluster_levels(raw_supports)
    resistance_clusters = _cluster_levels(raw_resistances)

    # Filter: supports below current price, resistances above
    supports = [level for level, count in support_clusters if level < current_price][:3]
    resistances = [level for level, count in resistance_clusters if level > current_price][:3]

    # Fallback if no pivots found
    if not resistances:
        resistances = [round(float(recent_df['High'].max()), 2)]
    if not supports:
        supports = [round(float(recent_df['Low'].min()), 2)]

    return (sorted(supports), sorted(resistances, reverse=True))


def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Calculate Fibonacci retracement levels from recent swing high/low.

    Args:
        df: DataFrame with 'High' and 'Low' columns
        lookback: Number of bars to look back

    Returns:
        dict with 'swing_high', 'swing_low', and 'levels' (dict of fib level -> price)
    """
    if df is None or df.empty or len(df) < 10:
        return {"swing_high": 0, "swing_low": 0, "levels": {}}

    recent = df.tail(min(lookback, len(df)))
    swing_high = float(recent['High'].max())
    swing_low = float(recent['Low'].min())
    diff = swing_high - swing_low

    if diff <= 0:
        return {"swing_high": swing_high, "swing_low": swing_low, "levels": {}}

    levels = {}
    for fib in FIBONACCI_LEVELS:
        # Retracement from high
        levels[fib] = round(swing_high - (diff * fib), 2)

    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "levels": levels,
    }


def calculate_relative_strength(ticker: str, days: int = RS_LOOKBACK_DAYS) -> float:
    """Calculate relative strength vs NIFTY."""
    try:
        import yfinance as yf

        # Stock data
        stock_df = fetch_stock_history(ticker, days=days + 10)
        if stock_df.empty or len(stock_df) < 5:
            return 0.0

        # NIFTY data
        nifty = yf.Ticker("^NSEI")
        nifty_df = nifty.history(period=f"{days + 10}d")

        if nifty_df.empty or len(nifty_df) < 5:
            return 0.0

        # Calculate returns
        stock_return = ((stock_df['Close'].iloc[-1] / stock_df['Close'].iloc[0]) - 1) * 100
        nifty_return = ((nifty_df['Close'].iloc[-1] / nifty_df['Close'].iloc[0]) - 1) * 100

        return round(stock_return - nifty_return, 2)

    except Exception:
        return 0.0


def detect_oversold_bounce_setup(
    ticker: str,
    current_price: float,
    rsi: float,
    macd_signal: str,
    supports: list[float],
    volume_ratio: float
) -> Optional[SwingSetup]:
    """
    Detect oversold bounce setup.

    Criteria:
    - RSI < 35 (oversold)
    - Price near support
    - MACD showing bullish divergence or crossover forming
    """
    if rsi >= 35:
        return None

    signals = [f"RSI oversold at {rsi:.1f}"]

    # Check if near support
    near_support = False
    closest_support = 0
    for support in supports:
        if support > 0:
            distance = ((current_price - support) / current_price) * 100
            if 0 <= distance < 3:
                near_support = True
                closest_support = support
                signals.append(f"Near support at ₹{support:.2f}")
                break

    if not near_support and supports:
        closest_support = supports[0]

    # MACD confirmation
    if macd_signal in ["bullish_crossover", "bullish"]:
        signals.append(f"MACD {macd_signal}")

    # Volume spike
    if volume_ratio > 1.5:
        signals.append(f"Volume spike {volume_ratio:.1f}x")

    # Calculate targets and stop
    stop_loss = closest_support * 0.97 if closest_support else current_price * 0.95
    target_1 = current_price * 1.05  # 5% target
    target_2 = current_price * 1.10  # 10% target

    risk = current_price - stop_loss
    reward = target_1 - current_price
    risk_reward = reward / risk if risk > 0 else 0

    # Confidence based on signal count
    confidence = min(len(signals) * 2 + (3 if near_support else 0), 10)

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.OVERSOLD_BOUNCE,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.01),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"rsi": rsi, "macd": macd_signal},
        relative_strength=0
    )


def detect_pullback_to_ema_setup(
    ticker: str,
    current_price: float,
    df: pd.DataFrame,
    tech_signals: dict,
    ma_trend: str
) -> Optional[SwingSetup]:
    """
    Detect pullback to moving average setup.

    Criteria:
    - Overall trend is bullish (price above 50 EMA)
    - Price pulled back to 20 or 50 EMA
    - RSI not overbought (< 65)
    """
    if ma_trend != "bullish":
        return None

    signals = []

    # Get EMAs from technical signals
    ema20 = tech_signals.get("ema20", 0)
    ema50 = tech_signals.get("ema50", 0)
    rsi = tech_signals.get("rsi", 50)

    if not ema20 or not ema50:
        return None

    # Check if price is near EMA20 or EMA50
    near_ema20 = abs((current_price - ema20) / current_price) < 0.02
    near_ema50 = abs((current_price - ema50) / current_price) < 0.03

    if not (near_ema20 or near_ema50):
        return None

    if near_ema20:
        signals.append(f"Pullback to 20 EMA at ₹{ema20:.2f}")
    if near_ema50:
        signals.append(f"Pullback to 50 EMA at ₹{ema50:.2f}")

    signals.append("Bullish MA alignment")

    if rsi < 65:
        signals.append(f"RSI healthy at {rsi:.1f}")

    # Stop below the EMA
    stop_loss = min(ema20, ema50) * 0.98 if ema20 and ema50 else current_price * 0.95
    target_1 = current_price * 1.06
    target_2 = current_price * 1.12

    risk = current_price - stop_loss
    reward = target_1 - current_price
    risk_reward = reward / risk if risk > 0 else 0

    confidence = min(len(signals) * 2 + 2, 10)

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.PULLBACK_TO_EMA,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.01),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"ema20": ema20, "ema50": ema50, "rsi": rsi},
        relative_strength=0
    )


def detect_breakout_setup(
    ticker: str,
    current_price: float,
    resistances: list[float],
    volume_ratio: float,
    macd_signal: str,
    rsi: float
) -> Optional[SwingSetup]:
    """
    Detect breakout setup.

    Criteria:
    - Price breaking above resistance
    - Volume confirmation (> 1.3x average)
    - MACD bullish
    - RSI not overbought
    """
    if not resistances:
        return None

    signals = []
    breaking_resistance = None

    # Check if breaking any resistance
    for resistance in resistances:
        if resistance > 0:
            distance = ((current_price - resistance) / resistance) * 100
            # Breaking resistance (0-2% above)
            if 0 <= distance < 2:
                breaking_resistance = resistance
                signals.append(f"Breaking resistance at ₹{resistance:.2f}")
                break

    if not breaking_resistance:
        return None

    # Volume confirmation
    if volume_ratio >= 1.3:
        signals.append(f"Volume breakout {volume_ratio:.1f}x")
    else:
        return None  # Volume is required for breakout

    # MACD
    if macd_signal in ["bullish_crossover", "bullish"]:
        signals.append(f"MACD {macd_signal}")

    # RSI check
    if rsi < 70:
        signals.append(f"RSI room to run at {rsi:.1f}")

    # Targets
    stop_loss = breaking_resistance * 0.97
    target_1 = current_price * 1.08
    target_2 = current_price * 1.15

    risk = current_price - stop_loss
    reward = target_1 - current_price
    risk_reward = reward / risk if risk > 0 else 0

    confidence = min(len(signals) * 2 + 2, 10)

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.BREAKOUT,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.02),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"resistance": breaking_resistance, "volume": volume_ratio},
        relative_strength=0
    )


def detect_momentum_continuation_setup(
    ticker: str,
    current_price: float,
    tech,
    supports: list[float],
    volume_ratio: float,
    rs: float,
    fib_levels: dict
) -> Optional[SwingSetup]:
    """
    Detect momentum continuation setup.

    Criteria:
    - MA trend bullish, ADX > 25 (strong trend)
    - RSI 50-70 (not overbought)
    - Price above EMA20
    - Positive relative strength
    """
    if not tech or not tech.ma_trend or tech.ma_trend != "bullish":
        return None

    rsi = tech.rsi or 50
    if rsi < 50 or rsi > 70:
        return None

    if tech.adx is not None and tech.adx < ADX_STRONG_TREND:
        return None

    if tech.price_vs_ema20 != "above":
        return None

    signals = []
    signals.append(f"Strong trend (ADX: {tech.adx:.1f})" if tech.adx else "Bullish MA alignment")
    signals.append(f"RSI healthy at {rsi:.1f}")
    signals.append("Price above EMA20")

    if rs > 0:
        signals.append(f"Outperforming NIFTY by {rs:.1f}%")

    if volume_ratio > 1.2:
        signals.append(f"Volume confirmation {volume_ratio:.1f}x")

    # Targets using Fibonacci extension if available
    ema20 = tech.ema_20 or current_price * 0.98
    stop_loss = ema20 * 0.97

    # Use Fibonacci for targets if available
    swing_high = fib_levels.get("swing_high", 0)
    if swing_high and swing_high > current_price:
        target_1 = swing_high
        target_2 = current_price + (swing_high - current_price) * 1.618
    else:
        target_1 = current_price * 1.06
        target_2 = current_price * 1.12

    risk = current_price - stop_loss
    reward = target_1 - current_price
    risk_reward = reward / risk if risk > 0 else 0

    # Weighted confidence
    confidence = _calculate_weighted_confidence(signals, {
        "Strong trend": 3, "ADX": 3, "Bullish MA": 2,
        "RSI healthy": 2, "EMA20": 1.5,
        "Outperforming": 1.5, "Volume": 2,
    })

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.MOMENTUM_CONTINUATION,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.01),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"adx": tech.adx, "rsi": rsi, "ma_trend": "bullish"},
        relative_strength=rs
    )


def detect_mean_reversion_setup(
    ticker: str,
    current_price: float,
    tech,
    supports: list[float],
    volume_ratio: float,
    rs: float
) -> Optional[SwingSetup]:
    """
    Detect mean reversion setup.

    Criteria:
    - RSI < 35 OR price below lower Bollinger Band
    - Bullish divergence detected
    - MACD histogram improving (less negative)
    """
    if not tech:
        return None

    rsi = tech.rsi or 50
    below_bb = tech.bb_position in ("below_lower", "near_lower")
    is_oversold = rsi < SCREENER_RSI_OVERSOLD

    if not (is_oversold or below_bb):
        return None

    signals = []

    if is_oversold:
        signals.append(f"RSI oversold at {rsi:.1f}")
    if below_bb:
        signals.append(f"Near/below lower Bollinger Band")

    # Bullish divergence is a strong signal for mean reversion
    has_divergence = tech.divergence == "bullish"
    if has_divergence:
        signals.append(f"Bullish divergence ({tech.divergence_strength})")

    # MACD improving
    if tech.macd_histogram is not None and tech.macd_trend in ("bullish_crossover", "bullish"):
        signals.append(f"MACD turning bullish")
    elif not has_divergence:
        return None  # Need either divergence or MACD improving

    if volume_ratio > 1.2:
        signals.append(f"Volume spike {volume_ratio:.1f}x")

    # Targets: revert to moving averages
    ema20 = tech.ema_20 or current_price * 1.03
    ema50 = tech.ema_50 or current_price * 1.06

    closest_support = supports[0] if supports else current_price * 0.95
    stop_loss = closest_support * 0.97

    target_1 = ema20
    target_2 = ema50

    risk = current_price - stop_loss
    reward = target_1 - current_price
    risk_reward = reward / risk if risk > 0 else 0

    confidence = _calculate_weighted_confidence(signals, {
        "RSI oversold": 2, "Bollinger": 2, "divergence": 3,
        "MACD": 2, "Volume": 1.5,
    })

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.MEAN_REVERSION,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.01),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"rsi": rsi, "bb_position": tech.bb_position, "divergence": tech.divergence},
        relative_strength=rs
    )


def detect_breakdown_setup(
    ticker: str,
    current_price: float,
    tech,
    supports: list[float],
    volume_ratio: float,
    rs: float
) -> Optional[SwingSetup]:
    """
    Detect breakdown warning (price breaking support).

    This is a WARNING signal, not a buy setup.

    Criteria:
    - Price 0-2% below support
    - Volume > 1.3x average
    - MACD bearish
    - RSI > 30 (not already crashed)
    """
    if not tech or not supports:
        return None

    rsi = tech.rsi or 50
    if rsi < 30:
        return None  # Already crashed

    signals = []
    breaking_support = None

    for support in supports:
        if support > 0:
            distance = ((current_price - support) / support) * 100
            if -2 <= distance <= 0:
                breaking_support = support
                signals.append(f"Breaking support at ₹{support:.2f}")
                break

    if not breaking_support:
        return None

    if volume_ratio < SWING_VOLUME_THRESHOLD:
        return None  # Need volume confirmation

    signals.append(f"Volume breakdown {volume_ratio:.1f}x")

    if tech.macd_trend in ("bearish_crossover", "bearish"):
        signals.append(f"MACD {tech.macd_trend}")
    else:
        return None  # Need bearish momentum

    if rsi > 30:
        signals.append(f"RSI at {rsi:.1f} (room to fall)")

    # For breakdown, stop is ABOVE support (exit if wrong)
    stop_loss = breaking_support * 1.03
    target_1 = breaking_support * 0.92
    target_2 = breaking_support * 0.85

    risk = stop_loss - current_price
    reward = current_price - target_1
    risk_reward = reward / risk if risk > 0 else 0

    confidence = _calculate_weighted_confidence(signals, {
        "Breaking support": 3, "Volume": 2, "MACD": 2, "RSI": 1,
    })

    return SwingSetup(
        ticker=ticker,
        sector=get_sector_for_stock(ticker) or "Unknown",
        setup_type=SwingSetupType.BREAKDOWN,
        current_price=current_price,
        entry_zone=(current_price * 0.99, current_price * 1.01),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        risk_reward=round(risk_reward, 2),
        confidence_score=confidence,
        signals=signals,
        technical_summary={"support": breaking_support, "volume": volume_ratio, "rsi": rsi},
        relative_strength=rs
    )


def _calculate_weighted_confidence(signals: list[str], weight_map: dict) -> int:
    """
    Calculate weighted confidence score from signal list.

    Matches signal text against weight_map keys (case-insensitive substring).
    Returns score clamped to 1-10.
    """
    total_weight = 0.0
    for signal in signals:
        signal_lower = signal.lower()
        for key, weight in weight_map.items():
            if key.lower() in signal_lower:
                total_weight += weight
                break

    return max(1, min(int(total_weight), 10))


def screen_stock(ticker: str) -> Optional[ScreenerResult]:
    """Screen a single stock for swing setups."""
    try:
        # Get historical data
        df = fetch_stock_history(ticker, days=60, force_refresh=True)
        if df.empty or len(df) < 20:
            return None

        # Get current price
        price_data = get_current_price(ticker)
        if price_data.get("success"):
            current_price = price_data["current_price"]
        else:
            current_price = float(df['Close'].iloc[-1])

        # Week change
        week_change = 0
        if len(df) >= 5:
            week_ago = float(df['Close'].iloc[-5])
            week_change = ((current_price - week_ago) / week_ago) * 100

        # Volume ratio
        volume_ratio = 1.0
        if 'Volume' in df.columns:
            current_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Volume'].tail(20).mean())
            volume_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

        # Technical analysis - pass the DataFrame we already have
        tech = get_technical_analysis(df, ticker)
        if not tech:
            return None

        rsi = tech.rsi or 50
        macd_signal = tech.macd_trend or "neutral"
        ma_trend = tech.ma_trend or "mixed"
        volume_signal = tech.volume_signal or "normal"
        technical_bias = tech.technical_bias or "neutral"
        technical_score = tech.technical_score or 50

        # Support/Resistance
        supports, resistances = find_support_resistance_levels(df)
        support = supports[0] if supports else 0
        resistance = resistances[0] if resistances else 0

        # Relative strength
        rs = calculate_relative_strength(ticker)

        # Technical summary for setup detection
        tech_summary = {
            "rsi": rsi,
            "macd": macd_signal,
            "ma_trend": ma_trend,
            "ema20": tech.ema_20,
            "ema50": tech.ema_50,
            "volume_ratio": volume_ratio
        }

        # Calculate Fibonacci levels
        fib_levels = calculate_fibonacci_levels(df)

        # Detect setups
        setups = []

        # 1. Oversold bounce
        oversold = detect_oversold_bounce_setup(
            ticker, current_price, rsi, macd_signal, supports, volume_ratio
        )
        if oversold:
            oversold.relative_strength = rs
            setups.append(oversold)

        # 2. Pullback to EMA
        pullback = detect_pullback_to_ema_setup(
            ticker, current_price, df, tech_summary, ma_trend
        )
        if pullback:
            pullback.relative_strength = rs
            setups.append(pullback)

        # 3. Breakout
        breakout = detect_breakout_setup(
            ticker, current_price, resistances, volume_ratio, macd_signal, rsi
        )
        if breakout:
            breakout.relative_strength = rs
            setups.append(breakout)

        # 4. Momentum Continuation
        momentum = detect_momentum_continuation_setup(
            ticker, current_price, tech, supports, volume_ratio, rs, fib_levels
        )
        if momentum:
            setups.append(momentum)

        # 5. Mean Reversion
        mean_rev = detect_mean_reversion_setup(
            ticker, current_price, tech, supports, volume_ratio, rs
        )
        if mean_rev:
            setups.append(mean_rev)

        # 6. Breakdown Warning
        breakdown = detect_breakdown_setup(
            ticker, current_price, tech, supports, volume_ratio, rs
        )
        if breakdown:
            setups.append(breakdown)

        # Calculate total score (normalized to 0-100)
        total_score = technical_score  # Already 0-100
        if setups:
            setup_bonus = max(s.confidence_score for s in setups) * 3  # max 30
            rs_bonus = min(rs * 2, 10) if rs > 0 else 0
            total_score = min(int(technical_score * 0.6 + setup_bonus + rs_bonus), 100)
        elif rs > 5:
            total_score = min(technical_score + 10, 100)
        elif rs > 0:
            total_score = min(technical_score + 5, 100)

        return ScreenerResult(
            ticker=ticker,
            sector=get_sector_for_stock(ticker) or "Unknown",
            current_price=round(current_price, 2),
            week_change=round(week_change, 2),
            rsi=round(rsi, 1),
            macd_signal=macd_signal,
            ma_trend=ma_trend,
            volume_signal=volume_signal,
            technical_bias=technical_bias,
            technical_score=technical_score,
            relative_strength=rs,
            support=support,
            resistance=resistance,
            setups=setups,
            total_score=total_score,
            # 52-week high/low from technical analysis
            week_52_high=tech.week_52_high or 0.0,
            week_52_low=tech.week_52_low or 0.0,
            pct_from_52w_high=tech.pct_from_52w_high or 0.0,
            near_52w_high=tech.near_52w_high or False
        )

    except Exception as e:
        print(f"Error screening {ticker}: {e}")
        return None


def run_swing_screener(
    stocks: list[str] = None,
    min_score: int = 60,
    setup_types: list[SwingSetupType] = None,
    max_workers: int = 5
) -> list[ScreenerResult]:
    """
    Run swing screener on a list of stocks.

    Args:
        stocks: List of tickers (defaults to NIFTY100)
        min_score: Minimum total score to include
        setup_types: Filter by specific setup types
        max_workers: Parallel workers

    Returns:
        List of ScreenerResult sorted by total_score
    """
    if stocks is None:
        stocks = NIFTY100_STOCKS

    print(f"Screening {len(stocks)} stocks for swing setups...")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(screen_stock, ticker): ticker for ticker in stocks}
        for future in as_completed(futures):
            result = future.result()
            if result and result.total_score >= min_score:
                # Filter by setup type if specified
                if setup_types:
                    result.setups = [s for s in result.setups if s.setup_type in setup_types]
                    if not result.setups:
                        continue
                results.append(result)

    # Sort by total score
    results.sort(key=lambda x: x.total_score, reverse=True)

    print(f"Found {len(results)} stocks matching criteria")
    return results


def get_top_swing_setups(results: list[ScreenerResult], top_n: int = 10) -> list[SwingSetup]:
    """Extract top swing setups from screener results."""
    all_setups = []
    for result in results:
        all_setups.extend(result.setups)

    # Sort by confidence and risk/reward
    all_setups.sort(key=lambda x: (x.confidence_score, x.risk_reward), reverse=True)

    return all_setups[:top_n]


def get_screener_summary(results: list[ScreenerResult]) -> dict:
    """Get summary statistics from screener results."""
    if not results:
        return {}

    total_setups = sum(len(r.setups) for r in results)
    setup_counts = {}
    for r in results:
        for s in r.setups:
            setup_counts[s.setup_type.value] = setup_counts.get(s.setup_type.value, 0) + 1

    sectors = {}
    for r in results:
        sectors[r.sector] = sectors.get(r.sector, 0) + 1

    return {
        "stocks_screened": len(results),
        "total_setups": total_setups,
        "setup_breakdown": setup_counts,
        "sectors_represented": sectors,
        "avg_score": sum(r.total_score for r in results) / len(results),
        "avg_rs": sum(r.relative_strength for r in results) / len(results)
    }


if __name__ == "__main__":
    # Test run
    results = run_swing_screener(stocks=NIFTY50_STOCKS[:20], min_score=50)

    print("\n=== SWING SCREENER RESULTS ===\n")

    for r in results[:10]:
        print(f"{r.ticker} ({r.sector})")
        print(f"  Price: ₹{r.current_price} | Week: {r.week_change:+.1f}%")
        print(f"  RSI: {r.rsi} | MACD: {r.macd_signal} | Bias: {r.technical_bias}")
        print(f"  RS vs NIFTY: {r.relative_strength:+.1f}%")
        print(f"  Score: {r.total_score}")
        if r.setups:
            print(f"  Setups:")
            for s in r.setups:
                print(f"    - {s.setup_type.value} (Confidence: {s.confidence_score}/10, R:R {s.risk_reward})")
                print(f"      Entry: ₹{s.entry_zone[0]:.2f}-{s.entry_zone[1]:.2f}")
                print(f"      Stop: ₹{s.stop_loss} | T1: ₹{s.target_1} | T2: ₹{s.target_2}")
        print()

    print("\n=== SUMMARY ===")
    summary = get_screener_summary(results)
    print(f"Stocks with setups: {summary.get('stocks_screened', 0)}")
    print(f"Total setups found: {summary.get('total_setups', 0)}")
    print(f"Setup breakdown: {summary.get('setup_breakdown', {})}")
