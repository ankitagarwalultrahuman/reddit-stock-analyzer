"""Common dependencies for FastAPI app - task store for async operations."""

import uuid
from datetime import datetime
from typing import Any

import numpy as np


def _sanitize_for_json(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


class TaskStore:
    """In-memory task store for long-running background operations."""

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}

    def create(self) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "status": "running",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }
        return task_id

    def complete(self, task_id: str, result: Any):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "complete"
            self._tasks[task_id]["result"] = _sanitize_for_json(result)

    def fail(self, task_id: str, error: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "error"
            self._tasks[task_id]["error"] = error

    def get(self, task_id: str) -> dict:
        return self._tasks.get(task_id, {"status": "not_found"})

    def cleanup_old(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours."""
        now = datetime.now()
        to_remove = []
        for tid, task in self._tasks.items():
            created = datetime.fromisoformat(task["created_at"])
            if (now - created).total_seconds() > max_age_hours * 3600:
                to_remove.append(tid)
        for tid in to_remove:
            del self._tasks[tid]


task_store = TaskStore()
