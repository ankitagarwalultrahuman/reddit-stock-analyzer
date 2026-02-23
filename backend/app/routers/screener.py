"""Screener router - wraps stock_screener.py with async task pattern."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.app.dependencies import task_store

router = APIRouter()


class ScanRequest(BaseModel):
    watchlist: str = "NIFTY50"
    strategy: str = "oversold_reversal"
    min_matches: int = 2


def _serialize_result(r):
    d = dataclasses.asdict(r) if dataclasses.is_dataclass(r) else dict(r)
    # Remove the full signals object to keep response lean
    d.pop("signals", None)
    return d


def _run_scan(task_id: str, req: ScanRequest):
    try:
        from stock_screener import scan_watchlist
        from watchlist_manager import get_stocks_from_watchlist
        results = scan_watchlist(
            watchlist_name=req.watchlist,
            strategy_name=req.strategy,
            min_matches=req.min_matches,
        )

        total_stocks = len(get_stocks_from_watchlist(req.watchlist))

        # Build summary metrics
        bias_counts = {}
        for r in results:
            bias = r.technical_bias or "neutral"
            bias_counts[bias] = bias_counts.get(bias, 0) + 1

        summary = {
            "total_scanned": total_stocks,
            "matched": len(results),
            "avg_score": round(sum(r.score for r in results) / len(results), 1) if results else 0,
            "bias_distribution": bias_counts,
        }

        task_store.complete(task_id, {
            "results": [_serialize_result(r) for r in results],
            "summary": summary,
        })
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/scan")
async def start_scan(body: ScanRequest, background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_scan, task_id, body)
    return {"task_id": task_id}


@router.get("/scan/{task_id}")
async def get_scan_result(task_id: str):
    return task_store.get(task_id)


@router.get("/strategies")
async def list_strategies():
    from stock_screener import get_available_strategies
    strategies = get_available_strategies()
    return {
        name: {"name": s.name, "description": s.description}
        for name, s in strategies.items()
    }


@router.get("/quick/{strategy}")
async def quick_scan(strategy: str, background_tasks: BackgroundTasks):
    req = ScanRequest(watchlist="NIFTY50", strategy=strategy, min_matches=2)
    task_id = task_store.create()
    background_tasks.add_task(_run_scan, task_id, req)
    return {"task_id": task_id}
