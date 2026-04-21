import httpx
import asyncio
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

YOUPIN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.youpin898.com",
    "Referer": "https://www.youpin898.com/",
    "Content-Type": "application/json",
}

class YoupinScraper:
    def __init__(self):
        self.base_url = settings.YOUPIN_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=YOUPIN_HEADERS,
            follow_redirects=True,
        )
    
    async def get_commodity_detail(self, commodity_id: int) -> Optional[Dict[str, Any]]:
        """Fetch detailed info for a specific commodity by ID."""
        try:
            url = f"{self.base_url}/api/commodity/Commodity/Detail"
            response = await self.client.get(url, params={"id": commodity_id})
            
            if response.status_code == 200:
                data = response.json()
                if data.get("Code") == 0 and data.get("Data"):
                    return data["Data"]
            logger.warning(f"Youpin detail failed for {commodity_id}: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Youpin detail error: {e}")
            return None
    
    async def get_search_tags(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch search categories/filters."""
        try:
            url = f"{self.base_url}/api/youpin/pc/query/filter/getSearchTags"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0 and data.get("data"):
                    return data["data"]
            logger.warning(f"Youpin tags failed: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Youpin tags error: {e}")
            return None
    
    async def get_order_deliver_stats(self) -> Optional[Dict[str, Any]]:
        """Fetch order delivery statistics (public endpoint)."""
        try:
            url = f"{self.base_url}/api/trade/Order/OrderDeliverStatistics"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("Code") == 0 and data.get("Data"):
                    return data["Data"]
            logger.warning(f"Youpin stats failed: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Youpin stats error: {e}")
            return None
    
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        Search for items by keywords.
        NOTE: Youpin search requires authentication. This is a placeholder
        that returns empty results. Users can extend with auth tokens.
        """
        logger.info(f"Youpin search for '{keywords}' requires auth")
        return []
    
    async def close(self):
        await self.client.aclose()

# Singleton instance
youpin_scraper = YoupinScraper()
