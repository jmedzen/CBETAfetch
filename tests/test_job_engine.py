"""
Unit tests for core.job_engine module.
"""

import time
import pytest
from core.job_engine import JobEngine, JobStatus


def test_job_lifecycle():
    engine = JobEngine()
    
    def dummy_task(job, log):
        log("Step 1")
        engine.update_progress(job.job_id, 50.0, "Halfway")
        log("Step 2")

    job = engine.submit_task("test", dummy_task)
    # Wait for completion
    for _ in range(50):
        if job.status == JobStatus.COMPLETED:
            break
        time.sleep(0.02)

    assert job.status == JobStatus.COMPLETED
    assert job.progress_percent == 100.0
    assert len(job.logs) >= 3


def test_job_failure():
    engine = JobEngine()

    def failing_task(job, log):
        log("About to fail")
        raise RuntimeError("Controlled test failure")

    job = engine.submit_task("fail_test", failing_task)
    for _ in range(50):
        if job.status == JobStatus.FAILED:
            break
        time.sleep(0.02)

    assert job.status == JobStatus.FAILED
    assert "Controlled test failure" in job.error
    assert any("RuntimeError" in l for l in job.logs)


def test_job_cancellation():
    engine = JobEngine()

    def cancellable_task(job, log):
        for _ in range(100):
            if job.is_cancelled():
                log("Job received cancellation")
                return
            time.sleep(0.02)

    job = engine.submit_task("cancel_test", cancellable_task)
    time.sleep(0.05)
    success = engine.cancel_job(job.job_id)

    assert success is True
    assert job.is_cancelled() is True
    assert job.status == JobStatus.CANCELLED


def test_job_history_limit():
    engine = JobEngine(max_history=5)
    for i in range(10):
        j = engine.create_job(f"type_{i}")
        j.status = JobStatus.COMPLETED

    jobs = engine.list_jobs()
    assert len(jobs) <= 6  # Kept within limit


def test_log_listeners():
    engine = JobEngine()
    received = []
    engine.subscribe_logs(received.append)

    engine.add_log(None, "Broadcast message")
    assert len(received) == 1
    assert "Broadcast message" in received[0]

    engine.unsubscribe_logs(received.append)
