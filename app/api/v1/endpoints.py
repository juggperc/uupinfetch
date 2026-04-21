from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from app.db.database import get_db
from app.models.models import Item, PriceHistory
from app.schemas.schemas import (
    ItemResponse, ItemDetailResponse, SearchResponse,
    HealthResponse, ScrapeStatus, PriceHistoryResponse
)
from app.services.youpin import youpin_scraper
from app.services.buff import buff_scraper
from app.services.steam import steam_scraper
from app.services.scraper import background_scraper
from app.core.config import get_settings
from app.core.auth import require_api_key
from datetime import datetime

router = APIRouter(prefix="/api/v1")
settings = get_settings()

# Auth dependencies
optional_auth = Depends(require_api_key)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        youpin_enabled=settings.ENABLE_YOUPIN,
        buff_enabled=settings.ENABLE_BUFF,
    )

@router.get("/items/search", response_model=SearchResponse)
async def search_items(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    source: Optional[str] = Query("all", description="Data source: all, steam, youpin, buff"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user = Depends(require_api_key),
):
    """Search for CS2 items across marketplaces. Requires API key."""
    all_items = []
    
    if source in ("all", "steam"):
        steam_results = await steam_scraper.search_items(q, page, page_size)
        for item_data in steam_results:
            all_items.append(item_data)
    
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
    
    db_items = db.query(Item).filter(Item.name.contains(q)).offset((page - 1) * page_size).limit(page_size).all()
    total = len(all_items) + len(db_items)
    
    return SearchResponse(
        items=all_items + [ItemResponse.model_validate(i) for i in db_items],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/items/popular")
async def get_popular_items(limit: int = Query(8, ge=1, le=20)):
    """Get popular items from database. No auth required."""
    items = await background_scraper.get_popular_items(limit)
    return {
        "items": [ItemResponse.model_validate(i) for i in items],
        "total": len(items),
    }

@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(
    item_id: str,
    source: str = Query("steam", description="Data source"),
    db: Session = Depends(get_db),
    user = Depends(require_api_key),
):
    """Get detailed info for a specific item. Requires API key."""
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
    else:
        raise HTTPException(status_code=400, detail="Invalid source")
    
    return ItemDetailResponse(
        item=ItemResponse(**item),
        price_history=[PriceHistoryResponse(**h) for h in price_history],
        related_items=related_items,
    )

@router.get("/items/{item_id}/price-history")
async def get_price_history(
    item_id: str,
    source: str = Query("buff", description="Data source"),
    days: int = Query(7, ge=1, le=365),
    user = Depends(require_api_key),
):
    """Get price history for an item. Requires API key."""
    if source == "buff" and settings.ENABLE_BUFF:
        history = await buff_scraper.get_price_history(int(item_id), days=days)
        return {"item_id": item_id, "source": source, "days": days, "data": history}
    elif source == "youpin" and settings.ENABLE_YOUPIN:
        return {"item_id": item_id, "source": source, "days": days, "data": [], "note": "Youpin price history requires authentication"}
    elif source == "steam":
        return {"item_id": item_id, "source": source, "days": days, "data": [], "note": "Steam price history not yet implemented"}
    else:
        raise HTTPException(status_code=400, detail="Invalid source")

@router.get("/categories")
async def get_categories():
    """Get item categories/filters. No auth required."""
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
    """Get market summary statistics. No auth required."""
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
    
    return summary

@router.get("/scrape/status", response_model=ScrapeStatus)
async def get_scrape_status():
    """Get scraper status. No auth required."""
    return ScrapeStatus(
        status="running" if background_scraper.is_running else "idle",
        items_scraped=0,
    )
