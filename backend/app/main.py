"""FastAPI app - REST API wrapping existing Python stock analyzer modules."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is on sys.path so existing modules can be imported
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.routers import (
    reports,
    stocks,
    portfolio,
    screener,
    swing,
    sectors,
    signals,
    news,
    alerts,
    weekly,
    etf,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize databases and caches on startup."""
    from stock_history import init_cache_db
    from signal_tracker import init_signals_db

    init_cache_db()
    init_signals_db()
    yield


app = FastAPI(
    title="Reddit Stock Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(screener.router, prefix="/api/screener", tags=["screener"])
app.include_router(swing.router, prefix="/api/swing", tags=["swing"])
app.include_router(sectors.router, prefix="/api/sectors", tags=["sectors"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(weekly.router, prefix="/api/weekly", tags=["weekly"])
app.include_router(etf.router, prefix="/api/etf", tags=["etf"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
