"""ETF router - wraps etf_analysis.py with async task pattern."""

import dataclasses

from fastapi import APIRouter, BackgroundTasks

from backend.app.dependencies import task_store

router = APIRouter()


def _run_etf_analysis(task_id: str):
    try:
        from etf_analysis import analyze_all_etfs, get_etf_summary, ETF_UNIVERSE

        metrics = analyze_all_etfs()
        summary = get_etf_summary(metrics)

        task_store.complete(task_id, {
            "etfs": [dataclasses.asdict(m) for m in metrics],
            "summary": summary,
        })
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/analyze")
async def start_analysis(background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_etf_analysis, task_id)
    return {"task_id": task_id}


@router.get("/analyze/{task_id}")
async def get_analysis_result(task_id: str):
    return task_store.get(task_id)


@router.get("/universe")
async def get_etf_universe():
    from etf_analysis import ETF_UNIVERSE
    return {
        ticker: {"name": name, "category": cat}
        for ticker, (name, cat) in ETF_UNIVERSE.items()
    }
