"""Screener router - wraps stock_screener.py with async task pattern."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from stock_screener import (
    scan_watchlist,
    get_available_strategies,
)
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
        results = scan_watchlist(
            watchlist_name=req.watchlist,
            strategy_name=req.strategy,
            min_matches=req.min_matches,
        )
        task_store.complete(task_id, [_serialize_result(r) for r in results])
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
