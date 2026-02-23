"""Swing screener router - wraps swing_screener.py with async task pattern."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.app.dependencies import task_store

router = APIRouter()


class SwingScanRequest(BaseModel):
    watchlist: str = "NIFTY50"
    min_score: int = 60
    setup_types: Optional[list[str]] = None


def _serialize_setup(s):
    d = dataclasses.asdict(s) if dataclasses.is_dataclass(s) else dict(s)
    # Convert enum to string
    if "setup_type" in d and hasattr(d["setup_type"], "value"):
        d["setup_type"] = d["setup_type"].value
    # Convert tuples to lists for JSON
    if "entry_zone" in d and isinstance(d["entry_zone"], tuple):
        d["entry_zone"] = list(d["entry_zone"])
    return d


def _serialize_screener_result(r):
    """Serialize a ScreenerResult to JSON-compatible dict."""
    d = dataclasses.asdict(r) if dataclasses.is_dataclass(r) else dict(r)
    # Convert enum values in nested setups
    if "setups" in d:
        d["setup_count"] = len(d["setups"])
        d.pop("setups", None)  # Remove full setups from all_results to keep it lean
    return d


def _run_swing_scan(task_id: str, req: SwingScanRequest):
    try:
        from swing_screener import run_swing_screener, get_top_swing_setups, get_screener_summary
        from watchlist_manager import get_stocks_from_watchlist
        stocks = get_stocks_from_watchlist(req.watchlist)
        results = run_swing_screener(stocks=stocks, min_score=req.min_score)
        setups = get_top_swing_setups(results, top_n=20)

        # Build summary
        by_type = {}
        for r in results:
            for s in r.setups:
                st = s.setup_type.value if hasattr(s.setup_type, "value") else str(s.setup_type)
                by_type[st] = by_type.get(st, 0) + 1

        bias_counts = {}
        for r in results:
            bias_counts[r.technical_bias] = bias_counts.get(r.technical_bias, 0) + 1

        task_store.complete(task_id, {
            "results_count": len(results),
            "setups": [_serialize_setup(s) for s in setups],
            "all_results": [_serialize_screener_result(r) for r in results],
            "summary": {
                "stocks_scanned": len(stocks),
                "setups_found": sum(len(r.setups) for r in results),
                "avg_score": round(sum(r.total_score for r in results) / len(results), 1) if results else 0,
                "by_type": by_type,
                "bias_distribution": bias_counts,
            },
        })
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/scan")
async def start_swing_scan(body: SwingScanRequest, background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_swing_scan, task_id, body)
    return {"task_id": task_id}


@router.get("/scan/{task_id}")
async def get_swing_result(task_id: str):
    return task_store.get(task_id)
