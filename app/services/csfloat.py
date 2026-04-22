import httpx
import time
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings
from app.services._http_utils import async_retry, RateLimiter, http_error_message

settings = get_settings()
logger = logging.getLogger(__name__)

CSFLOAT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

class CSFloatScraper:
    """
    CSFloat API scraper.

    CSFloat provides public API endpoints for browsing listings.
    Key features: float values, stickers, paint seeds, buy orders.
    
    Public endpoints (no auth):
    - GET /listings?market_hash_name={name}&limit={n}
    - GET /listings/{id}
    """

    def __init__(self):
        self.base_url = settings.CSFLOAT_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=CSFLOAT_HEADERS,
            follow_redirects=True,
        )
        self._rate_limiter = RateLimiter(min_interval=0.8)
        self._cache = {}
        self._cache_ttl = 120  # 2 minutes

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def search_listings(self, market_hash_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search CSFloat listings by market hash name."""
        cache_key = f"csfloat:listings:{market_hash_name}:{limit}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached["time"] < self._cache_ttl):
            return cached["data"]

        await self._rate_limiter.acquire()
        params = {
            "market_hash_name": market_hash_name,
            "limit": min(limit, 50),
        }
        response = await self.client.get(f"{self.base_url}/listings", params=params)

        if response.status_code == 200:
            data = response.json()
            listings = data.get("data", []) if isinstance(data, dict) else []
            results = []
            for item in listings:
                item_data = item.get("item", {}) or {}
                results.append({
                    "id": item.get("id"),
                    "price": self._cents_to_currency(item.get("price")),
                    "created_at": item.get("created_at"),
                    "type": item.get("type"),  # buy_now, auction
                    "state": item.get("state"),  # listed, withdrawn, etc
                    "market_hash_name": item_data.get("market_hash_name", market_hash_name),
                    "float_value": item_data.get("float_value"),
                    "paint_seed": item_data.get("paint_seed"),
                    "paint_index": item_data.get("paint_index"),
                    "def_index": item_data.get("def_index"),
                    "stickers": item_data.get("stickers", []),
                    "rarity": item_data.get("rarity"),
                    "quality": item_data.get("quality"),
                    "image_url": item_data.get("icon_url"),
                    "inspect_link": item_data.get("inspect_link"),
                    "wear_name": item_data.get("wear_name"),
                    "is_souvenir": item_data.get("is_souvenir", False),
                    "is_stattrak": item_data.get("is_stattrak", False),
                    "source": "csfloat",
                })
            self._cache[cache_key] = {"data": results, "time": time.time()}
            logger.info(f"CSFloat search '{market_hash_name}': {len(results)} listings")
            return results

        logger.warning(http_error_message(response.status_code, "CSFloat"))
        return []

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def get_listing_detail(self, listing_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed info for a specific CSFloat listing."""
        await self._rate_limiter.acquire()
        response = await self.client.get(f"{self.base_url}/listings/{listing_id}")

        if response.status_code == 200:
            data = response.json()
            item_data = data.get("item", {}) or {}
            return {
                "id": data.get("id"),
                "price": self._cents_to_currency(data.get("price")),
                "created_at": data.get("created_at"),
                "type": data.get("type"),
                "state": data.get("state"),
                "seller": data.get("seller", {}).get("steam_id"),
                "market_hash_name": item_data.get("market_hash_name"),
                "float_value": item_data.get("float_value"),
                "paint_seed": item_data.get("paint_seed"),
                "paint_index": item_data.get("paint_index"),
                "def_index": item_data.get("def_index"),
                "stickers": item_data.get("stickers", []),
                "rarity": item_data.get("rarity"),
                "quality": item_data.get("quality"),
                "image_url": item_data.get("icon_url"),
                "inspect_link": item_data.get("inspect_link"),
                "wear_name": item_data.get("wear_name"),
                "is_souvenir": item_data.get("is_souvenir", False),
                "is_stattrak": item_data.get("is_stattrak", False),
                "source": "csfloat",
            }

        logger.warning(http_error_message(response.status_code, "CSFloat"))
        return None

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search CSFloat by keywords (maps to unified scraper interface)."""
        listings = await self.search_listings(keywords, limit=page_size)
        results = []
        for item in listings:
            results.append({
                "source": "csfloat",
                "external_id": str(item.get("id", "")),
                "name": item.get("market_hash_name", keywords),
                "price": item.get("price"),
                "image_url": item.get("image_url", ""),
                "hash_name": item.get("market_hash_name", ""),
                "exterior": item.get("wear_name", ""),
                "rarity": item.get("rarity", ""),
                "float_value": item.get("float_value"),
                "paint_seed": item.get("paint_seed"),
                "paint_index": item.get("paint_index"),
                "inspect_link": item.get("inspect_link"),
                "stickers": item.get("stickers", []),
                "lowest_price": item.get("price"),
            })
        return results

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def get_item_detail(self, market_hash_name: str) -> Optional[Dict[str, Any]]:
        """Get cheapest listing detail for an item (maps to unified interface)."""
        listings = await self.search_listings(market_hash_name, limit=1)
        if listings:
            l = listings[0]
            return {
                "source": "csfloat",
                "external_id": str(l.get("id", "")),
                "name": l.get("market_hash_name", market_hash_name),
                "price": l.get("price"),
                "image_url": l.get("image_url", ""),
                "hash_name": l.get("market_hash_name", ""),
                "exterior": l.get("wear_name", ""),
                "rarity": l.get("rarity", ""),
                "float_value": l.get("float_value"),
                "paint_seed": l.get("paint_seed"),
                "paint_index": l.get("paint_index"),
                "inspect_link": l.get("inspect_link"),
                "stickers": l.get("stickers", []),
                "lowest_price": l.get("price"),
            }
        return None

    def _cents_to_currency(self, cents: Optional[int]) -> Optional[float]:
        """Convert CSFloat cents to currency units."""
        if cents is None:
            return None
        return round(cents / 100, 2)

    async def close(self):
        await self.client.aclose()

# Singleton instance
csfloat_scraper = CSFloatScraper()
