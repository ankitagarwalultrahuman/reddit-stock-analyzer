"""Weekly analysis router - wraps weekly_analysis.py with async task pattern."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.app.dependencies import task_store

router = APIRouter()


class WeeklyPulseRequest(BaseModel):
    watchlist: str = "NIFTY50"


def _serialize_report(report):
    """Serialize WeeklyPulseReport dataclass to JSON-compatible dict."""
    d = {}
    for field in dataclasses.fields(report):
        val = getattr(report, field.name)
        if hasattr(val, "isoformat"):
            d[field.name] = val.isoformat()
        elif isinstance(val, list):
            d[field.name] = [
                dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item
                for item in val
            ]
        elif dataclasses.is_dataclass(val):
            d[field.name] = dataclasses.asdict(val)
        else:
            d[field.name] = val
    return d


def _run_weekly_pulse(task_id: str, req: WeeklyPulseRequest):
    try:
        from weekly_analysis import generate_weekly_pulse, get_weekly_pulse_summary
        from watchlist_manager import get_stocks_from_watchlist
        stocks = get_stocks_from_watchlist(req.watchlist)
        report = generate_weekly_pulse(stocks=stocks)
        summary = get_weekly_pulse_summary(report)
        task_store.complete(task_id, {
            "report": _serialize_report(report),
            "summary": summary,
        })
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/pulse")
async def start_weekly_pulse(body: WeeklyPulseRequest, background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_weekly_pulse, task_id, body)
    return {"task_id": task_id}


@router.get("/pulse/{task_id}")
async def get_weekly_result(task_id: str):
    return task_store.get(task_id)


@router.get("/nifty")
async def nifty_performance():
    from weekly_analysis import get_nifty_performance
    return get_nifty_performance()
