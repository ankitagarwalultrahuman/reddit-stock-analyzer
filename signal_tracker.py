"""
Signal Tracker Module - Stores and tracks trading signals for accuracy analysis.

Uses SQLite to store:
- All signals generated (sentiment + technical indicators)
- Price outcomes at 1, 3, 5, 10 days after signal
- Accuracy metrics and statistics
"""

import sqlite3
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Database configuration
SIGNALS_DB = "signals.db"


@dataclass
class Signal:
    """Represents a trading signal with all relevant data."""
    id: Optional[int] = None
    date: Optional[str] = None
    ticker: str = ""

    # Sentiment data
    sentiment: str = ""  # bullish, bearish, neutral, mixed
    mention_count: int = 0
    post_count: int = 0
    comment_count: int = 0

    # Technical data
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None
    macd_trend: Optional[str] = None
    ma_trend: Optional[str] = None
    technical_score: Optional[int] = None
    technical_bias: Optional[str] = None

    # Price data
    price_at_signal: Optional[float] = None
    price_1d: Optional[float] = None
    price_3d: Optional[float] = None
    price_5d: Optional[float] = None
    price_10d: Optional[float] = None

    # Confluence data
    confluence_score: int = 0
    confluence_signals: Optional[str] = None  # JSON string of aligned signals

    # Outcome tracking
    return_1d: Optional[float] = None
    return_3d: Optional[float] = None
    return_5d: Optional[float] = None
    return_10d: Optional[float] = None
    was_accurate_1d: Optional[bool] = None
    was_accurate_3d: Optional[bool] = None
    was_accurate_5d: Optional[bool] = None


def init_signals_db():
    """Initialize SQLite database for signal tracking."""
    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,

            -- Sentiment data
            sentiment TEXT,
            mention_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,

            -- Technical data
            rsi REAL,
            rsi_signal TEXT,
            macd_trend TEXT,
            ma_trend TEXT,
            technical_score INTEGER,
            technical_bias TEXT,

            -- Price data
            price_at_signal REAL,
            price_1d REAL,
            price_3d REAL,
            price_5d REAL,
            price_10d REAL,

            -- Confluence data
            confluence_score INTEGER DEFAULT 0,
            confluence_signals TEXT,

            -- Outcome tracking
            return_1d REAL,
            return_3d REAL,
            return_5d REAL,
            return_10d REAL,
            was_accurate_1d BOOLEAN,
            was_accurate_3d BOOLEAN,
            was_accurate_5d BOOLEAN,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(date, ticker)
        )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_sentiment ON signals(sentiment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_confluence ON signals(confluence_score)")

    # Create accuracy stats view
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS signal_accuracy_stats AS
        SELECT
            sentiment,
            confluence_score,
            COUNT(*) as total_signals,
            SUM(CASE WHEN was_accurate_1d = 1 THEN 1 ELSE 0 END) as accurate_1d,
            SUM(CASE WHEN was_accurate_3d = 1 THEN 1 ELSE 0 END) as accurate_3d,
            SUM(CASE WHEN was_accurate_5d = 1 THEN 1 ELSE 0 END) as accurate_5d,
            AVG(return_1d) as avg_return_1d,
            AVG(return_3d) as avg_return_3d,
            AVG(return_5d) as avg_return_5d
        FROM signals
        WHERE was_accurate_1d IS NOT NULL
        GROUP BY sentiment, confluence_score
    """)

    conn.commit()
    conn.close()


def store_signal(signal: Signal) -> int:
    """
    Store a new signal in the database.

    Args:
        signal: Signal object with data to store

    Returns:
        ID of the inserted signal
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO signals (
            date, ticker, sentiment, mention_count, post_count, comment_count,
            rsi, rsi_signal, macd_trend, ma_trend, technical_score, technical_bias,
            price_at_signal, confluence_score, confluence_signals, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        signal.date,
        signal.ticker,
        signal.sentiment,
        signal.mention_count,
        signal.post_count,
        signal.comment_count,
        signal.rsi,
        signal.rsi_signal,
        signal.macd_trend,
        signal.ma_trend,
        signal.technical_score,
        signal.technical_bias,
        signal.price_at_signal,
        signal.confluence_score,
        signal.confluence_signals,
    ))

    signal_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return signal_id


def update_price_outcomes(ticker: str, signal_date: str, prices: dict):
    """
    Update price outcomes for a signal.

    Args:
        ticker: Stock ticker
        signal_date: Date of the signal (YYYY-MM-DD)
        prices: Dict with keys like 'price_1d', 'price_3d', etc.
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    # Get the original price
    cursor.execute("""
        SELECT price_at_signal, sentiment FROM signals
        WHERE ticker = ? AND date = ?
    """, (ticker, signal_date))

    row = cursor.fetchone()
    if not row or not row[0]:
        conn.close()
        return

    price_at_signal = row[0]
    sentiment = row[1]

    # Calculate returns and accuracy
    updates = {"updated_at": "datetime('now')"}

    for days, price_key in [(1, 'price_1d'), (3, 'price_3d'), (5, 'price_5d'), (10, 'price_10d')]:
        if price_key in prices and prices[price_key]:
            price = prices[price_key]
            return_pct = ((price - price_at_signal) / price_at_signal) * 100

            updates[price_key] = price
            updates[f'return_{days}d'] = round(return_pct, 2)

            # Determine if prediction was accurate
            if sentiment in ('bullish',):
                accurate = return_pct > 0
            elif sentiment in ('bearish',):
                accurate = return_pct < 0
            else:
                accurate = None  # Neutral signals don't have accuracy

            if days <= 5:  # Only track accuracy for 1, 3, 5 days
                updates[f'was_accurate_{days}d'] = accurate

    # Build update query
    set_clauses = []
    values = []
    for key, value in updates.items():
        if key == "updated_at":
            set_clauses.append(f"{key} = datetime('now')")
        else:
            set_clauses.append(f"{key} = ?")
            values.append(value)

    values.extend([ticker, signal_date])

    cursor.execute(f"""
        UPDATE signals SET {', '.join(set_clauses)}
        WHERE ticker = ? AND date = ?
    """, values)

    conn.commit()
    conn.close()


def get_signals_needing_price_update() -> list[dict]:
    """
    Get signals that need price outcome updates.

    Returns signals where:
    - Signal is at least 1 day old
    - Price outcomes are not yet filled
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    today = datetime.now().date()

    cursor.execute("""
        SELECT id, date, ticker, sentiment, price_at_signal
        FROM signals
        WHERE (
            (price_1d IS NULL AND date <= date('now', '-1 day'))
            OR (price_3d IS NULL AND date <= date('now', '-3 day'))
            OR (price_5d IS NULL AND date <= date('now', '-5 day'))
            OR (price_10d IS NULL AND date <= date('now', '-10 day'))
        )
        AND price_at_signal IS NOT NULL
        ORDER BY date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    signals = []
    for row in rows:
        signal_date = datetime.strptime(row[1], "%Y-%m-%d").date()
        days_old = (today - signal_date).days

        signals.append({
            "id": row[0],
            "date": row[1],
            "ticker": row[2],
            "sentiment": row[3],
            "price_at_signal": row[4],
            "days_old": days_old,
            "needs_1d": days_old >= 1,
            "needs_3d": days_old >= 3,
            "needs_5d": days_old >= 5,
            "needs_10d": days_old >= 10,
        })

    return signals


def get_accuracy_stats(days: int = 30) -> dict:
    """
    Get signal accuracy statistics.

    Args:
        days: Number of days to look back

    Returns:
        Dict with accuracy metrics by sentiment and confluence score
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    # Overall accuracy by sentiment
    cursor.execute("""
        SELECT
            sentiment,
            COUNT(*) as total,
            SUM(CASE WHEN was_accurate_1d = 1 THEN 1 ELSE 0 END) as acc_1d,
            SUM(CASE WHEN was_accurate_3d = 1 THEN 1 ELSE 0 END) as acc_3d,
            SUM(CASE WHEN was_accurate_5d = 1 THEN 1 ELSE 0 END) as acc_5d,
            AVG(return_1d) as avg_ret_1d,
            AVG(return_3d) as avg_ret_3d,
            AVG(return_5d) as avg_ret_5d
        FROM signals
        WHERE date >= date('now', ? || ' days')
        AND was_accurate_1d IS NOT NULL
        GROUP BY sentiment
    """, (f"-{days}",))

    by_sentiment = {}
    for row in cursor.fetchall():
        sentiment = row[0]
        total = row[1]
        by_sentiment[sentiment] = {
            "total": total,
            "accuracy_1d": round((row[2] / total) * 100, 1) if total > 0 else 0,
            "accuracy_3d": round((row[3] / total) * 100, 1) if total > 0 else 0,
            "accuracy_5d": round((row[4] / total) * 100, 1) if total > 0 else 0,
            "avg_return_1d": round(row[5], 2) if row[5] else 0,
            "avg_return_3d": round(row[6], 2) if row[6] else 0,
            "avg_return_5d": round(row[7], 2) if row[7] else 0,
        }

    # Accuracy by confluence score
    cursor.execute("""
        SELECT
            CASE
                WHEN confluence_score >= 4 THEN 'Strong (4-5)'
                WHEN confluence_score >= 3 THEN 'Moderate (3)'
                ELSE 'Weak (0-2)'
            END as strength,
            COUNT(*) as total,
            SUM(CASE WHEN was_accurate_3d = 1 THEN 1 ELSE 0 END) as acc_3d,
            AVG(return_3d) as avg_ret_3d
        FROM signals
        WHERE date >= date('now', ? || ' days')
        AND was_accurate_3d IS NOT NULL
        AND sentiment IN ('bullish', 'bearish')
        GROUP BY strength
    """, (f"-{days}",))

    by_confluence = {}
    for row in cursor.fetchall():
        by_confluence[row[0]] = {
            "total": row[1],
            "accuracy_3d": round((row[2] / row[1]) * 100, 1) if row[1] > 0 else 0,
            "avg_return_3d": round(row[3], 2) if row[3] else 0,
        }

    # Best performing stocks
    cursor.execute("""
        SELECT
            ticker,
            COUNT(*) as signals,
            AVG(return_3d) as avg_return,
            SUM(CASE WHEN was_accurate_3d = 1 THEN 1 ELSE 0 END) as accurate
        FROM signals
        WHERE date >= date('now', ? || ' days')
        AND was_accurate_3d IS NOT NULL
        GROUP BY ticker
        HAVING COUNT(*) >= 3
        ORDER BY avg_return DESC
        LIMIT 10
    """, (f"-{days}",))

    top_performers = []
    for row in cursor.fetchall():
        top_performers.append({
            "ticker": row[0],
            "signals": row[1],
            "avg_return_3d": round(row[2], 2) if row[2] else 0,
            "accuracy": round((row[3] / row[1]) * 100, 1) if row[1] > 0 else 0,
        })

    conn.close()

    return {
        "period_days": days,
        "by_sentiment": by_sentiment,
        "by_confluence": by_confluence,
        "top_performers": top_performers,
    }


def get_signal_history(ticker: str, limit: int = 30) -> list[dict]:
    """
    Get signal history for a specific ticker.

    Args:
        ticker: Stock ticker
        limit: Maximum number of signals to return

    Returns:
        List of signal records
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            date, sentiment, mention_count, confluence_score,
            technical_score, technical_bias, price_at_signal,
            return_1d, return_3d, return_5d, was_accurate_3d
        FROM signals
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
    """, (ticker, limit))

    signals = []
    for row in cursor.fetchall():
        signals.append({
            "date": row[0],
            "sentiment": row[1],
            "mentions": row[2],
            "confluence": row[3],
            "tech_score": row[4],
            "tech_bias": row[5],
            "price": row[6],
            "return_1d": row[7],
            "return_3d": row[8],
            "return_5d": row[9],
            "accurate": row[10],
        })

    conn.close()
    return signals


def get_recent_signals(days: int = 7, min_confluence: int = 0) -> list[dict]:
    """
    Get recent signals with optional confluence filter.

    Args:
        days: Number of days to look back
        min_confluence: Minimum confluence score filter

    Returns:
        List of recent signals
    """
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            date, ticker, sentiment, mention_count,
            confluence_score, confluence_signals,
            technical_score, technical_bias, rsi, macd_trend,
            price_at_signal, return_1d, return_3d
        FROM signals
        WHERE date >= date('now', ? || ' days')
        AND confluence_score >= ?
        ORDER BY date DESC, confluence_score DESC
    """, (f"-{days}", min_confluence))

    signals = []
    for row in cursor.fetchall():
        signals.append({
            "date": row[0],
            "ticker": row[1],
            "sentiment": row[2],
            "mentions": row[3],
            "confluence": row[4],
            "confluence_details": json.loads(row[5]) if row[5] else [],
            "tech_score": row[6],
            "tech_bias": row[7],
            "rsi": row[8],
            "macd_trend": row[9],
            "price": row[10],
            "return_1d": row[11],
            "return_3d": row[12],
        })

    conn.close()
    return signals


def get_signals_for_date(signal_date: str) -> list[dict]:
    """Get all signals for a specific date."""
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM signals WHERE date = ?
        ORDER BY confluence_score DESC, mention_count DESC
    """, (signal_date,))

    columns = [desc[0] for desc in cursor.description]
    signals = []
    for row in cursor.fetchall():
        signals.append(dict(zip(columns, row)))

    conn.close()
    return signals


def clear_old_signals(days: int = 90):
    """Delete signals older than specified days."""
    init_signals_db()

    conn = sqlite3.connect(SIGNALS_DB)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM signals WHERE date < date('now', ? || ' days')
    """, (f"-{days}",))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted
