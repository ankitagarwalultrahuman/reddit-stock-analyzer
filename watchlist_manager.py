"""
Watchlist Manager - Manages stock watchlists for scanning.

Provides:
- Built-in presets (NIFTY50, NIFTY100, Sector-wise)
- Custom user watchlists
- JSON-based persistence
"""

import csv
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from io import StringIO

import requests

# Watchlist storage file
WATCHLIST_FILE = "watchlists.json"
UNIVERSE_CACHE_FILE = "universe_cache.json"
UNIVERSE_CACHE_TTL_HOURS = 24

# =============================================================================
# NIFTY 50 STOCKS (as of 2024)
# =============================================================================
NIFTY50_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL",
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
    "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN",
    "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]

# Mapping for tickers with special characters (yfinance format)
TICKER_YFINANCE_MAP = {
    "BAJAJ-AUTO": "BAJAJ-AUTO",
    "M&M": "M&M",
}

# =============================================================================
# NIFTY NEXT 50 STOCKS (NIFTY100 = NIFTY50 + NIFTY NEXT 50)
# =============================================================================
NIFTY_NEXT50_STOCKS = [
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "ATGL",
    "AUROPHARMA", "BAJAJHLDNG", "BANKBARODA", "BERGEPAINT", "BOSCHLTD",
    "CANBK", "CHOLAFIN", "COLPAL", "DABUR", "DLF",
    "GAIL", "GODREJCP", "HAVELLS", "ICICIPRULI", "IDEA",
    "IDFCFIRSTB", "INDHOTEL", "INDIGO", "IOC", "IRCTC",
    "JINDALSTEL", "JSWENERGY", "LICI", "LODHA", "LUPIN",
    "MARICO", "MOTHERSON", "NAUKRI", "NHPC", "NMDC",
    "OBEROIRLTY", "OFSS", "PAGEIND", "PAYTM", "PFC",
    "PIDILITIND", "PNB", "POLYCAB", "RECLTD", "SBICARD",
    "SIEMENS", "TATAPOWER", "TORNTPHARM", "TVSMOTOR", "ZOMATO",
]

NIFTY100_STOCKS = NIFTY50_STOCKS + NIFTY_NEXT50_STOCKS

# =============================================================================
# NIFTY MIDCAP 100 STOCKS (prime swing trading territory)
# =============================================================================
NIFTY_MIDCAP100_STOCKS = [
    # Financial Services
    "CRISIL", "MUTHOOTFIN", "MANAPPURAM", "IIFL", "LICHSGFIN",
    "POONAWALLA", "CANFINHOME", "LTFH", "CREDITACC", "UJJIVANSFB",
    # IT & Tech
    "PERSISTENT", "COFORGE", "LTTS", "TATAELXSI", "CYIENT",
    "INTELLECT", "MPHASIS", "MINDTREE", "SONATSOFTW", "BSOFT",
    # Consumer & Retail
    "TRENT", "DMART", "DEVYANI", "JUBLFOOD", "RAJESHEXPO",
    "FINEORG", "ZOMATO", "NYKAA", "MEDANTA", "AFFLE",
    # Pharma & Healthcare
    "ZYDUSLIFE", "ALKEM", "IPCALAB", "LAURUSLABS", "GLENMARK",
    "GRANULES", "MAXHEALTH", "FORTIS", "LALPATHLAB", "METROPOLIS",
    # Industrial & Manufacturing
    "CUMMINSIND", "THERMAX", "AIAENG", "GRINDWELL", "SCHAEFFLER",
    "TIMKEN", "SKFINDIA", "KAJARIACER", "SUPREMEIND", "ASTRAL",
    # Chemicals
    "PIIND", "ATUL", "DEEPAKNTR", "NAVINFLUOR", "CLEAN",
    "FLUOROCHEM", "AARTI", "SRF", "TATACHEM", "UPL",
    # Auto & Ancillaries
    "SONACOMS", "ENDURANCE", "SUNDRMFAST", "SUPRAJIT", "MINDA",
    "CRAFTSMAN", "FIEM", "LUMAXTECH", "HAPPSTMNDS", "BIKAJI",
    # Real Estate & Construction
    "BRIGADE", "SOBHA", "SUNTECK", "MAHLIFE", "PRESTIGE",
    "PHOENIXLTD", "GODREJPROP", "OBEROIRLTY", "KOLTEPATIL", "RUSTOMJEE",
    # Utilities & Energy
    "SJVN", "TORNTPOWER", "CESC", "TATAPOWER", "JPPOWER",
    "NHPC", "JSL", "INOXWIND", "SUZLON", "ADANIENSOL",
    # Others
    "VOLTAS", "BLUESTARCO", "CROMPTON", "ORIENTELEC", "VGUARD",
    "RELAXO", "BATA", "CAMPUS", "METROBRAND", "KPRMILL",
]

# =============================================================================
# NIFTY SMALLCAP 100 STOCKS (high volatility, high opportunity)
# =============================================================================
NIFTY_SMALLCAP100_STOCKS = [
    # Financial Services
    "RBLBANK", "EQUITASBNK", "SURYODAY", "UJJIVAN", "DCBBANK",
    "CSBBANK", "KTKBANK", "SOUTHBANK", "TMB", "EDELWEISS",
    # IT & Tech
    "HAPPSTMNDS", "TANLA", "ROUTE", "MASTEK", "DATAPATTNS",
    "NETWEB", "NELCO", "ZENTEC", "KSOLVES",
    # Pharma & Healthcare
    "MEDPLUS", "VIJAYA", "PPLPHARMA", "MANKIND", "ERIS",
    "JBCHEPHARM", "MARKSANS", "BLISSGVS", "NATCOPHARM", "SOLARA",
    # Auto & Components
    "CRAFTSMAN", "SWARAJENG", "JAMNAUTO", "GABRIEL", "MUNJALSHOW",
    "LUMAXIND", "JTEKTINDIA", "GNA", "RAMKRISHNA", "SETCO",
    # Chemicals
    "GALAXYSURF", "ORIENTBELL", "ANURAS", "JUBILANTFOOD", "VINYLINDIA",
    "ROSSARI", "NOCIL", "IGPL", "PCBL", "RPSGVENT",
    # Consumer & Retail
    "VBL", "RADICO", "GLOBUSSPR", "ZENSARTECH", "HGINFRA",
    "RKFORGE", "JKTYRE", "TVSSRICHAK", "BALKRISIND", "MRF",
    # Industrial
    "ELGIEQUIP", "ISGEC", "PRAJIND", "REDINGTON", "RITES",
    "RAILTEL", "IRCON", "RVNL", "NBCC", "ENGINERSIN",
    # Real Estate
    "ASHIANA", "AHLUCONT", "SHRIRAMCIT", "KAPSTON", "MAGADSUGAR",
    "AARTIDRUGS", "SHILPAMED", "RAJRATAN", "ROLEXRINGS", "KPITTECH",
    # Textiles & Apparel
    "RAYMOND", "ARVIND", "TRIDENT", "WELSPUNIND", "SIYARAM",
    "GOKEX", "PAGEIND", "DOLLAR", "RUPA", "LUXIND",
    # Others
    "ROUTE", "SOLARINDS", "GPIL", "SARDAEN", "JINDALSAW",
    "SHYAMMETL", "UNIPARTS", "HONAUT", "CERA", "HINDWAREAP",
]

# Combined Midcap + Smallcap for broad swing trading universe
NIFTY_MIDSMALL_STOCKS = NIFTY_MIDCAP100_STOCKS + NIFTY_SMALLCAP100_STOCKS

# =============================================================================
# SECTOR-WISE STOCKS
# =============================================================================
SECTOR_STOCKS = {
    "Banking": [
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
        "INDUSINDBK", "BANKBARODA", "PNB", "CANBK", "IDFCFIRSTB",
        "FEDERALBNK", "BANDHANBNK", "AUBANK", "RBLBANK", "IDBI",
    ],
    "IT": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
        "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "OFSS",
        "NAUKRI", "ROUTE", "TATAELXSI", "LTTS", "CYIENT",
    ],
    "Pharma": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
        "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "BIOCON", "ALKEM",
        "IPCALAB", "LAURUSLABS", "GLENMARK", "GRANULES", "ABBOTINDIA",
    ],
    "Auto": [
        "TATAMOTORS", "M&M", "MARUTI", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "BHARATFORG", "MOTHERSON",
        "BALKRISIND", "MRF", "APOLLOTYRE", "EXIDEIND", "BOSCHLTD",
    ],
    "FMCG": [
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM",
        "GODREJCP", "DABUR", "MARICO", "COLPAL", "VBL",
        "EMAMILTD", "RADICO", "UBL", "PGHH", "JYOTHYLAB",
    ],
    "Energy": [
        "RELIANCE", "ONGC", "BPCL", "IOC", "GAIL",
        "COALINDIA", "NTPC", "POWERGRID", "ADANIGREEN", "TATAPOWER",
        "ADANIPOWER", "NHPC", "PETRONET", "IGL", "MGL",
    ],
    "Metals": [
        "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "COALINDIA",
        "NMDC", "JINDALSTEL", "SAIL", "NATIONALUM", "HINDZINC",
        "APLAPOLLO", "RATNAMANI", "WELCORP", "JSWENERGY", "MOIL",
    ],
    "Realty": [
        "DLF", "GODREJPROP", "OBEROIRLTY", "LODHA", "PRESTIGE",
        "PHOENIXLTD", "BRIGADE", "SOBHA", "SUNTECK", "MAHLIFE",
    ],
    "Finance_NBFC": [
        "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIPRULI",
        "CHOLAFIN", "SHRIRAMFIN", "M&MFIN", "POONAWALLA", "LICHSGFIN",
        "MUTHOOTFIN", "MANAPPURAM", "IIFL", "SBICARD", "PFC", "RECLTD",
    ],
    "Infrastructure": [
        "LT", "ADANIPORTS", "ULTRACEMCO", "GRASIM", "AMBUJACEM",
        "ACC", "SHREECEM", "RAMCOCEM", "DALBHARAT", "JKCEMENT",
        "IRB", "KNRCON", "NCC", "NBCC", "ENGINERSIN",
    ],
    "Telecom": [
        "BHARTIARTL", "IDEA", "TATACOMM", "ROUTE", "STLTECH",
    ],
    "Consumer_Durables": [
        "TITAN", "HAVELLS", "VOLTAS", "BLUESTARCO", "CROMPTON",
        "WHIRLPOOL", "BATAINDIA", "RELAXO", "VGUARD", "ORIENTELEC",
    ],
    "Defence_PSU": [
        "HAL", "BEL", "BHEL", "MAZDOCK", "COCHINSHIP",
        "BDL", "GRSE", "IRFC", "RVNL", "IRCON",
    ],
}

# All sectors list
ALL_SECTORS = list(SECTOR_STOCKS.keys())

LIVE_UNIVERSE_DEFS = {
    "NIFTY50": {
        "label": "NIFTY 50",
        "description": "NIFTY 50 Index constituents",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_nifty50list.csv"],
    },
    "NIFTY_NEXT50": {
        "label": "NIFTY Next 50",
        "description": "NIFTY Next 50 Index constituents",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_niftynext50list.csv"],
    },
    "NIFTY100": {
        "label": "NIFTY 100",
        "description": "NIFTY 100 Index constituents",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_nifty100list.csv"],
    },
    "NIFTY200": {
        "label": "NIFTY 200",
        "description": "NIFTY 200 Index constituents",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_nifty200list.csv"],
    },
    "NIFTY_MIDCAP100": {
        "label": "NIFTY Midcap 100",
        "description": "NIFTY Midcap 100 - Prime swing trading opportunities",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_niftymidcap100list.csv"],
    },
    "NIFTY_SMALLCAP100": {
        "label": "NIFTY Smallcap 100",
        "description": "NIFTY Smallcap 100 - High volatility swing trades",
        "urls": ["https://niftyindices.com/IndexConstituent/ind_niftysmallcap100list.csv"],
    },
}


@dataclass
class Watchlist:
    """Represents a user watchlist."""
    name: str
    stocks: list[str]
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    is_preset: bool = False
    source: str = "static"
    last_refreshed: str = ""
    is_fallback: bool = False


def _normalize_symbol(value: str) -> str:
    text = str(value or "").upper().strip()
    text = text.replace(".NS", "").replace(".BO", "")
    return "".join(ch for ch in text if ch.isalnum() or ch in {"&", "-"})


def _dedupe_symbols(symbols: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for symbol in symbols:
        normalized = _normalize_symbol(symbol)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
    return ordered


def _fallback_universe_map() -> dict[str, list[str]]:
    return {
        "NIFTY50": NIFTY50_STOCKS,
        "NIFTY_NEXT50": NIFTY_NEXT50_STOCKS,
        "NIFTY100": NIFTY100_STOCKS,
        "NIFTY200": _dedupe_symbols(NIFTY100_STOCKS + NIFTY_MIDCAP100_STOCKS),
        "NIFTY_MIDCAP100": NIFTY_MIDCAP100_STOCKS,
        "NIFTY_SMALLCAP100": NIFTY_SMALLCAP100_STOCKS,
        "NIFTY_MIDSMALL": NIFTY_MIDSMALL_STOCKS,
        "NSE_LIQUID_SWING": _dedupe_symbols(NIFTY100_STOCKS + NIFTY_MIDCAP100_STOCKS),
    }


def _load_universe_cache() -> dict:
    cache_path = Path(UNIVERSE_CACHE_FILE)
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_universe_cache(payload: dict):
    try:
        with open(UNIVERSE_CACHE_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _cache_is_fresh(payload: dict) -> bool:
    fetched_at = payload.get("fetched_at")
    if not fetched_at:
        return False
    try:
        cached_at = datetime.fromisoformat(fetched_at)
    except Exception:
        return False
    return datetime.now() - cached_at < timedelta(hours=UNIVERSE_CACHE_TTL_HOURS)


def _extract_symbols_from_csv(text: str) -> list[str]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return []

    symbol_key = None
    for field in reader.fieldnames:
        lowered = field.lower()
        if lowered in {"symbol", "ticker", "code"}:
            symbol_key = field
            break

    if not symbol_key:
        for field in reader.fieldnames:
            if "symbol" in field.lower():
                symbol_key = field
                break

    if not symbol_key:
        return []

    return _dedupe_symbols([row.get(symbol_key, "") for row in reader])


def _fetch_symbols_from_source(urls: list[str]) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,application/json,text/plain,*/*",
        "Referer": "https://niftyindices.com/",
    }
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            symbols = _extract_symbols_from_csv(response.text)
            if symbols:
                return symbols
        except Exception:
            continue
    return []


def refresh_market_universes(force_refresh: bool = False) -> dict:
    cached = _load_universe_cache()
    if cached and not force_refresh and _cache_is_fresh(cached):
        return cached

    fallback = _fallback_universe_map()
    payload = {
        "fetched_at": datetime.now().isoformat(),
        "source": "fallback",
        "watchlists": {},
    }

    live_results = {}
    for name, meta in LIVE_UNIVERSE_DEFS.items():
        symbols = _fetch_symbols_from_source(meta["urls"])
        if symbols:
            live_results[name] = symbols

    if live_results:
        payload["source"] = "live"
        for name, meta in LIVE_UNIVERSE_DEFS.items():
            stocks = live_results.get(name) or fallback.get(name, [])
            payload["watchlists"][name] = {
                "name": name,
                "label": meta["label"],
                "description": meta["description"],
                "stocks": stocks,
                "source": "live" if name in live_results else "fallback",
                "is_fallback": name not in live_results,
            }
    else:
        for name, stocks in fallback.items():
            payload["watchlists"][name] = {
                "name": name,
                "label": name.replace("_", " "),
                "description": LIVE_UNIVERSE_DEFS.get(name, {}).get("description", name.replace("_", " ")),
                "stocks": stocks,
                "source": "fallback",
                "is_fallback": True,
            }

    # Derived universes
    nifty100 = payload["watchlists"].get("NIFTY100", {}).get("stocks") or fallback["NIFTY100"]
    nifty200 = payload["watchlists"].get("NIFTY200", {}).get("stocks") or fallback["NIFTY200"]
    midcap = payload["watchlists"].get("NIFTY_MIDCAP100", {}).get("stocks") or fallback["NIFTY_MIDCAP100"]
    smallcap = payload["watchlists"].get("NIFTY_SMALLCAP100", {}).get("stocks") or fallback["NIFTY_SMALLCAP100"]
    next50 = payload["watchlists"].get("NIFTY_NEXT50", {}).get("stocks") or fallback["NIFTY_NEXT50"]

    payload["watchlists"]["NIFTY_MIDSMALL"] = {
        "name": "NIFTY_MIDSMALL",
        "label": "Mid + Small 200",
        "description": "Midcap + smallcap combined universe",
        "stocks": _dedupe_symbols(midcap + smallcap),
        "source": payload["source"],
        "is_fallback": payload["source"] != "live",
    }
    payload["watchlists"]["NSE_LIQUID_SWING"] = {
        "name": "NSE_LIQUID_SWING",
        "label": "NSE Liquid Swing",
        "description": "Liquid swing universe built from NIFTY 200 leaders",
        "stocks": _dedupe_symbols(nifty200),
        "source": payload["source"],
        "is_fallback": payload["source"] != "live",
    }
    payload["watchlists"]["NSE_EXPANDED_SWING"] = {
        "name": "NSE_EXPANDED_SWING",
        "label": "NSE Expanded Swing",
        "description": "Expanded liquid swing universe from Next 50, Midcap 100, and Smallcap 100",
        "stocks": _dedupe_symbols(next50 + midcap + smallcap),
        "source": payload["source"],
        "is_fallback": payload["source"] != "live",
    }
    payload["watchlists"]["NIFTY100"] = payload["watchlists"].get("NIFTY100") or {
        "name": "NIFTY100",
        "label": "NIFTY 100",
        "description": "NIFTY 100 Index constituents",
        "stocks": _dedupe_symbols(nifty100),
        "source": payload["source"],
        "is_fallback": payload["source"] != "live",
    }

    _save_universe_cache(payload)
    return payload


def get_universe_metadata(name: str) -> dict:
    payload = refresh_market_universes(force_refresh=False)
    return payload.get("watchlists", {}).get(name, {})


def get_preset_watchlists() -> dict[str, Watchlist]:
    """Get all preset watchlists."""
    payload = refresh_market_universes(force_refresh=False)
    fallback = _fallback_universe_map()
    presets = {}

    for name, meta in payload.get("watchlists", {}).items():
        stocks = meta.get("stocks") or fallback.get(name, [])
        presets[name] = Watchlist(
            name=name,
            stocks=stocks,
            description=meta.get("description", ""),
            is_preset=True,
            source=meta.get("source", payload.get("source", "fallback")),
            last_refreshed=payload.get("fetched_at", ""),
            is_fallback=bool(meta.get("is_fallback", False)),
        )

    # Add sector watchlists
    for sector, stocks in SECTOR_STOCKS.items():
        presets[f"SECTOR_{sector}"] = Watchlist(
            name=f"SECTOR_{sector}",
            stocks=stocks,
            description=f"{sector} sector stocks",
            is_preset=True,
            source="curated",
            last_refreshed=payload.get("fetched_at", ""),
            is_fallback=False,
        )

    return presets


def load_user_watchlists() -> dict[str, Watchlist]:
    """Load user-created watchlists from JSON file."""
    watchlist_path = Path(WATCHLIST_FILE)

    if not watchlist_path.exists():
        return {}

    try:
        with open(watchlist_path, 'r') as f:
            data = json.load(f)

        watchlists = {}
        for name, wl_data in data.items():
            watchlists[name] = Watchlist(**wl_data)

        return watchlists
    except Exception as e:
        print(f"Error loading watchlists: {e}")
        return {}


def save_user_watchlists(watchlists: dict[str, Watchlist]):
    """Save user watchlists to JSON file."""
    try:
        data = {name: asdict(wl) for name, wl in watchlists.items()}
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving watchlists: {e}")


def get_all_watchlists() -> dict[str, Watchlist]:
    """Get all watchlists (presets + user-created)."""
    presets = get_preset_watchlists()
    user_lists = load_user_watchlists()

    # User lists override presets with same name
    return {**presets, **user_lists}


def create_watchlist(name: str, stocks: list[str], description: str = "") -> Watchlist:
    """
    Create a new user watchlist.

    Args:
        name: Watchlist name
        stocks: List of stock tickers
        description: Optional description

    Returns:
        Created Watchlist object
    """
    now = datetime.now().isoformat()

    # Normalize stock tickers
    normalized_stocks = [s.upper().strip() for s in stocks]

    watchlist = Watchlist(
        name=name,
        stocks=normalized_stocks,
        description=description,
        created_at=now,
        updated_at=now,
        is_preset=False,
    )

    # Load existing and add new
    user_lists = load_user_watchlists()
    user_lists[name] = watchlist
    save_user_watchlists(user_lists)

    return watchlist


def update_watchlist(name: str, stocks: list[str] = None, description: str = None) -> Optional[Watchlist]:
    """
    Update an existing user watchlist.

    Args:
        name: Watchlist name
        stocks: New stock list (optional)
        description: New description (optional)

    Returns:
        Updated Watchlist or None if not found/preset
    """
    user_lists = load_user_watchlists()

    if name not in user_lists:
        print(f"Watchlist '{name}' not found or is a preset")
        return None

    watchlist = user_lists[name]

    if stocks is not None:
        watchlist.stocks = [s.upper().strip() for s in stocks]

    if description is not None:
        watchlist.description = description

    watchlist.updated_at = datetime.now().isoformat()

    save_user_watchlists(user_lists)
    return watchlist


def delete_watchlist(name: str) -> bool:
    """
    Delete a user watchlist.

    Args:
        name: Watchlist name

    Returns:
        True if deleted, False if not found/preset
    """
    user_lists = load_user_watchlists()

    if name not in user_lists:
        return False

    del user_lists[name]
    save_user_watchlists(user_lists)
    return True


def get_watchlist(name: str) -> Optional[Watchlist]:
    """Get a specific watchlist by name."""
    all_lists = get_all_watchlists()
    return all_lists.get(name)


def get_stocks_from_watchlist(name: str) -> list[str]:
    """Get stock list from a watchlist."""
    watchlist = get_watchlist(name)
    return watchlist.stocks if watchlist else []


def add_stocks_to_watchlist(name: str, stocks: list[str]) -> Optional[Watchlist]:
    """Add stocks to an existing user watchlist."""
    user_lists = load_user_watchlists()

    if name not in user_lists:
        return None

    watchlist = user_lists[name]
    normalized = [s.upper().strip() for s in stocks]

    # Add only new stocks
    existing = set(watchlist.stocks)
    for stock in normalized:
        if stock not in existing:
            watchlist.stocks.append(stock)

    watchlist.updated_at = datetime.now().isoformat()
    save_user_watchlists(user_lists)

    return watchlist


def remove_stocks_from_watchlist(name: str, stocks: list[str]) -> Optional[Watchlist]:
    """Remove stocks from an existing user watchlist."""
    user_lists = load_user_watchlists()

    if name not in user_lists:
        return None

    watchlist = user_lists[name]
    to_remove = {s.upper().strip() for s in stocks}
    watchlist.stocks = [s for s in watchlist.stocks if s not in to_remove]

    watchlist.updated_at = datetime.now().isoformat()
    save_user_watchlists(user_lists)

    return watchlist


def get_sector_for_stock(ticker: str) -> Optional[str]:
    """Find which sector a stock belongs to."""
    ticker_upper = ticker.upper().strip()

    for sector, stocks in SECTOR_STOCKS.items():
        if ticker_upper in stocks:
            return sector

    return None


def get_all_sectors() -> list[str]:
    """Get list of all available sectors."""
    return ALL_SECTORS


def get_sector_stocks(sector: str) -> list[str]:
    """Get stocks for a specific sector."""
    return SECTOR_STOCKS.get(sector, [])


def list_watchlists() -> list[dict]:
    """List watchlists with lightweight metadata for the frontend."""
    payload = refresh_market_universes(force_refresh=False)
    live_meta = payload.get("watchlists", {})
    watchlists = []
    for watchlist in get_all_watchlists().values():
        meta = live_meta.get(watchlist.name, {})
        watchlists.append({
            "name": watchlist.name,
            "label": meta.get("label", watchlist.name.replace("_", " ")),
            "description": watchlist.description,
            "stock_count": len(watchlist.stocks),
            "is_preset": watchlist.is_preset,
            "source": watchlist.source,
            "last_refreshed": watchlist.last_refreshed,
            "is_fallback": watchlist.is_fallback,
        })

    watchlists.sort(key=lambda item: (not item["is_preset"], item["name"]))
    return watchlists
