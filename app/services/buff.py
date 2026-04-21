import httpx
import re
import json
import time
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

BUFF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://buff.163.com/market/csgo",
}

class BuffScraper:
    def __init__(self):
        self.base_url = settings.BUFF_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=BUFF_HEADERS,
            follow_redirects=True,
        )
    
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search items on Buff163 marketplace."""
        try:
            url = f"{self.base_url}/api/market/goods"
            params = {
                "game": "csgo",
                "page_num": page,
                "page_size": min(page_size, 80),
                "search": keywords,
                "sort_by": "default",
                "_": int(time.time() * 1000),
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and data.get("data", {}).get("items"):
                    return data["data"]["items"]
            logger.warning(f"Buff search failed: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Buff search error: {e}")
            return []
    
    async def get_item_detail(self, goods_id: int) -> Optional[Dict[str, Any]]:
        """Fetch item detail from Buff."""
        try:
            url = f"{self.base_url}/api/market/goods/sell_order"
            params = {
                "game": "csgo",
                "goods_id": goods_id,
                "page_num": 1,
                "page_size": 20,
                "_": int(time.time() * 1000),
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok":
                    return data.get("data", {})
            logger.warning(f"Buff detail failed for {goods_id}: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Buff detail error: {e}")
            return None
    
    async def get_price_history(self, goods_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch price history for an item."""
        try:
            url = f"{self.base_url}/api/market/goods/price_history"
            params = {
                "game": "csgo",
                "goods_id": goods_id,
                "days": days,
                "_": int(time.time() * 1000),
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and data.get("data"):
                    return data["data"]
            logger.warning(f"Buff price history failed for {goods_id}: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Buff price history error: {e}")
            return []
    
    async def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Fetch market summary/stats."""
        try:
            url = f"{self.base_url}/api/market/goods"
            params = {
                "game": "csgo",
                "page_num": 1,
                "page_size": 10,
                "sort_by": "hot",
                "_": int(time.time() * 1000),
            }
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok":
                    return data.get("data", {})
            logger.warning(f"Buff market summary failed: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Buff market summary error: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()

# Singleton instance
buff_scraper = BuffScraper()
