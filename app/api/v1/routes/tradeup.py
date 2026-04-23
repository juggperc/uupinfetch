"""
Trade-up API routes.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging
from app.services.tradeup_engine import (
    analyze_trade_up, find_profitable_tradeups, get_collections_summary,
    TradeUpInput, RarityTier, COLLECTIONS
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/tradeup/collections")
async def get_tradeup_collections():
    return {"collections": get_collections_summary()}

@router.get("/tradeup/scan")
async def scan_tradeups(
    max_cost: float = Query(100.0, description="Max total input cost"),
    min_profit_pct: float = Query(5.0, description="Minimum ROI %"),
    collection: Optional[str] = Query(None, description="Filter by collection name"),
):
    try:
        collections = [collection] if collection else None
        results = await find_profitable_tradeups(
            target_collections=collections,
            max_cost=max_cost,
            min_profit_pct=min_profit_pct,
        )
        return {
            "count": len(results),
            "max_cost": max_cost,
            "min_profit_pct": min_profit_pct,
            "tradeups": results,
        }
    except Exception as e:
        logger.error(f"Trade-up scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tradeup/calculate")
async def calculate_tradeup(data: Dict[str, Any]):
    try:
        input_data = data.get("inputs", [])
        if len(input_data) != 10:
            raise HTTPException(status_code=400, detail="Exactly 10 inputs required")
        
        inputs = []
        for inp in input_data:
            skin_name = inp.get("skin_name", "")
            coll_name = inp.get("collection", "")
            found_skin = None
            
            for coll in COLLECTIONS:
                if coll.name == coll_name:
                    for skin in coll.skins:
                        if skin.name == skin_name:
                            found_skin = skin
                            break
                if found_skin:
                    break
            
            if not found_skin:
                for coll in COLLECTIONS:
                    for skin in coll.skins:
                        if skin.name == skin_name:
                            found_skin = skin
                            coll_name = coll.name
                            break
                    if found_skin:
                        break
            
            if not found_skin:
                raise HTTPException(status_code=400, detail=f"Skin not found: {skin_name}")
            
            inputs.append(TradeUpInput(
                skin=found_skin,
                collection=coll_name,
                price=float(inp.get("price", 0)),
                float_value=float(inp.get("float", 0.15)),
            ))
        
        contract = await analyze_trade_up(inputs)
        if not contract:
            raise HTTPException(status_code=400, detail="Invalid trade-up configuration")
        
        return {
            "total_cost": round(contract.total_cost, 2),
            "expected_value": round(contract.expected_value, 2),
            "expected_profit": round(contract.expected_profit, 2),
            "roi_pct": round(contract.roi_pct, 2),
            "profit_probability": round(contract.profit_probability * 100, 1),
            "break_even_probability": round(contract.break_even_probability * 100, 1),
            "worst_case": round(contract.worst_case, 2),
            "best_case": round(contract.best_case, 2),
            "input_rarity": contract.input_rarity,
            "output_rarity": contract.output_rarity,
            "collections": contract.collections_used,
            "outputs": [
                {
                    "name": o.skin.name,
                    "collection": o.collection,
                    "probability": round(o.probability * 100, 1),
                    "predicted_float": round(o.predicted_float, 6),
                    "estimated_price": o.estimated_price,
                }
                for o in contract.outputs
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade-up calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
