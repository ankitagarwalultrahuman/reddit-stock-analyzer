"""Swing screener router - wraps swing_screener.py with async task pattern."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from swing_screener import run_swing_screener, get_top_swing_setups
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


def _run_swing_scan(task_id: str, req: SwingScanRequest):
    try:
        from watchlist_manager import get_stocks_from_watchlist
        stocks = get_stocks_from_watchlist(req.watchlist)
        results = run_swing_screener(stocks=stocks, min_score=req.min_score)
        setups = get_top_swing_setups(results, top_n=20)
        task_store.complete(task_id, {
            "results_count": len(results),
            "setups": [_serialize_setup(s) for s in setups],
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
