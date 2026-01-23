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


class SwingSetupType(Enum):
    """Types of swing trade setups."""
    OVERSOLD_BOUNCE = "Oversold Bounce"
    PULLBACK_TO_EMA = "Pullback to EMA"
    BREAKOUT = "Breakout"
    MOMENTUM_CONTINUATION = "Momentum Continuation"
    MEAN_REVERSION = "Mean Reversion"
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


def find_support_resistance_levels(df: pd.DataFrame, lookback: int = 20) -> tuple[list[float], list[float]]:
    """
    Find multiple support and resistance levels.

    Returns:
        (support_levels, resistance_levels) - sorted lists
    """
    if df.empty or len(df) < lookback:
        return ([], [])

    recent_df = df.tail(lookback)

    # Find local minima (supports) and maxima (resistances)
    supports = []
    resistances = []

    highs = recent_df['High'].values
    lows = recent_df['Low'].values
    closes = recent_df['Close'].values

    # Simple pivot detection
    for i in range(2, len(recent_df) - 2):
        # Local high (resistance)
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            resistances.append(round(float(highs[i]), 2))

        # Local low (support)
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            supports.append(round(float(lows[i]), 2))

    # If no pivots found, use simple high/low
    if not resistances:
        resistances = [round(float(recent_df['High'].max()), 2)]
    if not supports:
        supports = [round(float(recent_df['Low'].min()), 2)]

    return (sorted(supports), sorted(resistances, reverse=True))


def calculate_relative_strength(ticker: str, days: int = 20) -> float:
    """Calculate relative strength vs NIFTY."""
    try:
        import yfinance as yf

        # Stock data
        stock_df = fetch_stock_history(ticker, days=days + 5)
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

        # Calculate total score
        total_score = technical_score
        if setups:
            total_score += max(s.confidence_score for s in setups) * 5
        if rs > 5:
            total_score += 10
        elif rs > 0:
            total_score += 5

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
            total_score=total_score
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
