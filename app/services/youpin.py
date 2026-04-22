import httpx
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings
from app.services._http_utils import async_retry, RateLimiter, http_error_message

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
    """
    Youpin (悠悠有品) scraper.

    Public endpoints (no auth needed):
    - Commodity detail by ID
    - Search tags / categories
    - Order delivery statistics

    Search requires authentication. The search_items method returns an
    empty list with a clear log message when auth is unavailable.
    """

    def __init__(self):
        self.base_url = settings.YOUPIN_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=YOUPIN_HEADERS,
            follow_redirects=True,
        )
        self._rate_limiter = RateLimiter(min_interval=1.0)

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_commodity_detail(self, commodity_id: int) -> Optional[Dict[str, Any]]:
        """Fetch detailed info for a specific commodity by ID."""
        await self._rate_limiter.acquire()
        url = f"{self.base_url}/api/commodity/Commodity/Detail"
        response = await self.client.get(url, params={"id": commodity_id})

        if response.status_code == 200:
            data = response.json()
            if data.get("Code") == 0 and data.get("Data"):
                d = data["Data"]
                return {
                    "source": "youpin",
                    "external_id": str(commodity_id),
                    "name": d.get("CommodityName", ""),
                    "price": d.get("Price"),
                    "image_url": d.get("ImgUrl", ""),
                    "hash_name": d.get("MarketHashName", ""),
                    "exterior": d.get("ExteriorName", ""),
                    "rarity": d.get("RarityName", ""),
                    "weapon_name": d.get("WeaponName", ""),
                    "lowest_price": d.get("LowestPrice"),
                    "lease_unit_price": d.get("LeaseUnitPrice"),
                    "lease_deposit": d.get("LeaseDeposit"),
                    "seller_name": d.get("UserNickName", ""),
                    "on_lease": d.get("OnLease", False),
                    "paint_seed": d.get("PaintSeed"),
                    "paint_index": d.get("PaintIndex"),
                    "abrade": d.get("Abrade"),
                    "inspect_link": d.get("InspectUrl", ""),
                }
            logger.warning(f"Youpin detail returned Code={data.get('Code')} for {commodity_id}")
            return None

        logger.warning(http_error_message(response.status_code, "Youpin"))
        return None

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_search_tags(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch search categories/filters."""
        await self._rate_limiter.acquire()
        url = f"{self.base_url}/api/youpin/pc/query/filter/getSearchTags"
        response = await self.client.get(url)

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0 and data.get("data"):
                return data["data"]
            return None

        logger.warning(http_error_message(response.status_code, "Youpin"))
        return None

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_order_deliver_stats(self) -> Optional[Dict[str, Any]]:
        """Fetch order delivery statistics (public endpoint)."""
        await self._rate_limiter.acquire()
        url = f"{self.base_url}/api/trade/Order/OrderDeliverStatistics"
        response = await self.client.get(url)

        if response.status_code == 200:
            data = response.json()
            if data.get("Code") == 0 and data.get("Data"):
                return data["Data"]
            return None

        logger.warning(http_error_message(response.status_code, "Youpin"))
        return None

    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        Search for items by keywords.
        NOTE: Youpin search requires authentication. This returns empty results
        with a clear log message. To enable search, add session cookies to
        the client headers in youpin.py.
        """
        logger.info(
            f"Youpin search for '{keywords}' skipped: authentication required. "
            "Add session cookies to app/services/youpin.py to enable."
        )
        return []

    async def close(self):
        await self.client.aclose()

# Singleton instance
youpin_scraper = YoupinScraper()
