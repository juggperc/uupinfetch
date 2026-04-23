"""
Simple in-memory job queue for background tasks.
Failed jobs retry with exponential backoff.
Exposes status for admin visibility.
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class Job:
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    next_retry_at: Optional[float] = None

class JobQueue:
    """In-memory priority job queue with retry logic."""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._worker())
            logger.info("Job queue started")
    
    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Job queue stopped")
    
    def submit(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Submit a job to the queue."""
        job_id = f"{name}_{int(time.time() * 1000)}"
        job = Job(
            id=job_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=kwargs.pop("max_retries", 3),
        )
        self._jobs[job_id] = job
        asyncio.create_task(self._queue.put(job_id))
        logger.info(f"Job {job_id} ({name}) submitted")
        return job_id
    
    async def _worker(self):
        while self._running:
            try:
                job_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                job = self._jobs.get(job_id)
                if not job:
                    continue
                
                if job.next_retry_at and time.time() < job.next_retry_at:
                    # Re-queue if not ready for retry
                    asyncio.create_task(self._queue.put(job_id))
                    await asyncio.sleep(1)
                    continue
                
                await self._execute_job(job)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Job queue worker error: {e}")
    
    async def _execute_job(self, job: Job):
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        
        try:
            if asyncio.iscoroutinefunction(job.func):
                job.result = await job.func(*job.args, **job.kwargs)
            else:
                job.result = job.func(*job.args, **job.kwargs)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            logger.info(f"Job {job.id} completed in {job.completed_at - job.started_at:.2f}s")
        except Exception as e:
            job.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            job.retries += 1
            
            if job.retries <= job.max_retries:
                delay = 2 ** job.retries  # Exponential backoff: 2s, 4s, 8s
                job.next_retry_at = time.time() + delay
                job.status = JobStatus.RETRYING
                asyncio.create_task(self._queue.put(job.id))
                logger.warning(f"Job {job.id} failed, retrying in {delay}s (attempt {job.retries}/{job.max_retries})")
            else:
                job.status = JobStatus.FAILED
                job.completed_at = time.time()
                logger.error(f"Job {job.id} failed permanently after {job.max_retries} retries: {e}")
    
    def get_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent jobs for admin visibility."""
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]
        return [
            {
                "id": j.id,
                "name": j.name,
                "status": j.status.value,
                "retries": j.retries,
                "max_retries": j.max_retries,
                "created_at": j.created_at,
                "started_at": j.started_at,
                "completed_at": j.completed_at,
                "error": j.error.split("\n")[0] if j.error else None,
            }
            for j in jobs
        ]
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "id": job.id,
            "name": job.name,
            "status": job.status.value,
            "result": job.result,
            "error": job.error,
            "retries": job.retries,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

# Singleton
job_queue = JobQueue()
