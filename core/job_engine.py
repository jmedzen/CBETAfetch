"""
CBETAfetch 2.0 - Job Coordination Engine
Provides asynchronous & threaded job management, structured task lifecycles,
real-time SSE log broadcasting, progress tracking, and cooperative cancellation.
"""

import time
import uuid
import threading
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    progress_percent: float = 0.0
    progress_message: str = "Ready"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal cancellation event
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def cancel(self):
        self._cancel_event.set()
        if self.status == JobStatus.RUNNING or self.status == JobStatus.PENDING:
            self.status = JobStatus.CANCELLED
            self.completed_at = time.time()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress_percent": round(self.progress_percent, 1),
            "progress_message": self.progress_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_s": round((self.completed_at or time.time()) - (self.started_at or self.created_at), 2) if self.started_at else 0.0,
            "error": self.error,
            "log_count": len(self.logs),
            "metadata": self.metadata
        }


class JobEngine:
    """
    Central Coordinator for all CBETA tasks with bounded memory retention.
    """

    def __init__(self, max_history: int = 50, max_logs: int = 2000):
        self.max_history = max_history
        self.max_logs = max_logs
        self.jobs: Dict[str, JobInfo] = {}
        self.lock = threading.RLock()
        self.global_logs: List[str] = []
        self._log_listeners: List[Callable[[str], None]] = []
        self.log_counter: int = 0

    def create_job(self, job_type: str, metadata: Optional[Dict[str, Any]] = None) -> JobInfo:
        with self.lock:
            job_id = f"{job_type}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            job = JobInfo(
                job_id=job_id,
                job_type=job_type,
                metadata=metadata or {}
            )
            self.jobs[job_id] = job
            # Trim history if exceeding max_history
            if len(self.jobs) > self.max_history:
                oldest_id = next(iter(self.jobs))
                if self.jobs[oldest_id].status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    del self.jobs[oldest_id]
            return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        with self.lock:
            return self.jobs.get(job_id)

    def get_active_job(self) -> Optional[JobInfo]:
        with self.lock:
            for job in reversed(list(self.jobs.values())):
                if job.status == JobStatus.RUNNING:
                    return job
            return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [job.to_dict() for job in reversed(list(self.jobs.values()))]

    def cancel_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            job.cancel()
            self.add_log(job_id, "Task cancellation requested.")
            return True

    def add_log(self, job_id: Optional[str], msg: str):
        if not msg:
            return

        formatted = msg if msg == "." else f"{time.strftime('%H:%M:%S')} - {msg}"

        with self.lock:
            self.log_counter += 1
            self.global_logs.append(formatted)
            # Memory leak protection: bound global logs ring buffer
            if len(self.global_logs) > self.max_logs:
                self.global_logs = self.global_logs[-self.max_logs:]

            if job_id and job_id in self.jobs:
                target_job = self.jobs[job_id]
                target_job.logs.append(formatted)
                # Bound per-job log storage to prevent memory exhaustion
                if len(target_job.logs) > 1000:
                    target_job.logs = target_job.logs[-1000:]
            listeners = list(self._log_listeners)

        for listener in listeners:
            try:
                listener(formatted)
            except Exception:
                pass

    def update_progress(self, job_id: str, percent: float, message: str = ""):
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.progress_percent = min(100.0, max(0.0, percent))
                if message:
                    job.progress_message = message

    def submit_task(
        self,
        job_type: str,
        task_fn: Callable[[JobInfo, Callable[[str], None]], None],
        metadata: Optional[Dict[str, Any]] = None
    ) -> JobInfo:
        """
        Creates a job and executes it in a background daemon thread.
        """
        job = self.create_job(job_type, metadata=metadata)

        def worker():
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            self.add_log(job.job_id, f"Job [{job.job_type}] started (ID: {job.job_id})")

            def job_logger(msg: str):
                self.add_log(job.job_id, msg)

            try:
                task_fn(job, job_logger)
                if not job.is_cancelled():
                    job.status = JobStatus.COMPLETED
                    job.progress_percent = 100.0
                    self.add_log(job.job_id, f"Job [{job.job_type}] completed successfully.")
            except Exception as e:
                import traceback
                job.error = str(e)
                self.add_log(job.job_id, f"Error in job [{job.job_type}]: {e}")
                self.add_log(job.job_id, traceback.format_exc())
                job.status = JobStatus.FAILED
            finally:
                job.completed_at = time.time()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return job

    def subscribe_logs(self, callback: Callable[[str], None]):
        with self.lock:
            self._log_listeners.append(callback)

    def unsubscribe_logs(self, callback: Callable[[str], None]):
        with self.lock:
            if callback in self._log_listeners:
                self._log_listeners.remove(callback)
