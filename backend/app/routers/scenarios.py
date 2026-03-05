"""Scenario router - live market snapshot for the geopolitical dashboard."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import APIRouter

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - handled at runtime
    yf = None

from stock_history import get_nse_symbol

router = APIRouter()

CACHE_TTL_SECONDS = 300
_quote_cache: dict[str, dict[str, Any]] = {}
_cache_lock = Lock()

QUOTE_GROUPS = {
    "india_market": [
        {
            "id": "nifty50",
            "name": "NIFTY 50",
            "symbol": "^NSEI",
            "symbol_type": "raw",
            "market": "India",
            "category": "Index",
            "unit": "pts",
            "currency": "INR",
        },
        {
            "id": "banknifty",
            "name": "Bank Nifty",
            "symbol": "^NSEBANK",
            "symbol_type": "raw",
            "market": "India",
            "category": "Index",
            "unit": "pts",
            "currency": "INR",
        },
        {
            "id": "sensex",
            "name": "Sensex",
            "symbol": "^BSESN",
            "symbol_type": "raw",
            "market": "India",
            "category": "Index",
            "unit": "pts",
            "currency": "INR",
        },
        {
            "id": "indiavix",
            "name": "India VIX",
            "symbol": "^INDIAVIX",
            "symbol_type": "raw",
            "market": "India",
            "category": "Volatility",
            "unit": "",
            "currency": "",
        },
        {
            "id": "usdinr",
            "name": "USD/INR",
            "symbol": "INR=X",
            "symbol_type": "raw",
            "market": "FX",
            "category": "FX",
            "unit": "",
            "currency": "INR",
        },
        {
            "id": "brent",
            "name": "Brent",
            "symbol": "BZ=F",
            "symbol_type": "raw",
            "market": "Global",
            "category": "Commodity",
            "unit": "/bbl",
            "currency": "USD",
        },
        {
            "id": "gold",
            "name": "Gold",
            "symbol": "GC=F",
            "symbol_type": "raw",
            "market": "Global",
            "category": "Commodity",
            "unit": "/oz",
            "currency": "USD",
        },
    ],
    "global_risk": [
        {
            "id": "vix",
            "name": "US VIX",
            "symbol": "^VIX",
            "symbol_type": "raw",
            "market": "US",
            "category": "Volatility",
            "unit": "",
            "currency": "",
        },
        {
            "id": "spx",
            "name": "S&P 500",
            "symbol": "^GSPC",
            "symbol_type": "raw",
            "market": "US",
            "category": "Index",
            "unit": "pts",
            "currency": "USD",
        },
        {
            "id": "wti",
            "name": "WTI",
            "symbol": "CL=F",
            "symbol_type": "raw",
            "market": "Global",
            "category": "Commodity",
            "unit": "/bbl",
            "currency": "USD",
        },
    ],
    "india_equities": [
        {
            "id": "reliance",
            "name": "Reliance",
            "symbol": "RELIANCE",
            "symbol_type": "nse",
            "market": "India",
            "category": "Energy",
        },
        {
            "id": "ongc",
            "name": "ONGC",
            "symbol": "ONGC",
            "symbol_type": "nse",
            "market": "India",
            "category": "Upstream energy",
        },
        {
            "id": "oil",
            "name": "Oil India",
            "symbol": "OIL",
            "symbol_type": "nse",
            "market": "India",
            "category": "Upstream energy",
        },
        {
            "id": "iocl",
            "name": "IOC",
            "symbol": "IOC",
            "symbol_type": "nse",
            "market": "India",
            "category": "OMC",
        },
        {
            "id": "bpcl",
            "name": "BPCL",
            "symbol": "BPCL",
            "symbol_type": "nse",
            "market": "India",
            "category": "OMC",
        },
        {
            "id": "hal",
            "name": "HAL",
            "symbol": "HAL",
            "symbol_type": "nse",
            "market": "India",
            "category": "Defense",
        },
        {
            "id": "bel",
            "name": "BEL",
            "symbol": "BEL",
            "symbol_type": "nse",
            "market": "India",
            "category": "Defense",
        },
        {
            "id": "mazdock",
            "name": "Mazagon Dock",
            "symbol": "MAZAGON",
            "symbol_type": "nse",
            "market": "India",
            "category": "Defense",
        },
        {
            "id": "indigo",
            "name": "IndiGo",
            "symbol": "INDIGO",
            "symbol_type": "nse",
            "market": "India",
            "category": "Airlines",
        },
        {
            "id": "asianpaint",
            "name": "Asian Paints",
            "symbol": "ASIANPAINT",
            "symbol_type": "nse",
            "market": "India",
            "category": "Crude derivative",
        },
        {
            "id": "hdfcbank",
            "name": "HDFC Bank",
            "symbol": "HDFCBANK",
            "symbol_type": "nse",
            "market": "India",
            "category": "Financials",
        },
        {
            "id": "tcs",
            "name": "TCS",
            "symbol": "TCS",
            "symbol_type": "nse",
            "market": "India",
            "category": "IT exporters",
        },
        {
            "id": "itc",
            "name": "ITC",
            "symbol": "ITC",
            "symbol_type": "nse",
            "market": "India",
            "category": "Consumer staples",
        },
        {
            "id": "sci",
            "name": "Shipping Corp",
            "symbol": "SCI",
            "symbol_type": "nse",
            "market": "India",
            "category": "Shipping and logistics",
        },
        {
            "id": "ntpc",
            "name": "NTPC",
            "symbol": "NTPC",
            "symbol_type": "nse",
            "market": "India",
            "category": "Utilities and power",
        },
        {
            "id": "maruti",
            "name": "Maruti",
            "symbol": "MARUTI",
            "symbol_type": "nse",
            "market": "India",
            "category": "Consumer discretionary",
        },
    ],
}


def _resolve_symbol(entry: dict[str, Any]) -> str:
    if entry["symbol_type"] == "nse":
        return get_nse_symbol(entry["symbol"])
    return entry["symbol"]


def _history_quote(symbol: str) -> tuple[float | None, float | None]:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")
    if hist.empty:
        return None, None
    last = float(hist["Close"].iloc[-1])
    previous = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
    return last, previous


def _fetch_quote(entry: dict[str, Any]) -> dict[str, Any]:
    resolved_symbol = _resolve_symbol(entry)

    if yf is None:
        return {
            **entry,
            "resolved_symbol": resolved_symbol,
            "success": False,
            "error": "yfinance not installed",
        }

    now_ts = datetime.now(timezone.utc).timestamp()
    with _cache_lock:
        cached = _quote_cache.get(resolved_symbol)
        if cached and now_ts - cached["fetched_ts"] < CACHE_TTL_SECONDS:
            return cached["payload"]

    payload: dict[str, Any] = {
        **entry,
        "resolved_symbol": resolved_symbol,
        "success": False,
        "last": None,
        "previous_close": None,
        "change_percent": None,
        "currency": entry.get("currency", ""),
        "unit": entry.get("unit", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        ticker = yf.Ticker(resolved_symbol)

        last_price = None
        previous_close = None

        try:
            fast_info = ticker.fast_info
            last_price = getattr(fast_info, "last_price", None) or fast_info.get("lastPrice")
            previous_close = getattr(fast_info, "previous_close", None) or fast_info.get("previousClose")
        except Exception:
            pass

        if last_price is None or previous_close is None:
            try:
                info = ticker.info
                last_price = last_price or info.get("currentPrice") or info.get("regularMarketPrice")
                previous_close = previous_close or info.get("previousClose") or info.get("regularMarketPreviousClose")
            except Exception:
                pass

        if last_price is None or previous_close is None:
            last_price, previous_close = _history_quote(resolved_symbol)

        if last_price is None:
            payload["error"] = "No quote data returned"
        else:
            change_percent = None
            if previous_close not in (None, 0):
                change_percent = ((float(last_price) - float(previous_close)) / float(previous_close)) * 100
            payload.update(
                {
                    "success": True,
                    "last": round(float(last_price), 2),
                    "previous_close": round(float(previous_close), 2) if previous_close is not None else None,
                    "change_percent": round(change_percent, 2) if change_percent is not None else None,
                }
            )
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        payload["error"] = str(exc)

    with _cache_lock:
        _quote_cache[resolved_symbol] = {
            "fetched_ts": now_ts,
            "payload": payload,
        }

    return payload


def _derive_watchpoints(sections: dict[str, list[dict[str, Any]]]) -> list[str]:
    by_id = {
        quote["id"]: quote
        for quotes in sections.values()
        for quote in quotes
        if quote.get("success")
    }
    notes: list[str] = []

    brent = by_id.get("brent", {}).get("last")
    usdinr = by_id.get("usdinr", {}).get("last")
    indiavix = by_id.get("indiavix", {}).get("last")
    nifty = by_id.get("nifty50", {}).get("change_percent")
    ongc = by_id.get("ongc", {}).get("change_percent")
    indigo = by_id.get("indigo", {}).get("change_percent")

    if brent and brent >= 95:
        notes.append("Brent above $95 keeps pressure on Indian importers, OMC margins, and inflation expectations.")
    if usdinr and usdinr >= 84:
        notes.append("USD/INR above 84 adds a second stress channel for India through imported energy and tighter liquidity.")
    if indiavix and indiavix >= 16:
        notes.append("India VIX above 16 usually marks a regime where stock-specific narratives matter less than macro hedging.")
    if (
        nifty is not None
        and ongc is not None
        and indigo is not None
        and ongc > nifty
        and indigo < nifty
    ):
        notes.append("Energy outperforming NIFTY while airlines lag is the cleanest India-specific confirmation of the oil shock path.")

    if not notes:
        notes.append("Use Brent, USD/INR, India VIX, and the RELIANCE-ONGC-INDIGO relative tape as the main confirmation cluster.")

    return notes


@router.get("/live-market")
async def live_market_snapshot():
    tasks = [
        (group_name, entry)
        for group_name, entries in QUOTE_GROUPS.items()
        for entry in entries
    ]

    sections: dict[str, list[dict[str, Any]]] = {key: [] for key in QUOTE_GROUPS}
    with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as executor:
        futures = [
            (group_name, executor.submit(_fetch_quote, entry))
            for group_name, entry in tasks
        ]
        for group_name, future in futures:
            sections[group_name].append(future.result())

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "sections": sections,
        "watchpoints": _derive_watchpoints(sections),
    }
