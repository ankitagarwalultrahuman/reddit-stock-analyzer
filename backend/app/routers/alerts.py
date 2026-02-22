"""Alerts router - wraps stock_movement_analyzer.py and telegram_alerts.py."""

import dataclasses
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.app.dependencies import task_store

router = APIRouter()


class MovementScanRequest(BaseModel):
    tickers: list[str]
    threshold: float = 1.0


class TelegramTestRequest(BaseModel):
    message: str = "Test alert from Reddit Stock Analyzer"


class SmsTestRequest(BaseModel):
    message: str = "Test SMS from Reddit Stock Analyzer"
    to_number: Optional[str] = None


def _serialize_movement(m):
    if dataclasses.is_dataclass(m):
        d = dataclasses.asdict(m)
        # Convert datetime
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        return d
    return dict(m)


def _run_movement_scan(task_id: str, req: MovementScanRequest):
    try:
        from stock_movement_analyzer import detect_significant_movements, analyze_portfolio_movements
        movements = analyze_portfolio_movements(
            portfolio_tickers=req.tickers,
            threshold=req.threshold,
            send_alerts=False,
        )
        task_store.complete(task_id, [_serialize_movement(m) for m in movements])
    except Exception as e:
        task_store.fail(task_id, str(e))


@router.post("/movement/scan")
async def start_movement_scan(body: MovementScanRequest, background_tasks: BackgroundTasks):
    task_id = task_store.create()
    background_tasks.add_task(_run_movement_scan, task_id, body)
    return {"task_id": task_id}


@router.get("/movement/scan/{task_id}")
async def get_movement_result(task_id: str):
    return task_store.get(task_id)


@router.post("/telegram/test")
async def test_telegram(body: TelegramTestRequest):
    try:
        from telegram_alerts import send_alert, is_telegram_configured
        if not is_telegram_configured():
            return {"success": False, "error": "Telegram not configured"}
        success = send_alert(title="Test", message=body.message)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/sms/test")
async def test_sms(body: SmsTestRequest):
    try:
        from stock_movement_analyzer import send_sms, is_twilio_configured
        if not is_twilio_configured():
            return {"success": False, "error": "Twilio not configured"}
        success = send_sms(body.message, body.to_number)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}
