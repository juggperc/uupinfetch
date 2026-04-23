"""
Search and item detail API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import logging
from datetime import datetime
from app.db.database import get_db
from app.models.models import Item, PriceHistory
from app.schemas.schemas import ItemResponse, ItemDetailResponse, SearchResponse, PriceHistoryResponse
from app.services.youpin import youpin_scraper
from app.services.buff import buff_scraper
from app.services.steam import steam_scraper
from app.services.skinport import skinport_scraper
from app.services.csfloat import csfloat_scraper
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/items/search", response_model=SearchResponse)
async def search_items(
    q: str = Query(..., min_length=1, max_length=200),
    source: str = Query("all", description="Data source: all, steam, buff, youpin, skinport"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
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
    items = db.query(Item).filter(Item.price.isnot(None)).order_by(Item.updated_at.desc()).limit(limit).all()
    return {
        "items": [ItemResponse.model_validate(item) for item in items],
        "total": len(items),
    }

@router.get("/items/compare")
async def compare_item_prices(q: str = Query(..., description="Item name to compare across sources")):
    results = {}
    
    async def fetch_steam():
        try:
            items = await steam_scraper.search_items(q, page=1, page_size=3)
            if items:
                results["steam"] = {"price": items[0].get("price"), "name": items[0].get("name")}
        except Exception:
            pass
    
    async def fetch_buff():
        if not settings.ENABLE_BUFF:
            return
        try:
            items = await buff_scraper.search_items(q, page=1, page_size=3)
            if items:
                results["buff"] = {"price": items[0].get("sell_min_price"), "name": items[0].get("name")}
        except Exception:
            pass
    
    async def fetch_youpin():
        if not settings.ENABLE_YOUPIN:
            return
        try:
            items = await youpin_scraper.search_items(q, page=1, page_size=3)
            if items:
                results["youpin"] = {"price": items[0].get("price"), "name": items[0].get("name")}
        except Exception:
            pass
    
    async def fetch_skinport():
        if not settings.ENABLE_SKINPORT:
            return
        try:
            items = await skinport_scraper.search_items(q, page_size=3)
            if items:
                results["skinport"] = {"price": items[0].get("price"), "name": items[0].get("name")}
        except Exception:
            pass
    
    await asyncio.gather(fetch_steam(), fetch_buff(), fetch_youpin(), fetch_skinport())
    return {"query": q, "sources": results}

@router.get("/items/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(
    item_id: str,
    source: str = Query("steam", description="Data source"),
    db: Session = Depends(get_db),
):
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

@router.get("/scrape/status")
async def get_scrape_status():
    from app.services.scraper import background_scraper
    from app.schemas.schemas import ScrapeStatus
    return ScrapeStatus(
        status="running" if background_scraper.is_running else "idle",
        items_scraped=0,
    )
