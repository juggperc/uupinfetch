from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
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
    """Get 挂刀 (Steam balance conversion) ratios. Lower = better."""
    if refresh or not ratio_engine._last_results:
        await ratio_engine.scan_ratios(max_items=80)
    
    results = ratio_engine.get_best_ratios(
        source=source, limit=limit, max_price=max_price, min_volume=min_volume
    )
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

@router.get("/items/search", response_model=SearchResponse)
async def search_items(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    source: Optional[str] = Query("all", description="Data source: all, steam, youpin, buff, skinport"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search for CS2 items across marketplaces."""
    all_items = []
    
    if source in ("all", "steam"):
        steam_results = await steam_scraper.search_items(q, page, page_size)
        for item_data in steam_results:
            all_items.append(item_data)
        if source == "all" and not steam_results:
            logger.info("Steam search returned no results (possible rate limit)")
    
    if source in ("all", "buff") and settings.ENABLE_BUFF:
        buff_results = await buff_scraper.search_items(q, page, page_size)
        for item_data in buff_results:
            all_items.append({
                "source": "buff",
                "external_id": str(item_data.get("id", "")),
                "name": item_data.get("name", ""),
                "price": item_data.get("sell_min_price"),
                "image_url": item_data.get("goods_info", {}).get("icon_url", ""),
                "exterior": item_data.get("goods_info", {}).get("info", {}).get("tags", {}).get("exterior", {}).get("localized_name", ""),
                "rarity": item_data.get("goods_info", {}).get("info", {}).get("tags", {}).get("rarity", {}).get("localized_name", ""),
                "weapon_name": item_data.get("goods_info", {}).get("info", {}).get("tags", {}).get("weapon", {}).get("localized_name", ""),
                "hash_name": item_data.get("market_hash_name", ""),
                "lowest_price": item_data.get("sell_min_price"),
            })
    
    if source in ("all", "youpin") and settings.ENABLE_YOUPIN:
        youpin_results = await youpin_scraper.search_items(q, page, page_size)
        for item_data in youpin_results:
            all_items.append(item_data)
    
    if source in ("all", "skinport") and settings.ENABLE_SKINPORT:
        skinport_results = await skinport_scraper.search_items(q, page, page_size)
        for item_data in skinport_results:
            all_items.append(item_data)
    
    if source in ("all", "csfloat") and settings.ENABLE_CSFLOAT:
        try:
            csfloat_results = await csfloat_scraper.search_items(q, page, page_size)
            for item_data in csfloat_results:
                all_items.append(item_data)
        except Exception as e:
            logger.debug(f"CSFloat search error: {e}")
    
    db_total = db.query(Item).filter(Item.name.contains(q)).count()
    db_items = db.query(Item).filter(Item.name.contains(q)).offset((page - 1) * page_size).limit(page_size).all()
    total = len(all_items) + db_total
    
    return SearchResponse(
        items=all_items + [ItemResponse.model_validate(i) for i in db_items],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/items/popular")
async def get_popular_items(limit: int = Query(8, ge=1, le=20)):
    """Get popular items from database."""
    items = await background_scraper.get_popular_items(limit)
    return {
        "items": [ItemResponse.model_validate(i) for i in items],
        "total": len(items),
    }

@router.get("/items/{item_id}/price-history")
async def get_price_history(
    item_id: str,
    source: str = Query("buff", description="Data source"),
    days: int = Query(7, ge=1, le=365),
):
    """Get price history for an item."""
    if source == "buff" and settings.ENABLE_BUFF:
        history = await buff_scraper.get_price_history(int(item_id), days=days)
        return {"item_id": item_id, "source": source, "days": days, "data": history}
    elif source == "youpin" and settings.ENABLE_YOUPIN:
        return {"item_id": item_id, "source": source, "days": days, "data": [], "note": "Youpin price history requires authentication"}
    elif source == "steam":
        return {"item_id": item_id, "source": source, "days": days, "data": [], "note": "Steam price history not yet implemented"}
    elif source == "skinport" and settings.ENABLE_SKINPORT:
        return {"item_id": item_id, "source": source, "days": days, "data": [], "note": "Skinport does not provide historical price data via public API"}
    else:
        raise HTTPException(status_code=400, detail="Invalid source")

@router.get("/items/{item_id}/compare")
async def compare_item_prices(
    item_id: str,
    name: Optional[str] = Query(None, description="Item name for cross-source matching"),
):
    """Get prices for an item across all enabled sources."""
    results = {
        "steam": {"price": None, "url": None, "available": False},
        "buff": {"price": None, "url": None, "available": False},
        "youpin": {"price": None, "url": None, "available": False},
        "skinport": {"price": None, "url": None, "available": False},
        "csfloat": {"price": None, "url": None, "available": False},
    }

    # Use name for searching if provided, otherwise use item_id
    search_term = name or item_id

    # Steam
    try:
        steam_price = await steam_scraper.get_price_overview(item_id)
        if steam_price and steam_price.get("lowest_price"):
            results["steam"] = {
                "price": steam_price.get("lowest_price"),
                "url": f"https://steamcommunity.com/market/listings/730/{item_id}",
                "available": True,
            }
    except Exception as e:
        logger.warning(f"Steam compare failed: {e}")

    # Buff (requires auth, usually fails but try)
    if settings.ENABLE_BUFF:
        try:
            buff_search = await buff_scraper.search_items(search_term, page_size=5)
            if buff_search:
                match = buff_search[0]
                price = match.get("sell_min_price")
                goods_id = match.get("id")
                if price:
                    results["buff"] = {
                        "price": price,
                        "url": f"https://buff.163.com/goods/{goods_id}" if goods_id else None,
                        "available": True,
                    }
        except Exception as e:
            logger.warning(f"Buff compare failed: {e}")

    # Youpin (requires auth for search)
    if settings.ENABLE_YOUPIN:
        try:
            detail = await youpin_scraper.get_commodity_detail(int(item_id))
            if detail and detail.get("Price"):
                results["youpin"] = {
                    "price": detail.get("Price"),
                    "url": None,
                    "available": True,
                }
        except Exception:
            pass

    # Skinport
    if settings.ENABLE_SKINPORT:
        try:
            skinport_item = await skinport_scraper.get_item_detail(item_id)
            if skinport_item and skinport_item.get("price"):
                results["skinport"] = {
                    "price": skinport_item.get("price"),
                    "url": skinport_item.get("item_page"),
                    "available": True,
                }
        except Exception as e:
            logger.warning(f"Skinport compare failed: {e}")

    # CSFloat
    if settings.ENABLE_CSFLOAT:
        try:
            csfloat_item = await csfloat_scraper.get_item_detail(item_id)
            if csfloat_item and csfloat_item.get("price"):
                results["csfloat"] = {
                    "price": csfloat_item.get("price"),
                    "url": f"https://csfloat.com/search?market_hash_name={item_id}",
                    "available": True,
                }
        except Exception as e:
            logger.warning(f"CSFloat compare failed: {e}")

    return {"item_id": item_id, "name": search_term, "sources": results}

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

@router.get("/scrape/status", response_model=ScrapeStatus)
async def get_scrape_status():
    """Get scraper status."""
    return ScrapeStatus(
        status="running" if background_scraper.is_running else "idle",
        items_scraped=0,
    )
