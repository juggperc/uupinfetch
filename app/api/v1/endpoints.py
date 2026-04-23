"""
Main API router — aggregates all domain routers.
Previously a 737-line god file; now delegates to focused domain routers.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
import json
import asyncio
from datetime import datetime

from app.db.database import get_db
from app.schemas.schemas import HealthResponse
from app.core.config import get_settings
from app.services.job_queue import job_queue

# Domain routers
from app.api.v1.routes.search import router as search_router
from app.api.v1.routes.ratios import router as ratios_router
from app.api.v1.routes.tradeup import router as tradeup_router
from app.api.v1.routes.patterns import router as patterns_router
from app.api.v1.routes.portfolio import router as portfolio_router
from app.api.v1.routes.backtest import router as backtest_router

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# Include all domain routers
router.include_router(search_router)
router.include_router(ratios_router)
router.include_router(tradeup_router)
router.include_router(patterns_router)
router.include_router(portfolio_router)
router.include_router(backtest_router)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        youpin_enabled=settings.ENABLE_YOUPIN and bool(settings.YOUPIN_TOKEN),
        buff_enabled=settings.ENABLE_BUFF and bool(settings.BUFF_SESSION_COOKIE),
        skinport_enabled=settings.ENABLE_SKINPORT,
    )

# Admin / observability endpoints

@router.get("/admin/jobs")
async def get_job_queue_status(limit: int = Query(50, ge=1, le=200)):
    """Get background job queue status for admin visibility."""
    return {
        "jobs": job_queue.get_jobs(limit=limit),
        "running": job_queue._running,
    }

@router.get("/admin/jobs/{job_id}")
async def get_job_detail(job_id: str):
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# SSE Alerts Stream

async def alert_stream_generator():
    """Generate SSE events for price alerts and bot activity."""
    while True:
        try:
            from app.services.bot_engine import get_bot_sync
            bot = get_bot_sync()
            alerts = await bot.check_watchlist()
            
            if alerts:
                for alert in alerts[:3]:
                    yield f"event: watchlist_alert\ndata: {json.dumps(alert)}\n\n"
            
            yield f"event: heartbeat\ndata: {json.dumps({'time': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(15)
        except Exception as e:
            logger.warning(f"SSE stream error: {e}")
            await asyncio.sleep(5)

@router.get("/alerts/stream")
async def alerts_stream():
    """Server-Sent Events stream for real-time price alerts and bot activity."""
    return StreamingResponse(
        alert_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
