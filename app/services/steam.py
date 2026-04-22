import httpx
import time
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings
from app.services._http_utils import async_retry, RateLimiter, http_error_message

settings = get_settings()
logger = logging.getLogger(__name__)

STEAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://steamcommunity.com/market/search?appid=730",
}

class SteamScraper:
    def __init__(self):
        self.base_url = "https://steamcommunity.com/market"
        self.api_url = "https://steamcommunity.com/market/search/render"
        self.price_url = "https://steamcommunity.com/market/priceoverview"
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=STEAM_HEADERS,
            follow_redirects=True,
        )
        self._rate_limiter = RateLimiter(min_interval=1.5)

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
        """Search items on Steam Community Market."""
        await self._rate_limiter.acquire()
        start = (page - 1) * page_size
        params = {
            "query": keywords,
            "start": start,
            "count": page_size,
            "search_descriptions": 0,
            "sort_column": "popular",
            "sort_dir": "desc",
            "appid": 730,
            "norender": 1,
        }
        response = await self.client.get(self.api_url, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("results"):
                items = []
                for result in data["results"]:
                    asset = result.get("asset_description", {}) or {}
                    icon_url = asset.get("icon_url", "")
                    items.append({
                        "source": "steam",
                        "external_id": result.get("hash_name", ""),
                        "name": result.get("name", ""),
                        "hash_name": result.get("hash_name", ""),
                        "price": self._parse_price(result.get("sell_price_text", "")),
                        "image_url": f"https://steamcommunity-a.akamaihd.net/economy/image/{icon_url}" if icon_url else "",
                        "exterior": self._extract_exterior(result.get("name", "")),
                        "rarity": asset.get("type", ""),
                        "volume": result.get("sell_listings", 0),
                        "steam_market_url": f"https://steamcommunity.com/market/listings/730/{result.get('hash_name', '')}",
                    })
                logger.info(f"Steam search found {len(items)} items for '{keywords}'")
                return items
            logger.warning(f"Steam search returned empty results for '{keywords}'")
            return []

        logger.warning(http_error_message(response.status_code, "Steam"))
        return []

    @async_retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
    async def get_price_overview(self, market_hash_name: str) -> Optional[Dict[str, Any]]:
        """Get price overview for an item."""
        await self._rate_limiter.acquire()
        params = {
            "country": "CN",
            "currency": 23,  # CNY
            "appid": 730,
            "market_hash_name": market_hash_name,
        }
        response = await self.client.get(self.price_url, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return {
                    "lowest_price": self._parse_price(data.get("lowest_price", "")),
                    "median_price": self._parse_price(data.get("median_price", "")),
                    "volume": data.get("volume", 0),
                }
            logger.warning(f"Steam price overview returned success=false for {market_hash_name}")
            return None

        logger.warning(http_error_message(response.status_code, "Steam"))
        return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price text to float. Handles ¥, $, €, commas, and prefixes like 'Starting at:'."""
        if not price_text:
            return None
        try:
            cleaned = str(price_text)
            for prefix in ["Starting at", "starting at", "About", "about", ":"]:
                cleaned = cleaned.replace(prefix, "")
            for sym in ["¥", "$", "€", "£", ",", " ", "\xa0"]:
                cleaned = cleaned.replace(sym, "")
            cleaned = cleaned.strip()
            if not cleaned:
                return None
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _extract_exterior(self, name: str) -> str:
        """Extract exterior/wear from item name."""
        exteriors = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
        for ext in exteriors:
            if ext in name:
                return ext
        return ""

    async def close(self):
        await self.client.aclose()

# Singleton instance
steam_scraper = SteamScraper()
