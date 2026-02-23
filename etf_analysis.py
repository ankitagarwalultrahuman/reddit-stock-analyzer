"""
Sector ETF Analysis Module - Multi-timeframe performance and relative strength
analysis for popular Indian NSE sector ETFs.

Reuses stock_history, sector_tracker, and technical_analysis for all heavy lifting.
"""

import concurrent.futures
from dataclasses import dataclass, asdict
from typing import Optional

from stock_history import fetch_stock_history
from sector_tracker import _get_return_for_period
from technical_analysis import get_technical_analysis


# ETF universe — ticker: (display name, category)
ETF_UNIVERSE = {
    "NIFTYBEES": ("Nifty 50 ETF", "Broad Market"),
    "JUNIORBEES": ("Nifty Next 50 ETF", "Broad Market"),
    "BANKBEES": ("Bank ETF", "Banking"),
    "PSUBNKBEES": ("PSU Bank ETF", "Banking"),
    "ITBEES": ("IT ETF", "Technology"),
    "PHARMABEES": ("Pharma ETF", "Healthcare"),
    "OILGASBEES": ("Energy ETF", "Energy"),
    "INFRABEES": ("Infra ETF", "Infrastructure"),
    "CPSE": ("CPSE ETF", "PSU/Govt"),
    "CONSUMPTION": ("Consumption ETF", "Consumer"),
    "MOM100": ("Momentum 100 ETF", "Factor"),
    "GOLDBEES": ("Gold ETF", "Commodity"),
    "SILVERBEES": ("Silver ETF", "Commodity"),
}


@dataclass
class ETFMetrics:
    ticker: str
    name: str
    category: str
    current_price: float = 0.0

    # Multi-timeframe returns
    return_1w: float = 0.0
    return_1m: float = 0.0
    return_3m: float = 0.0
    return_6m: float = 0.0

    # Relative strength vs NIFTY (ETF return - benchmark return)
    rs_1w: float = 0.0
    rs_1m: float = 0.0
    rs_3m: float = 0.0
    rs_6m: float = 0.0

    # Technical indicators
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None
    macd_trend: Optional[str] = None
    ma_trend: Optional[str] = None
    price_vs_ema20: Optional[str] = None
    price_vs_ema50: Optional[str] = None
    price_vs_ema200: Optional[str] = None
    volume_signal: Optional[str] = None
    adx: Optional[float] = None

    # 52-week
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    pct_from_52w_high: Optional[float] = None
    pct_from_52w_low: Optional[float] = None

    # Derived
    atr_percent: Optional[float] = None
    volatility_level: Optional[str] = None
    momentum_score: float = 0.0
    technical_score: Optional[int] = None
    technical_bias: Optional[str] = None
    rank: int = 0


def _compute_benchmark_returns() -> dict:
    """Fetch ^NSEI (Nifty 50 index) and compute returns at standard timeframes."""
    df = fetch_stock_history("NIFTY", days=250)
    if df.empty:
        return {"1w": 0.0, "1m": 0.0, "3m": 0.0, "6m": 0.0}
    return {
        "1w": _get_return_for_period(df, 7),
        "1m": _get_return_for_period(df, 30),
        "3m": _get_return_for_period(df, 90),
        "6m": _get_return_for_period(df, 180),
    }


def analyze_single_etf(ticker: str, benchmark_returns: dict) -> Optional[ETFMetrics]:
    """Analyze a single ETF: returns, relative strength, technicals."""
    name, category = ETF_UNIVERSE.get(ticker, (ticker, "Unknown"))
    try:
        df = fetch_stock_history(ticker, days=250)
        if df.empty or len(df) < 20:
            return None

        current_price = float(df["Close"].iloc[-1])

        # Returns
        ret_1w = _get_return_for_period(df, 7)
        ret_1m = _get_return_for_period(df, 30)
        ret_3m = _get_return_for_period(df, 90)
        ret_6m = _get_return_for_period(df, 180)

        # Relative strength
        rs_1w = ret_1w - benchmark_returns.get("1w", 0)
        rs_1m = ret_1m - benchmark_returns.get("1m", 0)
        rs_3m = ret_3m - benchmark_returns.get("3m", 0)
        rs_6m = ret_6m - benchmark_returns.get("6m", 0)

        # Technical analysis (reuse existing module)
        signals = get_technical_analysis(df, ticker)

        # Momentum score composite (0-100)
        score = 50.0

        # Return contribution (weighted: recent matters more)
        score += min(max(ret_1w * 2.0, -10), 10)
        score += min(max(ret_1m * 1.0, -10), 10)
        score += min(max(ret_3m * 0.3, -5), 5)

        # RS contribution (outperforming NIFTY is positive)
        score += min(max(rs_1m * 1.5, -8), 8)

        # RSI contribution
        rsi = signals.rsi
        if rsi is not None:
            if rsi > 60:
                score += 5
            elif rsi < 40:
                score -= 5

        # MA trend contribution
        if signals.ma_trend == "bullish":
            score += 7
        elif signals.ma_trend == "bearish":
            score -= 7

        # Timeframe alignment bonus
        if ret_1w > 0 and ret_1m > 0 and ret_3m > 0:
            score += 5
        elif ret_1w < 0 and ret_1m < 0 and ret_3m < 0:
            score -= 5

        score = max(0.0, min(100.0, score))

        return ETFMetrics(
            ticker=ticker,
            name=name,
            category=category,
            current_price=round(current_price, 2),
            return_1w=round(ret_1w, 2),
            return_1m=round(ret_1m, 2),
            return_3m=round(ret_3m, 2),
            return_6m=round(ret_6m, 2),
            rs_1w=round(rs_1w, 2),
            rs_1m=round(rs_1m, 2),
            rs_3m=round(rs_3m, 2),
            rs_6m=round(rs_6m, 2),
            rsi=round(rsi, 1) if rsi is not None else None,
            rsi_signal=signals.rsi_signal,
            macd_trend=signals.macd_trend,
            ma_trend=signals.ma_trend,
            price_vs_ema20=signals.price_vs_ema20,
            price_vs_ema50=signals.price_vs_ema50,
            price_vs_ema200=signals.price_vs_ema200,
            volume_signal=signals.volume_signal,
            adx=round(signals.adx, 1) if signals.adx is not None else None,
            week_52_high=signals.week_52_high,
            week_52_low=signals.week_52_low,
            pct_from_52w_high=signals.pct_from_52w_high,
            pct_from_52w_low=signals.pct_from_52w_low,
            atr_percent=signals.atr_percent,
            volatility_level=signals.volatility_level,
            momentum_score=round(score, 1),
            technical_score=signals.technical_score,
            technical_bias=signals.technical_bias,
        )
    except Exception as e:
        print(f"[ETF] {ticker}: Error - {e}")
        return None


def analyze_all_etfs(max_workers: int = 5) -> list[ETFMetrics]:
    """Analyze all ETFs in universe. Returns list sorted by momentum_score descending."""
    print("[ETF] Computing benchmark returns...")
    benchmark = _compute_benchmark_returns()
    print(f"[ETF] Benchmark (NIFTY): 1W={benchmark['1w']:.2f}%, 1M={benchmark['1m']:.2f}%")

    results: list[ETFMetrics] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_single_etf, ticker, benchmark): ticker
            for ticker in ETF_UNIVERSE
        }
        for future in concurrent.futures.as_completed(futures):
            ticker = futures[future]
            try:
                m = future.result(timeout=60)
                if m:
                    results.append(m)
                    print(f"[ETF] {ticker}: momentum={m.momentum_score}, RS_1M={m.rs_1m:+.2f}%")
            except Exception as e:
                print(f"[ETF] {ticker}: Future failed - {e}")

    results.sort(key=lambda x: x.momentum_score, reverse=True)
    for i, m in enumerate(results, 1):
        m.rank = i

    return results


def get_etf_summary(metrics: list[ETFMetrics]) -> dict:
    """Generate summary insights from ETF analysis results."""
    if not metrics:
        return {"error": "No ETF data available"}

    sorted_by_momentum = sorted(metrics, key=lambda x: x.momentum_score, reverse=True)
    top3 = sorted_by_momentum[:3]
    bottom3 = sorted_by_momentum[-3:]

    outperforming = [m for m in metrics if m.rs_1m > 0]
    oversold = [m for m in metrics if m.rsi is not None and m.rsi < 40]
    near_52w_high = [m for m in metrics if m.pct_from_52w_high is not None and m.pct_from_52w_high >= -5]
    near_52w_low = [m for m in metrics if m.pct_from_52w_low is not None and m.pct_from_52w_low <= 5]

    avg_momentum = sum(m.momentum_score for m in metrics) / len(metrics) if metrics else 0

    # Category rankings
    categories: dict[str, list[ETFMetrics]] = {}
    for m in metrics:
        categories.setdefault(m.category, []).append(m)
    category_best = {
        cat: max(etfs, key=lambda x: x.momentum_score).ticker
        for cat, etfs in categories.items()
    }

    # Recommendations
    recommendations = []
    if top3:
        recommendations.append(
            f"STRONGEST: {top3[0].ticker} ({top3[0].name}) leads with momentum {top3[0].momentum_score:.0f} "
            f"and 1M return of {top3[0].return_1m:+.1f}%"
        )
    if outperforming:
        tickers = ", ".join(m.ticker for m in outperforming[:5])
        recommendations.append(
            f"OUTPERFORMING NIFTY (1M): {tickers} ({len(outperforming)}/{len(metrics)} ETFs)"
        )
    if oversold:
        tickers = ", ".join(f"{m.ticker} (RSI {m.rsi:.0f})" for m in oversold)
        recommendations.append(f"OVERSOLD (potential bounce): {tickers}")
    if near_52w_low:
        tickers = ", ".join(m.ticker for m in near_52w_low)
        recommendations.append(f"NEAR 52W LOW (value opportunity): {tickers}")
    if near_52w_high:
        tickers = ", ".join(m.ticker for m in near_52w_high)
        recommendations.append(f"NEAR 52W HIGH (breakout watch): {tickers}")
    if bottom3:
        recommendations.append(
            f"WEAKEST: {bottom3[-1].ticker} ({bottom3[-1].name}) with momentum {bottom3[-1].momentum_score:.0f} "
            f"and 1M return of {bottom3[-1].return_1m:+.1f}%"
        )

    return {
        "top_momentum": [(m.ticker, m.name, m.momentum_score) for m in top3],
        "bottom_momentum": [(m.ticker, m.name, m.momentum_score) for m in bottom3],
        "outperforming_nifty_count": len(outperforming),
        "oversold_count": len(oversold),
        "near_52w_high_count": len(near_52w_high),
        "near_52w_low_count": len(near_52w_low),
        "avg_momentum": round(avg_momentum, 1),
        "category_best": category_best,
        "recommendations": recommendations,
        "total_etfs": len(metrics),
    }
