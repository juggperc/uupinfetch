from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
import json
import asyncio
from app.db.database import get_db
from app.models.models import Item, PriceHistory
from app.schemas.schemas import (
    ItemResponse, ItemDetailResponse, SearchResponse,
    HealthResponse, ScrapeStatus, PriceHistoryResponse
)
from app.services.youpin import youpin_scraper
from app.services.buff import buff_scraper
from app.services.steam import steam_scraper
from app.services.skinport import skinport_scraper
from app.services.csfloat import csfloat_scraper
from app.services.ratio_engine import ratio_engine
from app.services.market_fees import calculate_steam_ratio, ratio_grade, ratio_grade_zh
from app.services.tradeup_engine import (
    analyze_trade_up, find_profitable_tradeups, get_collections_summary,
    TradeUpInput, RarityTier, COLLECTIONS
)
from app.services.pattern_engine import analyze_pattern, get_pattern_alert
from app.services.scraper import background_scraper
from app.core.config import get_settings
from datetime import datetime

router = APIRouter(prefix="/api/v1")
settings = get_settings()
logger = logging.getLogger(__name__)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        youpin_enabled=settings.ENABLE_YOUPIN,
        buff_enabled=settings.ENABLE_BUFF,
        skinport_enabled=settings.ENABLE_SKINPORT,
    )

# ========== 挂刀 Ratio Engine Endpoints ==========

@router.get("/ratios")
async def get_ratios(
    source: str = Query("buff", description="Target marketplace: buff, youpin, skinport, csfloat"),
    limit: int = Query(50, ge=1, le=200),
    max_price: Optional[float] = Query(None, description="Max Steam price filter"),
    min_volume: Optional[int] = Query(None, description="Min Steam volume filter"),
    refresh: bool = Query(False, description="Force fresh scan"),
):
    """Get 挂刀 (Steam balance conversion) ratios. Lower = better.
    Returns cached/DB data immediately. Refresh is fire-and-forget."""
    if refresh:
        asyncio.create_task(ratio_engine.scan_ratios(max_items=80))
    
    results = ratio_engine.get_best_ratios(
        source=source, limit=limit, max_price=max_price, min_volume=min_volume
    )
    
    # If no in-memory cache, try to build from latest DB records quickly
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
    """Get ratio scan summary statistics."""
    return ratio_engine.get_ratio_summary()

@router.post("/ratios/scan")
async def trigger_ratio_scan(
    max_items: int = Query(80, ge=1, le=200),
):
    """Manually trigger a ratio scan."""
    import asyncio
    asyncio.create_task(ratio_engine.scan_ratios(max_items=max_items))
    return {"status": "scanning", "message": "Ratio scan started in background"}

@router.get("/ratios/item/{item_name}")
async def get_item_ratio_history(
    item_name: str,
    source: str = Query("buff", description="Marketplace source"),
    limit: int = Query(30, ge=1, le=365),
):
    """Get historical ratio data for a specific item."""
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

@router.get("/float/{item_name}")
async def get_float_data(
    item_name: str,
    limit: int = Query(10, ge=1, le=50),
):
    """Get CSFloat listings with float values for an item."""
    if not settings.ENABLE_CSFLOAT:
        raise HTTPException(status_code=503, detail="CSFloat scraper is disabled")
    
    try:
        listings = await csfloat_scraper.search_listings(item_name, limit=limit)
        return {
            "item_name": item_name,
            "count": len(listings),
            "listings": listings,
        }
    except Exception as e:
        logger.error(f"CSFloat fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== Trade-Up Contract Calculator ==========

@router.get("/tradeup/collections")
async def get_tradeup_collections():
    """Get all collections available for trade-up calculation."""
    return {"collections": get_collections_summary()}

@router.get("/tradeup/scan")
async def scan_tradeups(
    max_cost: float = Query(100.0, description="Max total input cost"),
    min_profit_pct: float = Query(5.0, description="Minimum ROI %"),
    collection: Optional[str] = Query(None, description="Filter by collection name"),
):
    """Scan for profitable trade-up contracts using live market prices."""
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
    """
    Calculate EV for a specific trade-up contract.
    
    Request body:
    {
        "inputs": [
            {"skin_name": "AK-47 | Safety Net", "collection": "Mirage", "price": 5.0, "float": 0.15},
            ... (10 items)
        ]
    }
    """
    try:
        input_data = data.get("inputs", [])
        if len(input_data) != 10:
            raise HTTPException(status_code=400, detail="Exactly 10 inputs required")
        
        # Build TradeUpInput objects
        inputs = []
        for inp in input_data:
            # Find the skin in collections
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
                # Try to find by name only
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

# ========== Pattern Detection ==========

@router.get("/patterns/analyze")
async def analyze_skin_pattern(
    item_name: str = Query(..., description="Full skin name"),
    paint_seed: Optional[int] = Query(None, description="Paint seed (0-1000)"),
    float_value: Optional[float] = Query(None, description="Float value"),
):
    """Analyze a skin for pattern-based value (blue gem, doppler phase, fade, etc.)."""
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
    """Search for pattern skins and flag potentially underpriced items."""
    try:
        # Search across sources
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
        
        return {
            "searched": len(all_items),
            "alerts": alerts,
        }
    except Exception as e:
        logger.error(f"Pattern scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(
    item_id: str,
    source: str = Query("steam", description="Data source"),
    db: Session = Depends(get_db),
):
    """Get detailed info for a specific item."""
    price_history = []
    related_items = []
    
    if source == "steam":
        price_data = await steam_scraper.get_price_overview(item_id)
        if price_data:
            item = {
                "source": "steam",
                "external_id": item_id,
                "name": item_id.replace("%20", " "),
                "price": price_data.get("lowest_price"),
                "image_url": f"https://steamcommunity-a.akamaihd.net/economy/image/{item_id}",
                "hash_name": item_id,
                "lowest_price": price_data.get("lowest_price"),
            }
        else:
            item = {
                "source": "steam",
                "external_id": item_id,
                "name": item_id,
                "price": None,
                "image_url": "",
                "hash_name": item_id,
            }
    
    elif source == "buff" and settings.ENABLE_BUFF:
        detail = await buff_scraper.get_item_detail(int(item_id))
        if detail:
            item_data = detail.get("goods_infos", {}).get(str(item_id), {})
            item = {
                "source": "buff",
                "external_id": str(item_id),
                "name": item_data.get("name", ""),
                "price": item_data.get("sell_min_price"),
                "image_url": item_data.get("icon_url", ""),
                "hash_name": item_data.get("market_hash_name", ""),
                "exterior": item_data.get("info", {}).get("tags", {}).get("exterior", {}).get("localized_name", ""),
                "rarity": item_data.get("info", {}).get("tags", {}).get("rarity", {}).get("localized_name", ""),
                "weapon_name": item_data.get("info", {}).get("tags", {}).get("weapon", {}).get("localized_name", ""),
                "lowest_price": item_data.get("sell_min_price"),
            }
            history = await buff_scraper.get_price_history(int(item_id), days=30)
            for h in history:
                price_history.append({
                    "price": h.get("price", 0),
                    "volume": h.get("volume", 0),
                    "recorded_at": h.get("date", datetime.now()),
                    "source": "buff",
                    "item_id": int(item_id),
                })
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    
    elif source == "youpin" and settings.ENABLE_YOUPIN:
        detail = await youpin_scraper.get_commodity_detail(int(item_id))
        if detail:
            item = {
                "source": "youpin",
                "external_id": str(item_id),
                "name": detail.get("CommodityName", ""),
                "price": detail.get("Price"),
                "image_url": detail.get("ImgUrl", ""),
                "hash_name": detail.get("MarketHashName", ""),
                "exterior": detail.get("ExteriorName", ""),
                "rarity": detail.get("RarityName", ""),
                "weapon_name": detail.get("WeaponName", ""),
                "lowest_price": detail.get("LowestPrice"),
                "lease_unit_price": detail.get("LeaseUnitPrice"),
                "lease_deposit": detail.get("LeaseDeposit"),
                "seller_name": detail.get("UserNickName", ""),
                "on_lease": detail.get("OnLease", False),
            }
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    
    elif source == "skinport" and settings.ENABLE_SKINPORT:
        detail = await skinport_scraper.get_item_detail(item_id)
        if detail:
            item = detail
        else:
            raise HTTPException(status_code=404, detail="Item not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    return ItemDetailResponse(
        item=ItemResponse(**item),
        price_history=[PriceHistoryResponse(**h) for h in price_history],
        related_items=related_items,
    )

@router.get("/categories")
async def get_categories():
    """Get item categories/filters."""
    if settings.ENABLE_YOUPIN:
        tags = await youpin_scraper.get_search_tags()
        if tags:
            return {"source": "youpin", "categories": tags}
    
    return {
        "source": "builtin",
        "categories": [
            {"id": "knife", "name": "Knives", "name_zh": "匕首"},
            {"id": "rifle", "name": "Rifles", "name_zh": "步枪"},
            {"id": "pistol", "name": "Pistols", "name_zh": "手枪"},
            {"id": "smg", "name": "SMGs", "name_zh": "冲锋枪"},
            {"id": "shotgun", "name": "Shotguns", "name_zh": "霰弹枪"},
            {"id": "machinegun", "name": "Machine Guns", "name_zh": "机枪"},
            {"id": "gloves", "name": "Gloves", "name_zh": "手套"},
            {"id": "agent", "name": "Agents", "name_zh": "探员"},
            {"id": "sticker", "name": "Stickers", "name_zh": "印花"},
            {"id": "case", "name": "Cases", "name_zh": "武器箱"},
        ],
    }

@router.get("/market/summary")
async def get_market_summary():
    """Get market summary statistics."""
    summary = {}
    
    if settings.ENABLE_BUFF:
        buff_summary = await buff_scraper.get_market_summary()
        if buff_summary:
            summary["buff"] = {
                "total_items": buff_summary.get("total_count", 0),
                "page": buff_summary.get("page_num", 1),
            }
    
    if settings.ENABLE_YOUPIN:
        stats = await youpin_scraper.get_order_deliver_stats()
        if stats:
            summary["youpin"] = {
                "deliver_success_rate": stats.get("DeliverSuccessRate"),
                "avg_deliver_time": stats.get("AvgDeliverTime"),
                "un_deliver_number": stats.get("UnDeliverNumber"),
            }
    
    if settings.ENABLE_SKINPORT:
        skinport_items = await skinport_scraper._fetch_all_items()
        if skinport_items:
            summary["skinport"] = {
                "total_items": len(skinport_items),
                "cached": True,
            }
    
    return summary

@router.get("/items/search", response_model=SearchResponse)
async def search_items(
    q: str = Query(..., min_length=1, max_length=200),
    source: str = Query("all", description="Data source: all, steam, buff, youpin, skinport"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Search items across all enabled sources."""
    all_items = []
    
    try:
        if source in ("all", "steam"):
            steam_results = await steam_scraper.search_items(q, page=page, page_size=page_size)
            for item in steam_results:
                item["source"] = "steam"
            all_items.extend(steam_results)
    except Exception as e:
        logger.warning(f"Steam search failed: {e}")
    
    try:
        if source in ("all", "skinport") and settings.ENABLE_SKINPORT:
            skinport_results = await skinport_scraper.search_items(q, page_size=page_size)
            for item in skinport_results:
                item["source"] = "skinport"
            all_items.extend(skinport_results)
    except Exception as e:
        logger.warning(f"Skinport search failed: {e}")
    
    try:
        if source in ("all", "buff") and settings.ENABLE_BUFF:
            buff_results = await buff_scraper.search_items(q, page=page, page_size=page_size)
            for item in buff_results:
                item["source"] = "buff"
            all_items.extend(buff_results)
    except Exception as e:
        logger.warning(f"Buff search failed: {e}")
    
    try:
        if source in ("all", "youpin") and settings.ENABLE_YOUPIN:
            youpin_results = await youpin_scraper.search_items(q, page=page, page_size=page_size)
            for item in youpin_results:
                item["source"] = "youpin"
            all_items.extend(youpin_results)
    except Exception as e:
        logger.warning(f"Youpin search failed: {e}")
    
    # Deduplicate by name+source
    seen = set()
    deduped = []
    for item in all_items:
        key = f"{item.get('name', '')}:{item.get('source', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    total = len(deduped)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = deduped[start:end]
    
    return SearchResponse(
        items=[ItemResponse(**item) for item in paginated],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/items/popular")
async def get_popular_items(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    """Get trending/popular items from the database."""
    items = db.query(Item).filter(
        Item.price.isnot(None)
    ).order_by(Item.updated_at.desc()).limit(limit).all()
    
    return {
        "items": [ItemResponse.model_validate(item) for item in items],
        "total": len(items),
    }

@router.get("/scrape/status", response_model=ScrapeStatus)
async def get_scrape_status():
    """Get scraper status."""
    return ScrapeStatus(
        status="running" if background_scraper.is_running else "idle",
        items_scraped=0,
    )

# ========== Portfolio Endpoints ==========

from app.services.portfolio_engine import PortfolioEngine
from app.schemas.schemas import PortfolioItemCreate, PortfolioItemResponse, PortfolioSummary, TransactionResponse

@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    """Get all portfolio holdings."""
    engine = PortfolioEngine(db)
    items = engine.get_all_items()
    return [PortfolioItemResponse.model_validate(item) for item in items]

@router.post("/portfolio")
async def add_portfolio_item(data: PortfolioItemCreate, db: Session = Depends(get_db)):
    """Add an item to the portfolio."""
    engine = PortfolioEngine(db)
    item = engine.add_item(data.model_dump())
    return PortfolioItemResponse.model_validate(item)

@router.put("/portfolio/{item_id}")
async def update_portfolio_item(item_id: int, data: PortfolioItemCreate, db: Session = Depends(get_db)):
    """Update a portfolio item."""
    engine = PortfolioEngine(db)
    item = engine.update_item(item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    return PortfolioItemResponse.model_validate(item)

@router.delete("/portfolio/{item_id}")
async def delete_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    """Remove a portfolio item (records a sell transaction)."""
    engine = PortfolioEngine(db)
    if not engine.remove_item(item_id):
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    return {"status": "removed"}

@router.post("/portfolio/{item_id}/sell")
async def sell_portfolio_item(item_id: int, quantity: int = Query(1, ge=1), 
                               sell_price: float = Query(..., gt=0),
                               db: Session = Depends(get_db)):
    """Sell (reduce quantity of) a portfolio item."""
    engine = PortfolioEngine(db)
    item = engine.sell_partial(item_id, quantity, sell_price)
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found or insufficient quantity")
    return PortfolioItemResponse.model_validate(item) if item else {"status": "sold_out"}

@router.get("/portfolio/summary")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """Get portfolio summary with P&L and allocation."""
    engine = PortfolioEngine(db)
    return engine.get_summary()

@router.post("/portfolio/refresh")
async def refresh_portfolio_prices(db: Session = Depends(get_db)):
    """Refresh current prices for all portfolio items from price history."""
    engine = PortfolioEngine(db)
    updated = engine.refresh_prices()
    return {"updated": updated}

@router.get("/portfolio/transactions")
async def get_portfolio_transactions(item_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Get transaction history."""
    engine = PortfolioEngine(db)
    txns = engine.get_transactions(item_id)
    return [TransactionResponse.model_validate(t) for t in txns]

# ========== Backtest Endpoints ==========

from app.services.backtest_engine import BacktestEngine

@router.get("/backtest/strategies")
async def get_backtest_strategies():
    """Get available backtesting strategies."""
    return {"strategies": BacktestEngine.get_strategies()}

@router.post("/backtest/run")
async def run_backtest(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Run a backtest on historical price data."""
    engine = BacktestEngine(db)
    result = engine.run_backtest(
        strategy=data.get("strategy", "buy_and_hold"),
        item_name=data.get("item_name", ""),
        source=data.get("source", "steam"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        initial_capital=data.get("initial_capital", 1000.0),
        parameters=data.get("parameters"),
    )
    return result

# ========== SSE Alerts Stream ==========

from fastapi.responses import StreamingResponse
import asyncio
import json

async def alert_stream_generator():
    """Generate SSE events for price alerts and bot activity."""
    while True:
        try:
            # Check watchlist alerts
            from app.services.bot_engine import get_bot_sync
            bot = get_bot_sync()
            alerts = await bot.check_watchlist()
            
            if alerts:
                for alert in alerts[:3]:
                    yield f"event: watchlist_alert\ndata: {json.dumps(alert)}\n\n"
            
            # Send bot heartbeat
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
