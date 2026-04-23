"""
Ratios API routes.
"""

from fastapi import APIRouter, Query
from typing import Optional
import asyncio
import logging
from app.services.ratio_engine import ratio_engine
from app.services.scraper import background_scraper
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/ratios")
async def get_ratios(
    source: str = Query("buff", description="Target marketplace: buff, youpin, skinport, csfloat"),
    limit: int = Query(50, ge=1, le=200),
    max_price: Optional[float] = Query(None, description="Max Steam price filter"),
    min_volume: Optional[int] = Query(None, description="Min Steam volume filter"),
    refresh: bool = Query(False, description="Force fresh scan"),
):
    if refresh:
        asyncio.create_task(ratio_engine.scan_ratios(max_items=80))
    
    results = ratio_engine.get_best_ratios(
        source=source, limit=limit, max_price=max_price, min_volume=min_volume
    )
    
    if not results and not refresh:
        try:
            results = await ratio_engine.get_best_ratios_from_db(
                source=source, limit=limit, max_price=max_price, min_volume=min_volume
            )
        except Exception as e:
            logger.debug(f"DB ratio fallback failed: {e}")
    
    return {
        "source": source,
        "count": len(results),
        "last_update": ratio_engine._last_update,
        "items": results,
    }

@router.get("/ratios/summary")
async def get_ratio_summary():
    return ratio_engine.get_ratio_summary()

@router.post("/ratios/scan")
async def trigger_ratio_scan(max_items: int = Query(80, ge=1, le=200)):
    asyncio.create_task(ratio_engine.scan_ratios(max_items=max_items))
    return {"status": "scanning", "message": "Ratio scan started in background"}

@router.get("/ratios/item/{item_name}")
async def get_item_ratio_history(
    item_name: str,
    source: str = Query("buff", description="Marketplace source"),
    limit: int = Query(30, ge=1, le=365),
):
    history = await background_scraper.get_ratio_history(item_name, source, limit)
    return {
        "item_name": item_name,
        "source": source,
        "count": len(history),
        "data": [
            {
                "steam_price": h.steam_price,
                "tp_price": getattr(h, f"{source}_price", None),
                "ratio": getattr(h, f"{source}_ratio", None),
                "recorded_at": h.recorded_at.isoformat() if h.recorded_at else None,
            }
            for h in history
        ],
    }
