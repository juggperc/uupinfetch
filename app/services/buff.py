import httpx
import time
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings
from app.services._http_utils import async_retry, RateLimiter, http_error_message

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
    """Buff163 scraper. Requires authentication for search and price history."""

    def __init__(self):
        self.base_url = settings.BUFF_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=BUFF_HEADERS,
            follow_redirects=True,
        )
        self._rate_limiter = RateLimiter(min_interval=1.0)
        self._auth_required = False

    def _check_auth(self, data: dict) -> bool:
        """Check if Buff response indicates auth is required."""
        code = data.get("code")
        if code == "LoginRequired" or code == "NotLogin" or code == 401:
            self._auth_required = True
            return False
        return True

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search items on Buff163 marketplace. Returns empty list if auth is required."""
        if self._auth_required:
            logger.info("Buff search skipped: authentication required")
            return []

        await self._rate_limiter.acquire()
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
            if not self._check_auth(data):
                logger.warning("Buff search requires authentication. Add session cookies to buff.py")
                return []
            if data.get("code") == "Ok" and data.get("data", {}).get("items"):
                return data["data"]["items"]
            logger.info(f"Buff search returned empty for '{keywords}' (code={data.get('code')})")
            return []

        logger.warning(http_error_message(response.status_code, "Buff"))
        return []

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_item_detail(self, goods_id: int) -> Optional[Dict[str, Any]]:
        """Fetch item detail from Buff."""
        if self._auth_required:
            return None

        await self._rate_limiter.acquire()
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
            if not self._check_auth(data):
                return None
            if data.get("code") == "Ok":
                return data.get("data", {})
            return None

        logger.warning(http_error_message(response.status_code, "Buff"))
        return None

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_price_history(self, goods_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch price history for an item."""
        if self._auth_required:
            return []

        await self._rate_limiter.acquire()
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
            if not self._check_auth(data):
                return []
            if data.get("code") == "Ok" and data.get("data"):
                return data["data"]
            return []

        logger.warning(http_error_message(response.status_code, "Buff"))
        return []

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Fetch market summary/stats."""
        if self._auth_required:
            return None

        await self._rate_limiter.acquire()
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
            if not self._check_auth(data):
                return None
            if data.get("code") == "Ok":
                return data.get("data", {})
            return None

        logger.warning(http_error_message(response.status_code, "Buff"))
        return None

    async def close(self):
        await self.client.aclose()

# Singleton instance
buff_scraper = BuffScraper()
