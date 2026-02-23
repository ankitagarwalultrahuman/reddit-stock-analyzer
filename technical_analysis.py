"""
Technical Analysis Module - Calculates key technical indicators for stocks.

Provides RSI, MACD, Moving Averages, Bollinger Bands, and ATR calculations
using pandas-ta library for reliable indicator calculations.
"""

import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass

from config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, RSI_NEAR_OVERSOLD, RSI_NEAR_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    EMA_SHORT, EMA_MEDIUM, EMA_LONG,
    BB_PERIOD, BB_STD_DEV, ATR_PERIOD,
    ADX_PERIOD, ADX_STRONG_TREND, ADX_WEAK_TREND,
    STOCH_RSI_PERIOD, STOCH_RSI_OVERSOLD, STOCH_RSI_OVERBOUGHT,
    VOLUME_SIGNAL_HIGH,
)

# Try importing pandas-ta, fall back to manual calculations if not available
try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    print("Warning: pandas-ta not installed. Using manual calculations.")


@dataclass
class TechnicalSignals:
    """Container for all technical indicators for a stock."""
    ticker: str
    current_price: float

    # 52-Week High/Low
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    pct_from_52w_high: Optional[float] = None  # Negative = below high
    pct_from_52w_low: Optional[float] = None   # Positive = above low
    near_52w_high: bool = False  # Within 5% of 52-week high
    near_52w_low: bool = False   # Within 5% of 52-week low

    # RSI
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None  # "oversold", "overbought", "neutral"

    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_trend: Optional[str] = None  # "bullish_crossover", "bearish_crossover", "bullish", "bearish"

    # Moving Averages
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    price_vs_ema20: Optional[str] = None  # "above", "below", "at"
    price_vs_ema50: Optional[str] = None
    price_vs_ema200: Optional[str] = None
    ma_trend: Optional[str] = None  # "bullish" (20>50>200), "bearish", "mixed"

    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_position: Optional[str] = None  # "above_upper", "near_upper", "middle", "near_lower", "below_lower"
    bb_width: Optional[float] = None  # Volatility indicator

    # ATR (Average True Range)
    atr: Optional[float] = None
    atr_percent: Optional[float] = None  # ATR as % of price
    volatility_level: Optional[str] = None  # "high", "medium", "low"

    # Volume
    volume: Optional[int] = None
    volume_avg: Optional[float] = None
    volume_ratio: Optional[float] = None  # Current vs average
    volume_signal: Optional[str] = None  # "high", "normal", "low"

    # ADX (Average Directional Index)
    adx: Optional[float] = None
    adx_signal: str = "neutral"  # "strong_trend", "weak_trend", "no_trend"
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None

    # Stochastic RSI
    stoch_rsi_k: Optional[float] = None
    stoch_rsi_d: Optional[float] = None
    stoch_rsi_signal: str = "neutral"  # "oversold", "overbought", "bullish_cross", "bearish_cross"

    # Divergence
    divergence: Optional[str] = None  # "bullish", "bearish", None
    divergence_strength: Optional[str] = None  # "strong", "moderate"

    # Overall technical score (0-100)
    technical_score: Optional[int] = None
    technical_bias: Optional[str] = None  # "bullish", "bearish", "neutral"


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        df: DataFrame with 'Close' column
        period: RSI period (default 14)

    Returns:
        Series with RSI values
    """
    if PANDAS_TA_AVAILABLE:
        try:
            result = ta.rsi(df['Close'], length=period)
            if result is not None:
                return result
        except Exception:
            pass  # Fall back to manual calculation

    # Manual RSI calculation (fallback) using Wilder's exponential smoothing
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period).mean()

    rs = gain / loss.replace(0, float('nan'))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        df: DataFrame with 'Close' column
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)

    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    if PANDAS_TA_AVAILABLE:
        try:
            macd_df = ta.macd(df['Close'], fast=fast, slow=slow, signal=signal)
            if macd_df is not None and not macd_df.empty:
                # Find columns dynamically (pandas-ta column names can vary)
                macd_col = None
                signal_col = None
                hist_col = None

                for col in macd_df.columns:
                    col_lower = col.lower()
                    if col.startswith('MACD_') or col_lower == 'macd':
                        macd_col = col
                    elif col.startswith('MACDs_') or 'signal' in col_lower:
                        signal_col = col
                    elif col.startswith('MACDh_') or 'hist' in col_lower:
                        hist_col = col

                if macd_col and signal_col and hist_col:
                    return macd_df[macd_col], macd_df[signal_col], macd_df[hist_col]
        except Exception:
            pass  # Fall back to manual calculation

    # Manual MACD calculation (fallback)
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    if PANDAS_TA_AVAILABLE:
        try:
            result = ta.ema(df['Close'], length=period)
            if result is not None:
                return result
        except Exception:
            pass  # Fall back to manual calculation
    return df['Close'].ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> tuple:
    """
    Calculate Bollinger Bands.

    Args:
        df: DataFrame with 'Close' column
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)

    Returns:
        Tuple of (Upper band, Middle band, Lower band)
    """
    if PANDAS_TA_AVAILABLE:
        try:
            bb = ta.bbands(df['Close'], length=period, std=std_dev)
            if bb is not None and not bb.empty:
                # pandas-ta column names can vary - try multiple formats
                # Format 1: BBU_20_2.0 (with decimal)
                # Format 2: BBU_20_2 (without decimal)
                upper_col = None
                middle_col = None
                lower_col = None

                for col in bb.columns:
                    if col.startswith('BBU'):
                        upper_col = col
                    elif col.startswith('BBM'):
                        middle_col = col
                    elif col.startswith('BBL'):
                        lower_col = col

                if upper_col and middle_col and lower_col:
                    return bb[upper_col], bb[middle_col], bb[lower_col]
        except Exception as e:
            # Fall back to manual calculation if pandas-ta fails
            pass

    # Manual Bollinger Bands calculation (fallback)
    middle = df['Close'].rolling(window=period).mean()
    std = df['Close'].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    Args:
        df: DataFrame with 'High', 'Low', 'Close' columns
        period: ATR period (default 14)

    Returns:
        Series with ATR values
    """
    if PANDAS_TA_AVAILABLE:
        try:
            result = ta.atr(df['High'], df['Low'], df['Close'], length=period)
            if result is not None:
                return result
        except Exception:
            pass  # Fall back to manual calculation

    # Manual ATR calculation (fallback)
    high_low = df['High'] - df['Low']
    high_close_prev = abs(df['High'] - df['Close'].shift(1))
    low_close_prev = abs(df['Low'] - df['Close'].shift(1))

    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()  # Wilder's smoothing

    return atr


def calculate_volume_analysis(df: pd.DataFrame, period: int = 20) -> tuple:
    """
    Analyze volume patterns.

    Args:
        df: DataFrame with 'Volume' column
        period: Period for average volume calculation

    Returns:
        Tuple of (average volume, volume ratio)
    """
    if 'Volume' not in df.columns or df['Volume'].isna().all():
        return None, None

    avg_volume = df['Volume'].rolling(window=period).mean().iloc[-1]
    current_volume = df['Volume'].iloc[-1]

    volume_ratio = current_volume / avg_volume if avg_volume > 0 else None

    return avg_volume, volume_ratio


def calculate_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> tuple:
    """
    Calculate Average Directional Index (ADX) with +DI and -DI.

    Args:
        df: DataFrame with 'High', 'Low', 'Close' columns
        period: ADX period (default from config)

    Returns:
        Tuple of (ADX value, +DI value, -DI value) or (None, None, None) on error
    """
    if df is None or df.empty or len(df) < period * 2:
        return None, None, None

    if PANDAS_TA_AVAILABLE:
        try:
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=period)
            if adx_df is not None and not adx_df.empty:
                adx_col = None
                dmp_col = None
                dmn_col = None
                for col in adx_df.columns:
                    if col.startswith('ADX_'):
                        adx_col = col
                    elif col.startswith('DMP_'):
                        dmp_col = col
                    elif col.startswith('DMN_'):
                        dmn_col = col
                if adx_col and dmp_col and dmn_col:
                    adx_val = adx_df[adx_col].iloc[-1]
                    plus_di = adx_df[dmp_col].iloc[-1]
                    minus_di = adx_df[dmn_col].iloc[-1]
                    if not np.isnan(adx_val):
                        return float(adx_val), float(plus_di), float(minus_di)
        except Exception:
            pass

    # Manual ADX calculation fallback
    try:
        high = df['High']
        low = df['Low']
        close = df['Close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.ewm(alpha=1/period, min_periods=period).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, float('nan'))
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()

        adx_val = adx.iloc[-1]
        if not np.isnan(adx_val):
            return float(adx_val), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])
    except Exception:
        pass

    return None, None, None


def calculate_stoch_rsi(df: pd.DataFrame, period: int = STOCH_RSI_PERIOD) -> tuple:
    """
    Calculate Stochastic RSI (%K and %D).

    Args:
        df: DataFrame with 'Close' column
        period: Stochastic RSI period

    Returns:
        Tuple of (%K value, %D value) or (None, None)
    """
    if df is None or df.empty or len(df) < period * 2:
        return None, None

    if PANDAS_TA_AVAILABLE:
        try:
            stoch_rsi_df = ta.stochrsi(df['Close'], length=period)
            if stoch_rsi_df is not None and not stoch_rsi_df.empty:
                k_col = None
                d_col = None
                for col in stoch_rsi_df.columns:
                    if 'STOCHRSIk' in col:
                        k_col = col
                    elif 'STOCHRSId' in col:
                        d_col = col
                if k_col and d_col:
                    k_val = stoch_rsi_df[k_col].iloc[-1]
                    d_val = stoch_rsi_df[d_col].iloc[-1]
                    if not np.isnan(k_val):
                        return float(k_val), float(d_val)
        except Exception:
            pass

    # Manual Stochastic RSI calculation
    try:
        rsi_series = calculate_rsi(df, period)
        if rsi_series is None:
            return None, None

        rsi_min = rsi_series.rolling(window=period).min()
        rsi_max = rsi_series.rolling(window=period).max()
        rsi_range = rsi_max - rsi_min

        stoch_rsi_k = ((rsi_series - rsi_min) / rsi_range.replace(0, float('nan'))) * 100
        stoch_rsi_d = stoch_rsi_k.rolling(window=3).mean()

        k_val = stoch_rsi_k.iloc[-1]
        d_val = stoch_rsi_d.iloc[-1]

        if not np.isnan(k_val):
            return float(k_val), float(d_val) if not np.isnan(d_val) else None
    except Exception:
        pass

    return None, None


def detect_divergence(df: pd.DataFrame, rsi_series: pd.Series = None, lookback: int = 20) -> dict:
    """
    Detect RSI/Price divergence.

    Bullish divergence: price makes lower low, RSI makes higher low
    Bearish divergence: price makes higher high, RSI makes lower high

    Args:
        df: DataFrame with 'Close', 'Low', 'High' columns
        rsi_series: Pre-calculated RSI series (will calculate if None)
        lookback: Number of bars to look back for divergence

    Returns:
        dict with 'type' ("bullish"/"bearish"/None) and 'strength' ("strong"/"moderate")
    """
    result = {"type": None, "strength": None}

    if df is None or df.empty or len(df) < lookback + 10:
        return result

    try:
        if rsi_series is None:
            rsi_series = calculate_rsi(df)
        if rsi_series is None or len(rsi_series) < lookback:
            return result

        recent_close = df['Close'].iloc[-lookback:]
        recent_rsi = rsi_series.iloc[-lookback:]
        recent_low = df['Low'].iloc[-lookback:] if 'Low' in df.columns else recent_close
        recent_high = df['High'].iloc[-lookback:] if 'High' in df.columns else recent_close

        # Split into two halves to compare
        mid = lookback // 2
        first_half_low = recent_low.iloc[:mid].min()
        second_half_low = recent_low.iloc[mid:].min()
        first_half_rsi_at_low = recent_rsi.iloc[:mid].min()
        second_half_rsi_at_low = recent_rsi.iloc[mid:].min()

        first_half_high = recent_high.iloc[:mid].max()
        second_half_high = recent_high.iloc[mid:].max()
        first_half_rsi_at_high = recent_rsi.iloc[:mid].max()
        second_half_rsi_at_high = recent_rsi.iloc[mid:].max()

        # Bullish divergence: price lower low, RSI higher low
        if second_half_low < first_half_low and second_half_rsi_at_low > first_half_rsi_at_low:
            price_diff_pct = abs((second_half_low - first_half_low) / first_half_low) * 100
            rsi_diff = second_half_rsi_at_low - first_half_rsi_at_low
            strength = "strong" if (price_diff_pct > 2 and rsi_diff > 5) else "moderate"
            result = {"type": "bullish", "strength": strength}

        # Bearish divergence: price higher high, RSI lower high
        elif second_half_high > first_half_high and second_half_rsi_at_high < first_half_rsi_at_high:
            price_diff_pct = abs((second_half_high - first_half_high) / first_half_high) * 100
            rsi_diff = first_half_rsi_at_high - second_half_rsi_at_high
            strength = "strong" if (price_diff_pct > 2 and rsi_diff > 5) else "moderate"
            result = {"type": "bearish", "strength": strength}

    except Exception:
        pass

    return result


def calculate_52_week_high_low(df: pd.DataFrame, ticker: str = None) -> tuple:
    """
    Calculate 52-week high and low.

    If the provided DataFrame has less than 200 trading days and a ticker is given,
    fetches 1-year historical data directly from yfinance to get accurate 52-week values.

    Args:
        df: DataFrame with 'High' and 'Low' columns
        ticker: Stock ticker symbol (used to fetch full 1-year data if df is too short)

    Returns:
        Tuple of (52_week_high, 52_week_low)
    """
    if df is None or df.empty:
        return None, None

    # If we don't have enough data for a proper 52-week calculation, fetch it
    if len(df) < 200 and ticker:
        try:
            import yfinance as yf
            from stock_history import get_nse_symbol
            from datetime import datetime, timedelta

            yf_symbol = get_nse_symbol(ticker)
            stock = yf.Ticker(yf_symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=375)  # ~1 year + buffer for weekends/holidays

            yearly_df = stock.history(start=start_date, end=end_date)
            if yearly_df is not None and not yearly_df.empty and len(yearly_df) > len(df):
                df = yearly_df
        except Exception:
            pass  # Fall back to whatever data we have

    # Use last 252 trading days (approximately 52 weeks)
    period = min(252, len(df))
    recent_df = df.tail(period)

    week_52_high = recent_df['High'].max() if 'High' in df.columns else recent_df['Close'].max()
    week_52_low = recent_df['Low'].min() if 'Low' in df.columns else recent_df['Close'].min()

    return week_52_high, week_52_low


def get_rsi_signal(rsi: float) -> str:
    """Interpret RSI value."""
    if rsi is None or np.isnan(rsi):
        return "unknown"
    if rsi < RSI_OVERSOLD:
        return "oversold"
    elif rsi > RSI_OVERBOUGHT:
        return "overbought"
    elif rsi < RSI_NEAR_OVERSOLD:
        return "near_oversold"
    elif rsi > RSI_NEAR_OVERBOUGHT:
        return "near_overbought"
    return "neutral"


def get_macd_trend(macd: float, signal: float, histogram: float, prev_histogram: float = None) -> str:
    """Interpret MACD values."""
    if macd is None or signal is None:
        return "unknown"

    # Check for crossover
    if prev_histogram is not None:
        if prev_histogram < 0 and histogram >= 0:
            return "bullish_crossover"
        elif prev_histogram > 0 and histogram <= 0:
            return "bearish_crossover"

    # General trend
    if histogram > 0:
        return "bullish"
    elif histogram < 0:
        return "bearish"
    return "neutral"


def get_price_vs_ma(price: float, ma: float) -> str:
    """Compare price to moving average."""
    if ma is None or np.isnan(ma):
        return "unknown"

    pct_diff = ((price - ma) / ma) * 100

    if pct_diff > 2:
        return "above"
    elif pct_diff < -2:
        return "below"
    return "at"


def get_ma_trend(ema_20: float, ema_50: float, ema_200: float) -> str:
    """Determine overall MA trend alignment."""
    if any(x is None or np.isnan(x) for x in [ema_20, ema_50, ema_200]):
        return "unknown"

    if ema_20 > ema_50 > ema_200:
        return "bullish"
    elif ema_20 < ema_50 < ema_200:
        return "bearish"
    return "mixed"


def get_bb_position(price: float, upper: float, middle: float, lower: float) -> str:
    """Determine price position within Bollinger Bands."""
    if any(x is None or np.isnan(x) for x in [upper, middle, lower]):
        return "unknown"

    if price > upper:
        return "above_upper"
    elif price > upper - (upper - middle) * 0.2:
        return "near_upper"
    elif price < lower:
        return "below_lower"
    elif price < lower + (middle - lower) * 0.2:
        return "near_lower"
    return "middle"


def get_volatility_level(atr_percent: float) -> str:
    """Classify volatility based on ATR percentage."""
    if atr_percent is None or np.isnan(atr_percent):
        return "unknown"

    if atr_percent > 4:
        return "high"
    elif atr_percent > 2:
        return "medium"
    return "low"


def get_volume_signal(volume_ratio: float) -> str:
    """Interpret volume ratio."""
    if volume_ratio is None or np.isnan(volume_ratio):
        return "unknown"

    if volume_ratio > VOLUME_SIGNAL_HIGH:
        return "high"
    elif volume_ratio < 0.5:
        return "low"
    return "normal"


def calculate_technical_score(signals: TechnicalSignals) -> tuple:
    """
    Calculate overall technical score (0-100) and bias.

    Scoring (rebalanced for swing trading):
    - RSI: +15 if oversold (trend-context aware), -15 if overbought, +8/-8 for near levels
    - MACD: +18 for bullish_crossover, +10 for bullish, -18/-10 for bearish
    - MA Trend: +15 for bullish, -15 for bearish
    - Price vs EMA50: +8 if above, -8 if below
    - Volume: +8 if high confirming direction, -8 if confirming opposite
    - ADX: ±8 for strong trend amplification, ±8 dampening for no trend
    - Divergence: +12/-12
    - BB Position: +5/-5
    - Stochastic RSI: +8/-8
    - 52-week proximity: +5 near low, -5 near high

    Base score starts at 50 (neutral).

    Returns:
        Tuple of (score 0-100, bias string)
    """
    score = 50  # Start neutral

    # RSI contribution (trend-context aware)
    # RSI oversold in a bearish trend is NOT a buy signal — reduce bonus
    if signals.rsi_signal == "oversold":
        if signals.ma_trend == "bearish":
            score += 5   # Oversold in downtrend — might keep falling
        else:
            score += 15  # Oversold in uptrend/mixed — good bounce candidate
    elif signals.rsi_signal == "overbought":
        if signals.ma_trend == "bullish":
            score -= 5   # Overbought in uptrend — momentum may continue
        else:
            score -= 15  # Overbought in downtrend/mixed — likely to drop
    elif signals.rsi_signal == "near_oversold":
        score += 8
    elif signals.rsi_signal == "near_overbought":
        score -= 8

    # MACD contribution (reduced from 25 to 18 to prevent single-indicator dominance)
    if signals.macd_trend == "bullish_crossover":
        score += 18
    elif signals.macd_trend == "bullish":
        score += 10
    elif signals.macd_trend == "bearish_crossover":
        score -= 18
    elif signals.macd_trend == "bearish":
        score -= 10

    # MA trend contribution
    if signals.ma_trend == "bullish":
        score += 15
    elif signals.ma_trend == "bearish":
        score -= 15

    # Price vs EMA50 contribution
    if signals.price_vs_ema50 == "above":
        score += 8
    elif signals.price_vs_ema50 == "below":
        score -= 8

    # Volume contribution (independent of current score direction)
    if signals.volume_signal == "high":
        # High volume confirms the prevailing MA trend, not the intermediate score
        if signals.ma_trend == "bullish":
            score += 8
        elif signals.ma_trend == "bearish":
            score -= 8
        else:
            # In mixed trend, amplify whatever direction the score is leaning
            if score > 52:
                score += 5
            elif score < 48:
                score -= 5

    # ADX contribution (stronger dampening for no-trend environments)
    if signals.adx is not None:
        if signals.adx > ADX_STRONG_TREND:
            # Strong trend - amplify existing directional score
            if score > 55:
                score += 8
            elif score < 45:
                score -= 8
        elif signals.adx < ADX_WEAK_TREND:
            # No clear trend - dampen directional score toward neutral more aggressively
            if score > 58:
                score -= 8
            elif score < 42:
                score += 8

    # Divergence contribution
    if signals.divergence == "bullish":
        score += 12
    elif signals.divergence == "bearish":
        score -= 12

    # Bollinger Band position contribution
    if signals.bb_position == "near_lower" or signals.bb_position == "below_lower":
        score += 5
    elif signals.bb_position == "near_upper" or signals.bb_position == "above_upper":
        score -= 5

    # Stochastic RSI contribution
    if signals.stoch_rsi_signal == "oversold" or signals.stoch_rsi_signal == "bullish_cross":
        score += 8
    elif signals.stoch_rsi_signal == "overbought" or signals.stoch_rsi_signal == "bearish_cross":
        score -= 8

    # 52-week proximity bonus
    if signals.near_52w_low:
        score += 5  # Potential value buy
    elif signals.near_52w_high:
        score -= 3  # Near highs, but breakout possible so smaller penalty

    # Clamp to 0-100
    score = max(0, min(100, score))

    # Determine bias (tighter neutral band for more actionable signals)
    if score >= 60:
        bias = "bullish"
    elif score <= 40:
        bias = "bearish"
    else:
        bias = "neutral"

    return score, bias


def get_technical_analysis(df: pd.DataFrame, ticker: str) -> TechnicalSignals:
    """
    Perform complete technical analysis on a stock.

    Args:
        df: DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
        ticker: Stock ticker symbol

    Returns:
        TechnicalSignals object with all indicators
    """
    if df is None or df.empty or len(df) < 30:
        return TechnicalSignals(ticker=ticker, current_price=0)

    # Get current price
    current_price = df['Close'].iloc[-1]

    # Calculate RSI
    rsi_series = calculate_rsi(df)
    rsi = rsi_series.iloc[-1] if rsi_series is not None else None

    # Calculate MACD
    macd_line, signal_line, histogram = calculate_macd(df)
    macd = macd_line.iloc[-1] if macd_line is not None else None
    macd_signal = signal_line.iloc[-1] if signal_line is not None else None
    macd_hist = histogram.iloc[-1] if histogram is not None else None
    prev_hist = histogram.iloc[-2] if histogram is not None and len(histogram) > 1 else None

    # Calculate EMAs
    ema_20 = calculate_ema(df, 20)
    ema_50 = calculate_ema(df, 50)
    ema_200 = calculate_ema(df, 200)

    ema_20_val = ema_20.iloc[-1] if ema_20 is not None else None
    ema_50_val = ema_50.iloc[-1] if ema_50 is not None else None
    ema_200_val = ema_200.iloc[-1] if ema_200 is not None else None

    # Calculate Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df)
    bb_upper_val = bb_upper.iloc[-1] if bb_upper is not None else None
    bb_middle_val = bb_middle.iloc[-1] if bb_middle is not None else None
    bb_lower_val = bb_lower.iloc[-1] if bb_lower is not None else None

    # Calculate BB width (volatility indicator)
    bb_width = None
    if bb_upper_val and bb_lower_val and bb_middle_val:
        bb_width = ((bb_upper_val - bb_lower_val) / bb_middle_val) * 100

    # Calculate ATR
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if atr_series is not None else None
    atr_percent = (atr / current_price) * 100 if atr and current_price else None

    # Calculate Volume analysis
    volume_avg, volume_ratio = calculate_volume_analysis(df)
    current_volume = int(df['Volume'].iloc[-1]) if 'Volume' in df.columns else None

    # Calculate ADX
    adx_val, plus_di_val, minus_di_val = calculate_adx(df)
    adx_signal = "neutral"
    if adx_val is not None:
        if adx_val > ADX_STRONG_TREND:
            adx_signal = "strong_trend"
        elif adx_val < ADX_WEAK_TREND:
            adx_signal = "no_trend"
        else:
            adx_signal = "weak_trend"

    # Calculate Stochastic RSI
    stoch_k, stoch_d = calculate_stoch_rsi(df)
    stoch_rsi_signal = "neutral"
    if stoch_k is not None:
        if stoch_k < STOCH_RSI_OVERSOLD:
            stoch_rsi_signal = "oversold"
        elif stoch_k > STOCH_RSI_OVERBOUGHT:
            stoch_rsi_signal = "overbought"
        elif stoch_d is not None and stoch_k > stoch_d and stoch_k < 50:
            stoch_rsi_signal = "bullish_cross"
        elif stoch_d is not None and stoch_k < stoch_d and stoch_k > 50:
            stoch_rsi_signal = "bearish_cross"

    # Detect divergence
    divergence_result = detect_divergence(df, rsi_series)

    # Calculate 52-week high/low (pass ticker to fetch full year data if needed)
    week_52_high, week_52_low = calculate_52_week_high_low(df, ticker)
    pct_from_52w_high = None
    pct_from_52w_low = None
    near_52w_high = False
    near_52w_low = False

    if week_52_high and current_price:
        pct_from_52w_high = ((current_price - week_52_high) / week_52_high) * 100
        near_52w_high = pct_from_52w_high >= -5  # Within 5% of high

    if week_52_low and current_price:
        pct_from_52w_low = ((current_price - week_52_low) / week_52_low) * 100
        near_52w_low = pct_from_52w_low <= 5  # Within 5% of low

    # Build signals object
    signals = TechnicalSignals(
        ticker=ticker,
        current_price=round(current_price, 2),

        # 52-Week High/Low
        week_52_high=round(week_52_high, 2) if week_52_high else None,
        week_52_low=round(week_52_low, 2) if week_52_low else None,
        pct_from_52w_high=round(pct_from_52w_high, 1) if pct_from_52w_high is not None else None,
        pct_from_52w_low=round(pct_from_52w_low, 1) if pct_from_52w_low is not None else None,
        near_52w_high=near_52w_high,
        near_52w_low=near_52w_low,

        # RSI
        rsi=round(rsi, 2) if rsi and not np.isnan(rsi) else None,
        rsi_signal=get_rsi_signal(rsi),

        # MACD
        macd=round(macd, 4) if macd and not np.isnan(macd) else None,
        macd_signal=round(macd_signal, 4) if macd_signal and not np.isnan(macd_signal) else None,
        macd_histogram=round(macd_hist, 4) if macd_hist and not np.isnan(macd_hist) else None,
        macd_trend=get_macd_trend(macd, macd_signal, macd_hist, prev_hist),

        # Moving Averages
        ema_20=round(ema_20_val, 2) if ema_20_val and not np.isnan(ema_20_val) else None,
        ema_50=round(ema_50_val, 2) if ema_50_val and not np.isnan(ema_50_val) else None,
        ema_200=round(ema_200_val, 2) if ema_200_val and not np.isnan(ema_200_val) else None,
        price_vs_ema20=get_price_vs_ma(current_price, ema_20_val),
        price_vs_ema50=get_price_vs_ma(current_price, ema_50_val),
        price_vs_ema200=get_price_vs_ma(current_price, ema_200_val),
        ma_trend=get_ma_trend(ema_20_val, ema_50_val, ema_200_val),

        # Bollinger Bands
        bb_upper=round(bb_upper_val, 2) if bb_upper_val and not np.isnan(bb_upper_val) else None,
        bb_middle=round(bb_middle_val, 2) if bb_middle_val and not np.isnan(bb_middle_val) else None,
        bb_lower=round(bb_lower_val, 2) if bb_lower_val and not np.isnan(bb_lower_val) else None,
        bb_position=get_bb_position(current_price, bb_upper_val, bb_middle_val, bb_lower_val),
        bb_width=round(bb_width, 2) if bb_width else None,

        # ATR
        atr=round(atr, 2) if atr and not np.isnan(atr) else None,
        atr_percent=round(atr_percent, 2) if atr_percent else None,
        volatility_level=get_volatility_level(atr_percent),

        # Volume
        volume=current_volume,
        volume_avg=round(volume_avg, 0) if volume_avg else None,
        volume_ratio=round(volume_ratio, 2) if volume_ratio else None,
        volume_signal=get_volume_signal(volume_ratio),

        # ADX
        adx=round(adx_val, 1) if adx_val is not None else None,
        adx_signal=adx_signal,
        plus_di=round(plus_di_val, 1) if plus_di_val is not None else None,
        minus_di=round(minus_di_val, 1) if minus_di_val is not None else None,

        # Stochastic RSI
        stoch_rsi_k=round(stoch_k, 1) if stoch_k is not None else None,
        stoch_rsi_d=round(stoch_d, 1) if stoch_d is not None else None,
        stoch_rsi_signal=stoch_rsi_signal,

        # Divergence
        divergence=divergence_result.get("type"),
        divergence_strength=divergence_result.get("strength"),
    )

    # Calculate overall score
    score, bias = calculate_technical_score(signals)
    signals.technical_score = score
    signals.technical_bias = bias

    return signals


def get_technical_summary_text(signals: TechnicalSignals) -> str:
    """
    Generate a human-readable technical analysis summary.

    Args:
        signals: TechnicalSignals object

    Returns:
        Formatted string summary
    """
    if signals.current_price == 0:
        return f"{signals.ticker}: Technical data unavailable"

    # 52-week high/low status
    high_low_status = ""
    if signals.near_52w_high:
        high_low_status = " ⭐ NEAR 52W HIGH"
    elif signals.near_52w_low:
        high_low_status = " ⚠️ NEAR 52W LOW"

    lines = [
        f"=== {signals.ticker} Technical Analysis ==={high_low_status}",
        f"Price: ₹{signals.current_price}",
        f"52W High: ₹{signals.week_52_high} ({signals.pct_from_52w_high:+.1f}%)" if signals.week_52_high else "",
        f"52W Low: ₹{signals.week_52_low} ({signals.pct_from_52w_low:+.1f}%)" if signals.week_52_low else "",
        "",
        f"RSI (14): {signals.rsi} ({signals.rsi_signal})",
        f"MACD: {signals.macd_trend}",
        f"MA Trend: {signals.ma_trend}",
        f"  - Price vs 20 EMA: {signals.price_vs_ema20}",
        f"  - Price vs 50 EMA: {signals.price_vs_ema50}",
        f"  - Price vs 200 EMA: {signals.price_vs_ema200}",
        f"Bollinger Position: {signals.bb_position}",
        f"Volatility (ATR%): {signals.atr_percent}% ({signals.volatility_level})",
        f"Volume: {signals.volume_signal} ({signals.volume_ratio}x avg)",
        f"ADX: {signals.adx} ({signals.adx_signal})" if signals.adx else "",
        f"  - +DI: {signals.plus_di}, -DI: {signals.minus_di}" if signals.plus_di else "",
        f"Stochastic RSI: K={signals.stoch_rsi_k}, D={signals.stoch_rsi_d} ({signals.stoch_rsi_signal})" if signals.stoch_rsi_k else "",
        f"Divergence: {signals.divergence} ({signals.divergence_strength})" if signals.divergence else "",
        "",
        f"Technical Score: {signals.technical_score}/100",
        f"Technical Bias: {signals.technical_bias.upper()}",
    ]

    return "\n".join(lines)


def signals_to_dict(signals: TechnicalSignals) -> dict:
    """Convert TechnicalSignals to dictionary for JSON serialization."""
    return {
        "ticker": signals.ticker,
        "current_price": signals.current_price,
        "week_52_high": signals.week_52_high,
        "week_52_low": signals.week_52_low,
        "pct_from_52w_high": signals.pct_from_52w_high,
        "pct_from_52w_low": signals.pct_from_52w_low,
        "near_52w_high": signals.near_52w_high,
        "near_52w_low": signals.near_52w_low,
        "rsi": signals.rsi,
        "rsi_signal": signals.rsi_signal,
        "macd": signals.macd,
        "macd_signal": signals.macd_signal,
        "macd_histogram": signals.macd_histogram,
        "macd_trend": signals.macd_trend,
        "ema_20": signals.ema_20,
        "ema_50": signals.ema_50,
        "ema_200": signals.ema_200,
        "price_vs_ema20": signals.price_vs_ema20,
        "price_vs_ema50": signals.price_vs_ema50,
        "price_vs_ema200": signals.price_vs_ema200,
        "ma_trend": signals.ma_trend,
        "bb_upper": signals.bb_upper,
        "bb_middle": signals.bb_middle,
        "bb_lower": signals.bb_lower,
        "bb_position": signals.bb_position,
        "bb_width": signals.bb_width,
        "atr": signals.atr,
        "atr_percent": signals.atr_percent,
        "volatility_level": signals.volatility_level,
        "volume": signals.volume,
        "volume_avg": signals.volume_avg,
        "volume_ratio": signals.volume_ratio,
        "volume_signal": signals.volume_signal,
        "adx": signals.adx,
        "adx_signal": signals.adx_signal,
        "plus_di": signals.plus_di,
        "minus_di": signals.minus_di,
        "stoch_rsi_k": signals.stoch_rsi_k,
        "stoch_rsi_d": signals.stoch_rsi_d,
        "stoch_rsi_signal": signals.stoch_rsi_signal,
        "divergence": signals.divergence,
        "divergence_strength": signals.divergence_strength,
        "technical_score": signals.technical_score,
        "technical_bias": signals.technical_bias,
    }
