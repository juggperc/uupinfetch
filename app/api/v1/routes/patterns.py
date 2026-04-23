"""
Pattern detection API routes.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
from app.services.pattern_engine import analyze_pattern, get_pattern_alert
from app.services.steam import steam_scraper
from app.services.skinport import skinport_scraper
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/patterns/analyze")
async def analyze_skin_pattern(
    item_name: str = Query(..., description="Full skin name"),
    paint_seed: Optional[int] = Query(None, description="Paint seed (0-1000)"),
    float_value: Optional[float] = Query(None, description="Float value"),
):
    try:
        result = analyze_pattern(item_name, paint_seed, float_value)
        return {
            "item_name": result.item_name,
            "pattern_type": result.pattern_type.value,
            "pattern_subtype": result.pattern_subtype,
            "tier": result.tier,
            "estimated_premium_pct": result.estimated_premium_pct,
            "notes": result.notes,
        }
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns/scan")
async def scan_for_pattern_deals(
    query: str = Query("Knife", description="Search query for pattern skins"),
    limit: int = Query(20, ge=1, le=50),
):
    try:
        all_items = []
        steam_results = await steam_scraper.search_items(query, page_size=limit)
        all_items.extend(steam_results)
        
        if settings.ENABLE_SKINPORT:
            skinport_results = await skinport_scraper.search_items(query, page_size=limit)
            all_items.extend(skinport_results)
        
        alerts = []
        for item in all_items:
            name = item.get("name", "")
            price = item.get("price")
            seed = item.get("paint_seed")
            if not price:
                continue
            alert = get_pattern_alert(name, price, seed)
            if alert:
                alert["source"] = item.get("source", "unknown")
                alert["external_id"] = item.get("external_id", "")
                alerts.append(alert)
        
        return {"searched": len(all_items), "alerts": alerts}
    except Exception as e:
        logger.error(f"Pattern scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
