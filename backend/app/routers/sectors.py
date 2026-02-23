"""Sectors router - wraps sector_tracker.py with async task pattern."""

import dataclasses

from fastapi import APIRouter, BackgroundTasks

from backend.app.dependencies import task_store

router = APIRouter()


def _serialize_sector(s):
    d = dataclasses.asdict(s) if dataclasses.is_dataclass(s) else dict(s)
    return d


def _run_sector_analysis(task_id: str):
    try:
        from sector_tracker import (
            analyze_all_sectors,
            analyze_sector,
            get_sector_rotation_signals,
            get_sector_summary_table,
            analyze_stock_for_sector,
        )
        from watchlist_manager import get_sector_stocks
        metrics = analyze_all_sectors()
        rotation = get_sector_rotation_signals(metrics)
        summary_df = get_sector_summary_table(metrics)
        summary_records = summary_df.to_dict(orient="records") if summary_df is not None and not summary_df.empty else []

        # Enrich each sector with per-stock data
        sectors_with_stocks = []
        for m in metrics:
            d = _serialize_sector(m)
            # Get individual stock performances for this sector
            stocks = get_sector_stocks(m.sector)
            stock_perfs = []
            for ticker in stocks:
                perf = analyze_stock_for_sector(ticker)
                if perf:
                    stock_perfs.append(dataclasses.asdict(perf))
            d["stocks"] = sorted(stock_perfs, key=lambda x: x.get("return_1m", 0), reverse=True)
            sectors_with_stocks.append(d)

        task_store.complete(task_id, {
            "sectors": sectors_with_stocks,
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
