"""Sectors router - wraps sector_tracker.py with async task pattern."""

import dataclasses

from fastapi import APIRouter, BackgroundTasks

from sector_tracker import (
    analyze_all_sectors,
    get_sector_rotation_signals,
    get_sector_summary_table,
)
from backend.app.dependencies import task_store

router = APIRouter()


def _serialize_sector(s):
    d = dataclasses.asdict(s) if dataclasses.is_dataclass(s) else dict(s)
    return d


def _run_sector_analysis(task_id: str):
    try:
        metrics = analyze_all_sectors()
        rotation = get_sector_rotation_signals(metrics)
        summary_df = get_sector_summary_table(metrics)
        summary_records = summary_df.to_dict(orient="records") if summary_df is not None and not summary_df.empty else []
        task_store.complete(task_id, {
            "sectors": [_serialize_sector(m) for m in metrics],
            "rotation_signals": rotation,
            "summary_table": summary_records,
        })
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/analyze")
async def start_analysis(background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_sector_analysis, task_id)
    return {"task_id": task_id}


@router.get("/analyze/{task_id}")
async def get_analysis_result(task_id: str):
    return task_store.get(task_id)


@router.get("/quick")
async def quick_sector_overview(background_tasks: BackgroundTasks):
    """Start a sector analysis and return the task ID."""
    task_id = task_store.create()
    background_tasks.add_task(_run_sector_analysis, task_id)
    return {"task_id": task_id}
