import httpx
import time
from typing import Optional, Dict, Any, List
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

SKINPORT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "br",  # Required by Skinport API
}

class SkinportScraper:
    def __init__(self):
        self.base_url = settings.SKINPORT_BASE_URL
        self.client = httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT,
            headers=SKINPORT_HEADERS,
            follow_redirects=True,
        )
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 300  # 5 minutes (matches Skinport API cache)
    
    async def _fetch_all_items(self, currency: str = "CNY", tradable: int = 0) -> List[Dict[str, Any]]:
        """Fetch the full Skinport item catalog. Cached for 5 minutes."""
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cache
        
        try:
            params = {
                "app_id": 730,
                "currency": currency,
                "tradable": tradable,
            }
            response = await self.client.get(
                f"{self.base_url}/items",
                params=params,
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self._cache = data
                    self._cache_time = now
                    logger.info(f"Skinport catalog fetched: {len(data)} items")
                    return data
                else:
                    logger.warning(f"Skinport unexpected response type: {type(data)}")
            else:
                logger.warning(f"Skinport items failed: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            logger.error(f"Skinport fetch error: {e}")
        
        return self._cache or []
    
    def _extract_exterior(self, name: str) -> str:
        """Extract exterior/wear from item name."""
        exteriors = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
        for ext in exteriors:
            if ext in name:
                return ext
        return ""
    
    def _extract_rarity(self, name: str) -> str:
        """Infer rarity from item name patterns."""
        if "Case" in name:
            return "Container"
        if "Sticker" in name or "Capsule" in name:
            return "Sticker"
        if "Gloves" in name or "Hand Wraps" in name:
            return "Gloves"
        if "Knife" in name or "Bayonet" in name or "Karambit" in name or "Daggers" in name:
            return "Knife"
        return ""
    
    def _build_image_url(self, market_hash_name: str) -> str:
        """Build a Steam community image URL from market hash name."""
        # Skinport doesn't provide image URLs in the items endpoint,
        # so we construct a Steam CDN URL.
        return f"https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvFi08rdQ1Bkag1oG-6mtlMxhaKecz8T7dCJloWZk67nMuqIqT8J7pRz3L2W8d2kiQax_0M5ZD2GcIGVJlQ7YQzR-QW3wO7t1pO6vM7AnSd9-n51FVSY/360fx360f"
    
    async def search_items(self, keywords: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search Skinport items by keywords. Filters client-side from cached catalog."""
        all_items = await self._fetch_all_items()
        if not all_items:
            return []
        
        query_lower = keywords.lower()
        matched = []
        
        for item in all_items:
            name = item.get("market_hash_name", "")
            if query_lower in name.lower():
                price = item.get("min_price") or item.get("suggested_price")
                if price is None:
                    continue
                
                matched.append({
                    "source": "skinport",
                    "external_id": name,
                    "name": name,
                    "price": float(price),
                    "image_url": self._build_image_url(name),
                    "hash_name": name,
                    "exterior": self._extract_exterior(name),
                    "rarity": self._extract_rarity(name),
                    "lowest_price": float(price) if price else None,
                    "suggested_price": item.get("suggested_price"),
                    "mean_price": item.get("mean_price"),
                    "median_price": item.get("median_price"),
                    "quantity": item.get("quantity", 0),
                    "item_page": item.get("item_page", ""),
                })
        
        # Client-side pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = matched[start:end]
        
        logger.info(f"Skinport search '{keywords}': {len(matched)} matched, returning {len(paginated)}")
        return paginated
    
    async def get_item_detail(self, market_hash_name: str) -> Optional[Dict[str, Any]]:
        """Get detail for a specific item by market_hash_name."""
        all_items = await self._fetch_all_items()
        
        for item in all_items:
            if item.get("market_hash_name") == market_hash_name:
                price = item.get("min_price") or item.get("suggested_price")
                return {
                    "source": "skinport",
                    "external_id": market_hash_name,
                    "name": market_hash_name,
                    "price": float(price) if price else None,
                    "image_url": self._build_image_url(market_hash_name),
                    "hash_name": market_hash_name,
                    "exterior": self._extract_exterior(market_hash_name),
                    "rarity": self._extract_rarity(market_hash_name),
                    "lowest_price": float(price) if price else None,
                    "suggested_price": item.get("suggested_price"),
                    "mean_price": item.get("mean_price"),
                    "median_price": item.get("median_price"),
                    "quantity": item.get("quantity", 0),
                    "item_page": item.get("item_page", ""),
                }
        return None
    
    async def close(self):
        await self.client.aclose()

# Singleton instance
skinport_scraper = SkinportScraper()
