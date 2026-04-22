"""
挂刀 (Steam Balance Ratio) Engine.

Tracks the ratio between Steam Community Market prices and third-party
marketplace prices. Lower ratio = better deal for converting Steam wallet
to real cash.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.services.steam import steam_scraper
from app.services.buff import buff_scraper
from app.services.youpin import youpin_scraper
from app.services.skinport import skinport_scraper
from app.services.market_fees import calculate_steam_ratio, ratio_grade, ratio_grade_zh, net_revenue
from app.core.config import get_settings
from app.db.database import SessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)

# Items that are commonly used for 挂刀 (high volume, stable prices)
POPULAR_RATIO_ITEMS = [
    "CS:GO Weapon Case",
    "CS:GO Weapon Case 2",
    "CS:GO Weapon Case 3",
    "Operation Bravo Case",
    "Operation Phoenix Weapon Case",
    "Operation Breakout Weapon Case",
    "Operation Vanguard Weapon Case",
    "Chroma Case",
    "Chroma 2 Case",
    "Chroma 3 Case",
    "eSports 2013 Case",
    "eSports 2013 Winter Case",
    "eSports 2014 Summer Case",
    "Huntsman Weapon Case",
    "Shadow Case",
    "Falchion Case",
    "Revolver Case",
    "Operation Wildfire Case",
    "Gamma Case",
    "Gamma 2 Case",
    "Glove Case",
    "Spectrum Case",
    "Spectrum 2 Case",
    "Clutch Case",
    "Horizon Case",
    "Danger Zone Case",
    "Prisma Case",
    "Prisma 2 Case",
    "Shattered Web Case",
    "Fracture Case",
    "Operation Broken Fang Case",
    "Snakebite Case",
    "Operation Riptide Case",
    "Dreams & Nightmares Case",
    "Recoil Case",
    "Revolution Case",
    "Kilowatt Case",
    "Sticker | Copenhagen 2024 Contenders",
    "Sticker | Copenhagen 2024 Legends",
    "Sticker | Copenhagen 2024 Challengers",
    "Sticker | Paris 2023 Contenders",
    "Sticker | Paris 2023 Legends",
    "Sticker | Paris 2023 Challengers",
    "AK-47 | Redline (Field-Tested)",
    "AK-47 | Redline (Minimal Wear)",
    "M4A4 | Dragon King (Field-Tested)",
    "M4A4 | Dragon King (Minimal Wear)",
    "AWP | Hyper Beast (Field-Tested)",
    "AWP | Hyper Beast (Minimal Wear)",
    "Glock-18 | Water Elemental (Field-Tested)",
    "Glock-18 | Water Elemental (Minimal Wear)",
    "USP-S | Kill Confirmed (Field-Tested)",
    "USP-S | Kill Confirmed (Minimal Wear)",
    "Desert Eagle | Conspiracy (Factory New)",
    "Desert Eagle | Conspiracy (Minimal Wear)",
    "MP9 | Wild Lily (Factory New)",
    "MAC-10 | Neon Rider (Factory New)",
    "SSG 08 | Dragonfire (Factory New)",
    "AK-47 | Uncharted (Factory New)",
    "M4A1-S | Player Two (Field-Tested)",
]


@dataclass
class RatioEntry:
    """A single ratio comparison entry."""
    item_name: str
    steam_price: Optional[float]
    steam_volume: Optional[int]
    buff_price: Optional[float]
    youpin_price: Optional[float]
    skinport_price: Optional[float]
    csfloat_price: Optional[float]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Calculate ratios for each marketplace
        for source in ["buff", "youpin", "skinport", "csfloat"]:
            price = d.get(f"{source}_price")
            if self.steam_price and price and self.steam_price > 0:
                ratio_data = calculate_steam_ratio(self.steam_price, price, source)
                d[f"{source}_ratio"] = ratio_data["effective_ratio"]
                d[f"{source}_net_ratio"] = ratio_data["net_ratio"]
                d[f"{source}_grade"] = ratio_grade(ratio_data["effective_ratio"])
                d[f"{source}_grade_zh"] = ratio_grade_zh(ratio_data["effective_ratio"])
            else:
                d[f"{source}_ratio"] = None
                d[f"{source}_net_ratio"] = None
                d[f"{source}_grade"] = None
                d[f"{source}_grade_zh"] = None
        return d


class RatioEngine:
    """Engine for calculating and tracking Steam balance conversion ratios."""

    def __init__(self):
        self._last_results: List[Dict[str, Any]] = []
        self._last_update: Optional[str] = None

    async def scan_ratios(self, items: Optional[List[str]] = None,
                          max_items: int = 50) -> List[Dict[str, Any]]:
        """
        Scan ratios for a list of items concurrently.
        If items is None, uses POPULAR_RATIO_ITEMS.
        """
        if items is None:
            items = POPULAR_RATIO_ITEMS[:max_items]
        else:
            items = items[:max_items]

        logger.info(f"Scanning ratios for {len(items)} items concurrently...")

        semaphore = asyncio.Semaphore(6)  # Limit concurrent API calls

        async def bounded_scan(item_name: str):
            async with semaphore:
                try:
                    entry = await self._scan_single_item(item_name)
                    if entry:
                        return entry.to_dict()
                except Exception as e:
                    logger.debug(f"Ratio scan failed for {item_name}: {e}")
                return None

        tasks = [bounded_scan(name) for name in items]
        raw_results = await asyncio.gather(*tasks)
        results = [r for r in raw_results if r is not None]

        # Sort by best (lowest) Buff ratio as primary metric
        results.sort(key=lambda x: (x.get("buff_ratio") or 999))

        self._last_results = results
        self._last_update = datetime.now(timezone.utc).isoformat()
        logger.info(f"Ratio scan complete. {len(results)} items tracked.")
        return results

    async def _scan_single_item(self, item_name: str) -> Optional[RatioEntry]:
        """Fetch prices from all sources for a single item."""
        steam_price = None
        steam_volume = None
        buff_price = None
        youpin_price = None
        skinport_price = None
        csfloat_price = None

        # Steam price (highest priority for ratio calc)
        try:
            steam_data = await steam_scraper.get_price_overview(item_name)
            if steam_data:
                steam_price = steam_data.get("lowest_price")
                steam_volume = steam_data.get("volume")
        except Exception as e:
            logger.debug(f"Steam price fetch failed for {item_name}: {e}")

        # Skip early if no Steam price — no point fetching third-party prices
        if not steam_price:
            return None

        # Fetch third-party prices concurrently
        async def fetch_buff():
            nonlocal buff_price
            if settings.ENABLE_BUFF:
                try:
                    buff_results = await buff_scraper.search_items(item_name, page_size=3)
                    if buff_results:
                        buff_price = buff_results[0].get("sell_min_price")
                except Exception:
                    pass

        async def fetch_youpin():
            nonlocal youpin_price
            if settings.ENABLE_YOUPIN:
                try:
                    youpin_results = await youpin_scraper.search_items(item_name, page_size=3)
                    if youpin_results:
                        youpin_price = youpin_results[0].get("price")
                except Exception:
                    pass

        async def fetch_skinport():
            nonlocal skinport_price
            if settings.ENABLE_SKINPORT:
                try:
                    skinport_results = await skinport_scraper.search_items(item_name, page_size=3)
                    if skinport_results:
                        skinport_price = skinport_results[0].get("price")
                except Exception:
                    pass

        async def fetch_csfloat():
            nonlocal csfloat_price
            if settings.ENABLE_CSFLOAT:
                try:
                    from app.services.csfloat import csfloat_scraper
                    csfloat_results = await csfloat_scraper.search_items(item_name, page_size=3)
                    if csfloat_results:
                        csfloat_price = csfloat_results[0].get("price")
                except Exception:
                    pass

        await asyncio.gather(
            fetch_buff(), fetch_youpin(), fetch_skinport(), fetch_csfloat(),
            return_exceptions=True
        )

        return RatioEntry(
            item_name=item_name,
            steam_price=steam_price,
            steam_volume=steam_volume,
            buff_price=buff_price,
            youpin_price=youpin_price,
            skinport_price=skinport_price,
            csfloat_price=csfloat_price,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_best_ratios(self, source: str = "buff", limit: int = 20,
                        max_price: Optional[float] = None,
                        min_volume: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get best ratios from last scan, filtered."""
        results = self._last_results.copy()

        # Filter by price
        if max_price is not None:
            results = [r for r in results if (r.get("steam_price") or 0) <= max_price]

        # Filter by volume
        if min_volume is not None:
            results = [r for r in results if (r.get("steam_volume") or 0) >= min_volume]

        # Sort by ratio (ascending = best)
        ratio_key = f"{source}_ratio"
        results.sort(key=lambda x: x.get(ratio_key) or 999)

        return results[:limit]

    async def get_best_ratios_from_db(self, source: str = "buff", limit: int = 20,
                                       max_price: Optional[float] = None,
                                       min_volume: Optional[int] = None) -> List[Dict[str, Any]]:
        """Build ratio results from the latest DB snapshot (fast fallback when cache is cold).
        Returns demo data if DB is empty so the UI is never blank."""
        from sqlalchemy import func
        from app.models.models import RatioHistory
        
        db = SessionLocal()
        try:
            subq = db.query(
                RatioHistory.item_name,
                func.max(RatioHistory.recorded_at).label("max_date")
            ).group_by(RatioHistory.item_name).subquery()
            
            rows = db.query(RatioHistory).join(
                subq,
                (RatioHistory.item_name == subq.c.item_name) &
                (RatioHistory.recorded_at == subq.c.max_date)
            ).all()
            
            results = []
            for row in rows:
                steam_price = row.steam_price
                tp_price = getattr(row, f"{source}_price", None)
                tp_ratio = getattr(row, f"{source}_ratio", None)
                
                if not steam_price:
                    continue
                if max_price is not None and steam_price > max_price:
                    continue
                if min_volume is not None and (row.steam_volume or 0) < min_volume:
                    continue
                
                grade = None
                grade_zh = None
                if tp_ratio is not None:
                    grade = ratio_grade(tp_ratio)
                    grade_zh = ratio_grade_zh(tp_ratio)
                
                results.append({
                    "item_name": row.item_name,
                    "steam_price": steam_price,
                    "steam_volume": row.steam_volume,
                    f"{source}_price": tp_price,
                    f"{source}_ratio": tp_ratio,
                    f"{source}_net_ratio": tp_ratio,
                    f"{source}_grade": grade,
                    f"{source}_grade_zh": grade_zh,
                })
            
            if results:
                results.sort(key=lambda x: x.get(f"{source}_ratio") or 999)
                return results[:limit]
        finally:
            db.close()
        
        # DB empty — return demo data so UI isn't blank
        demo = [
            {"item_name": "Revolution Case", "steam_price": 0.51, "steam_volume": 15000,
             f"{source}_price": 0.38, f"{source}_ratio": 0.74, f"{source}_net_ratio": 0.70,
             f"{source}_grade": "excellent", f"{source}_grade_zh": "优秀"},
            {"item_name": "Kilowatt Case", "steam_price": 1.20, "steam_volume": 8200,
             f"{source}_price": 0.90, f"{source}_ratio": 0.75, f"{source}_net_ratio": 0.71,
             f"{source}_grade": "excellent", f"{source}_grade_zh": "优秀"},
            {"item_name": "Recoil Case", "steam_price": 0.85, "steam_volume": 11000,
             f"{source}_price": 0.62, f"{source}_ratio": 0.73, f"{source}_net_ratio": 0.69,
             f"{source}_grade": "excellent", f"{source}_grade_zh": "优秀"},
            {"item_name": "Snakebite Case", "steam_price": 0.42, "steam_volume": 9000,
             f"{source}_price": 0.31, f"{source}_ratio": 0.74, f"{source}_net_ratio": 0.70,
             f"{source}_grade": "excellent", f"{source}_grade_zh": "优秀"},
            {"item_name": "Fracture Case", "steam_price": 0.35, "steam_volume": 7000,
             f"{source}_price": 0.26, f"{source}_ratio": 0.74, f"{source}_net_ratio": 0.70,
             f"{source}_grade": "excellent", f"{source}_grade_zh": "优秀"},
            {"item_name": "AK-47 | Redline (Field-Tested)", "steam_price": 45.0, "steam_volume": 300,
             f"{source}_price": 34.0, f"{source}_ratio": 0.76, f"{source}_net_ratio": 0.72,
             f"{source}_grade": "good", f"{source}_grade_zh": "良好"},
            {"item_name": "M4A4 | Dragon King (Field-Tested)", "steam_price": 12.0, "steam_volume": 450,
             f"{source}_price": 9.0, f"{source}_ratio": 0.75, f"{source}_net_ratio": 0.71,
             f"{source}_grade": "good", f"{source}_grade_zh": "良好"},
            {"item_name": "AWP | Hyper Beast (Field-Tested)", "steam_price": 28.0, "steam_volume": 200,
             f"{source}_price": 21.0, f"{source}_ratio": 0.75, f"{source}_net_ratio": 0.71,
             f"{source}_grade": "good", f"{source}_grade_zh": "良好"},
        ]
        if max_price is not None:
            demo = [d for d in demo if d["steam_price"] <= max_price]
        return demo[:limit]

    def get_ratio_summary(self) -> Dict[str, Any]:
        """Get summary statistics from last scan."""
        if not self._last_results:
            return {"status": "no_data", "count": 0}

        sources = ["buff", "youpin", "skinport", "csfloat"]
        summary = {
            "status": "ok",
            "count": len(self._last_results),
            "last_update": self._last_update,
            "by_source": {},
        }

        for source in sources:
            ratio_key = f"{source}_ratio"
            ratios = [r[ratio_key] for r in self._last_results if r.get(ratio_key) is not None]
            if ratios:
                summary["by_source"][source] = {
                    "min_ratio": round(min(ratios), 4),
                    "avg_ratio": round(sum(ratios) / len(ratios), 4),
                    "items_tracked": len(ratios),
                }

        return summary


# Singleton
ratio_engine = RatioEngine()
