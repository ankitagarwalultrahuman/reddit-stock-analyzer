"""
Shared market analytics utilities for Indian swing-trading workflows.

Provides aligned relative strength, liquidity scoring, and price-structure helpers
used across the screener, swing, and weekly analysis modules.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import pandas as pd

from config import RS_BENCHMARK
from stock_history import fetch_stock_history


def _prepare_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a price frame to Date + Close columns."""
    if df is None or df.empty or "Close" not in df.columns:
        return pd.DataFrame(columns=["Date", "Close"])

    frame = df.copy()
    if "Date" in frame.columns:
        frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
    else:
        frame = frame.reset_index().rename(columns={"index": "Date"})
        frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)

    frame = frame[["Date", "Close"]].dropna().sort_values("Date")
    return frame


def calculate_relative_strength_aligned(
    ticker: str,
    benchmark_ticker: str = RS_BENCHMARK,
    days: int = 20,
    force_refresh: bool = False,
) -> float:
    """
    Calculate relative strength using aligned dates for stock and benchmark.

    `days` is treated as a calendar lookback window anchored to the latest
    common trading date rather than an arbitrary row count.
    """
    try:
        stock_df = fetch_stock_history(ticker, days=days + 25, force_refresh=force_refresh)
        benchmark_df = fetch_stock_history(benchmark_ticker, days=days + 25, force_refresh=force_refresh)

        stock_frame = _prepare_price_frame(stock_df)
        benchmark_frame = _prepare_price_frame(benchmark_df)
        if stock_frame.empty or benchmark_frame.empty:
            return 0.0

        aligned = stock_frame.merge(
            benchmark_frame,
            on="Date",
            how="inner",
            suffixes=("_stock", "_benchmark"),
        )
        if len(aligned) < 5:
            return 0.0

        end_row = aligned.iloc[-1]
        target_date = end_row["Date"] - timedelta(days=days)
        history = aligned[aligned["Date"] <= target_date]
        start_row = history.iloc[-1] if not history.empty else aligned.iloc[0]

        stock_start = float(start_row["Close_stock"])
        stock_end = float(end_row["Close_stock"])
        bench_start = float(start_row["Close_benchmark"])
        bench_end = float(end_row["Close_benchmark"])

        if min(stock_start, bench_start) <= 0:
            return 0.0

        stock_return = ((stock_end / stock_start) - 1) * 100
        benchmark_return = ((bench_end / bench_start) - 1) * 100
        return round(stock_return - benchmark_return, 2)
    except Exception:
        return 0.0


def calculate_average_traded_value(df: pd.DataFrame, period: int = 20) -> Optional[float]:
    """Average traded value over the recent period in INR."""
    if df is None or df.empty or "Close" not in df.columns or "Volume" not in df.columns:
        return None

    recent = df.tail(period).copy()
    if recent.empty:
        return None

    traded_value = recent["Close"] * recent["Volume"]
    avg_value = traded_value.mean()
    return float(avg_value) if pd.notna(avg_value) else None


def liquidity_tier_from_adv(avg_traded_value: Optional[float]) -> str:
    """Classify liquidity using average traded value in INR."""
    if avg_traded_value is None:
        return "unknown"
    if avg_traded_value >= 100_00_00_000:  # 100 Cr
        return "institutional"
    if avg_traded_value >= 25_00_00_000:  # 25 Cr
        return "liquid"
    if avg_traded_value >= 5_00_00_000:   # 5 Cr
        return "tradable"
    return "illiquid"


def average_traded_value_cr(avg_traded_value: Optional[float]) -> Optional[float]:
    """Convert INR traded value to crore INR."""
    if avg_traded_value is None:
        return None
    return round(avg_traded_value / 1e7, 2)


def calculate_relative_volume(df: pd.DataFrame, recent_period: int = 5, base_period: int = 20) -> float:
    """Relative volume using recent average volume vs trailing base average."""
    if df is None or df.empty or "Volume" not in df.columns or len(df) < base_period:
        return 1.0

    recent_avg = float(df["Volume"].tail(recent_period).mean())
    base_avg = float(df["Volume"].tail(base_period).mean())
    if base_avg <= 0:
        return 1.0
    return round(recent_avg / base_avg, 2)


def cluster_levels(levels: list[float], threshold_pct: float = 1.5) -> list[tuple[float, int]]:
    """Cluster nearby price levels and count touches."""
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters: list[list[float]] = [[sorted_levels[0]]]

    for level in sorted_levels[1:]:
        anchor = clusters[-1][0]
        if anchor > 0 and abs(level - anchor) / anchor * 100 < threshold_pct:
            clusters[-1].append(level)
        else:
            clusters.append([level])

    reduced = []
    for cluster in clusters:
        reduced.append((round(sum(cluster) / len(cluster), 2), len(cluster)))

    reduced.sort(key=lambda item: item[1], reverse=True)
    return reduced


def find_support_resistance_levels(
    df: pd.DataFrame,
    lookback: int = 30,
    threshold_pct: float = 1.5,
) -> tuple[list[float], list[float]]:
    """
    Find clustered support and resistance levels from pivot highs/lows.

    Returns up to three support levels and three resistance levels.
    """
    if df is None or df.empty or len(df) < max(lookback, 10):
        return ([], [])

    recent = df.tail(lookback)
    current_price = float(recent["Close"].iloc[-1])
    highs = recent["High"].values
    lows = recent["Low"].values

    raw_supports: list[float] = []
    raw_resistances: list[float] = []

    for window in [2, 3, 4]:
        for idx in range(window, len(recent) - window):
            local_high = all(highs[idx] >= highs[idx - j] for j in range(1, window + 1)) and all(
                highs[idx] >= highs[idx + j] for j in range(1, window + 1)
            )
            if local_high:
                raw_resistances.append(float(highs[idx]))

            local_low = all(lows[idx] <= lows[idx - j] for j in range(1, window + 1)) and all(
                lows[idx] <= lows[idx + j] for j in range(1, window + 1)
            )
            if local_low:
                raw_supports.append(float(lows[idx]))

    support_clusters = cluster_levels(raw_supports, threshold_pct=threshold_pct)
    resistance_clusters = cluster_levels(raw_resistances, threshold_pct=threshold_pct)

    supports = sorted([level for level, _ in support_clusters if level < current_price])[-3:]
    resistances = sorted([level for level, _ in resistance_clusters if level > current_price])[:3]

    if not supports:
        supports = [round(float(recent["Low"].min()), 2)]
    if not resistances:
        resistances = [round(float(recent["High"].max()), 2)]

    return supports, resistances


def nearest_support_resistance(
    current_price: float,
    supports: list[float],
    resistances: list[float],
) -> tuple[float, float]:
    """Return the nearest support below and resistance above the current price."""
    nearest_support = max([s for s in supports if s < current_price], default=(supports[-1] if supports else 0))
    nearest_resistance = min([r for r in resistances if r > current_price], default=(resistances[0] if resistances else 0))
    return round(float(nearest_support), 2) if nearest_support else 0.0, round(float(nearest_resistance), 2) if nearest_resistance else 0.0


def position_allocation_pct(
    entry_price: float,
    stop_loss: float,
    risk_budget_pct: float = 1.0,
    max_allocation_pct: float = 25.0,
) -> float:
    """
    Generic position-allocation helper.

    Returns the maximum position size as a % of portfolio if the trader risks
    `risk_budget_pct` of capital and uses the provided stop-loss distance.
    """
    if entry_price <= 0 or stop_loss <= 0:
        return 0.0

    stop_distance_pct = abs(entry_price - stop_loss) / entry_price * 100
    if stop_distance_pct <= 0:
        return 0.0

    allocation = (risk_budget_pct / stop_distance_pct) * 100
    return round(min(allocation, max_allocation_pct), 1)
