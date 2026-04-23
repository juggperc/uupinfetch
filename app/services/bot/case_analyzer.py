"""
Case investment analyzer.
Extracted from the monolithic bot_engine.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("cs2_bot.cases")

@dataclass
class InvestmentRecommendation:
    item_name: str
    item_type: str
    current_price: float
    target_price: float
    reasoning: str
    confidence: str
    timeframe: str
    expected_roi_pct: float
    timestamp: str
    source: str

CASES = [
    "Operation Broken Fang Case", "Operation Riptide Case",
    "Revolution Case", "Kilowatt Case", "Dreams & Nightmares Case",
    "Recoil Case", "Snakebite Case", "Fracture Case",
    "Prisma 2 Case", "CS20 Case", "Danger Zone Case",
    "Horizon Case", "Clutch Case", "Spectrum 2 Case",
    "Glove Case", "Gamma 2 Case", "Gamma Case",
    "Chroma 3 Case", "Chroma 2 Case", "Falchion Case",
    "Shadow Case", "Revolver Case", "Vanguard Case",
    "Huntsman Case", "Breakout Case", "Phoenix Case",
    "Weapon Case", "Weapon Case 2", "Weapon Case 3",
    "Bravo Case", "Esports 2013 Case", "Esports 2013 Winter Case",
    "Esports 2014 Summer Case", "Weapon Case 1",
]

class CaseAnalyzer:
    """Analyze CS2 case investment opportunities."""
    
    async def analyze(self, search_func, limit: int = 15) -> List[InvestmentRecommendation]:
        import asyncio
        
        async def analyze_one(case_name: str) -> Optional[InvestmentRecommendation]:
            try:
                items = await search_func(case_name, "steam")
                if not items:
                    return None
                case = items[0]
                price = case.get("price", 0)
                if not price or price <= 0:
                    return None
                
                if price < 1.0:
                    expected_roi = 25.0
                    reasoning = f"{case_name} is a common drop case priced under 1 CNY. Historically, common cases appreciate 20-40% annually as they rotate out of active drop pool."
                    confidence = "medium"
                    timeframe = "6-12 months"
                elif price < 5.0:
                    expected_roi = 15.0
                    reasoning = f"{case_name} at {price} CNY offers moderate growth potential. Cases in this range often see 10-20% gains during major updates."
                    confidence = "medium"
                    timeframe = "3-6 months"
                elif price < 20.0:
                    expected_roi = 8.0
                    reasoning = f"{case_name} is approaching mature pricing. Lower volatility but steady appreciation expected."
                    confidence = "low"
                    timeframe = "6-12 months"
                else:
                    expected_roi = 5.0
                    reasoning = f"{case_name} is a premium case. High price limits explosive growth but maintains value well."
                    confidence = "low"
                    timeframe = "12+ months"
                
                return InvestmentRecommendation(
                    item_name=case_name,
                    item_type="case",
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
                logger.debug(f"Case search failed for '{case_name}': {e}")
                return None
        
        results = await asyncio.gather(*[analyze_one(c) for c in CASES[:limit]])
        recommendations = [r for r in results if r is not None]
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
