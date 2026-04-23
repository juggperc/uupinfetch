"""
Sticker and capsule investment analyzer.
Extracted from the monolithic bot_engine.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from app.services.bot.case_analyzer import InvestmentRecommendation

logger = logging.getLogger("cs2_bot.stickers")

STICKER_CAPSULES = [
    "Copenhagen 2024", "Paris 2023", "Rio 2022", "Antwerp 2022",
    "Stockholm 2021", "Berlin 2019", "Katowice 2019",
]

class StickerAnalyzer:
    """Analyze sticker and capsule investment opportunities."""
    
    async def analyze(self, search_func) -> List[InvestmentRecommendation]:
        import asyncio
        
        async def analyze_one(capsule: str) -> Optional[InvestmentRecommendation]:
            try:
                items = await search_func(f"{capsule} Sticker Capsule", "steam")
                if not items:
                    items = await search_func(f"{capsule} Capsule", "steam")
                if not items:
                    return None
                
                item = items[0]
                price = item.get("price", 0)
                if not (0.5 < price < 50):
                    return None
                
                try:
                    year = int(capsule.split()[-1])
                except ValueError:
                    year = 2024
                age_years = 2026 - year
                
                if age_years == 0:
                    expected_roi = 40.0
                    reasoning = f"{capsule} is the current major. Buy capsules NOW before the major ends and they stop dropping. Historical ROI: 50-200% post-major."
                    confidence = "high"
                    timeframe = "3-6 months post-major"
                elif age_years == 1:
                    expected_roi = 25.0
                    reasoning = f"{capsule} capsules are no longer dropping. Supply is fixed. Demand increases as crafts use them up."
                    confidence = "high"
                    timeframe = "6-12 months"
                elif age_years <= 3:
                    expected_roi = 15.0
                    reasoning = f"{capsule} is a recent major with established demand. Steady appreciation expected."
                    confidence = "medium"
                    timeframe = "6-12 months"
                else:
                    expected_roi = 8.0
                    reasoning = f"{capsule} is an older major. Lower growth but stable demand from collectors."
                    confidence = "low"
                    timeframe = "12+ months"
                
                return InvestmentRecommendation(
                    item_name=f"{capsule} Capsule",
                    item_type="sticker",
                    current_price=price,
                    target_price=round(price * (1 + expected_roi/100), 2),
                    reasoning=reasoning,
                    confidence=confidence,
                    timeframe=timeframe,
                    expected_roi_pct=expected_roi,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="steam"
                )
            except Exception as e:
                logger.debug(f"Sticker search failed for '{capsule}': {e}")
                return None
        
        results = await asyncio.gather(*[analyze_one(c) for c in STICKER_CAPSULES])
        recommendations = [r for r in results if r is not None]
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
