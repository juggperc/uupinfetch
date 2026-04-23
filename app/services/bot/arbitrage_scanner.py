"""
Arbitrage scanner: cross-marketplace price spread detection.
Extracted from the monolithic bot_engine.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from dataclasses import dataclass
from app.services.market_fees import calculate_spread

logger = logging.getLogger("cs2_bot.arbitrage")

@dataclass
class ArbitrageOpportunity:
    item_name: str
    buy_source: str
    buy_price: float
    sell_source: str
    sell_price: float
    spread: float
    spread_pct: float
    item_id: str
    timestamp: str
    confidence: str

class ArbitrageScanner:
    """Scan for cross-marketplace arbitrage opportunities."""
    
    async def scan(self, search_func, queries: List[str]) -> List[ArbitrageOpportunity]:
        """
        Args:
            search_func: async function(query, source="all", page_size) -> List[Dict]
        """
        import asyncio
        
        async def search_one(query: str):
            try:
                return await search_func(query, source="all", page_size=50)
            except Exception as e:
                logger.warning(f"Arbitrage search failed for '{query}': {e}")
                return []
        
        all_results = await asyncio.gather(*[search_one(q) for q in queries])
        
        # Aggregate prices by item name + source (keep lowest price per source)
        prices_by_source: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        for items in all_results:
            for item in items:
                name = item.get("name", "")
                price = item.get("price")
                item_source = item.get("source", "unknown")
                volume = item.get("volume") or item.get("quantity") or 0
                if price and price > 0:
                    if name not in prices_by_source:
                        prices_by_source[name] = {}
                    if item_source not in prices_by_source[name] or price < prices_by_source[name][item_source]["price"]:
                        prices_by_source[name][item_source] = {
                            "price": price,
                            "id": item.get("external_id", ""),
                            "volume": volume,
                        }
        
        opportunities = []
        for name, source_prices in prices_by_source.items():
            if len(source_prices) >= 2:
                sources = list(source_prices.items())
                for i in range(len(sources)):
                    for j in range(len(sources)):
                        if i == j:
                            continue
                        buy_src, buy_data = sources[i]
                        sell_src, sell_data = sources[j]
                        
                        buy_price = buy_data["price"]
                        sell_price = sell_data["price"]
                        
                        fee_data = calculate_spread(buy_src, buy_price, sell_src, sell_price)
                        net_spread = fee_data["net_spread"]
                        net_spread_pct = fee_data["net_spread_pct"]
                        
                        if net_spread <= 0.3:
                            continue
                        if buy_data.get("volume", 0) < 3:
                            continue
                        
                        confidence = "high" if net_spread_pct > 12 else "medium" if net_spread_pct > 6 else "low"
                        opp = ArbitrageOpportunity(
                            item_name=name,
                            buy_source=buy_src,
                            buy_price=buy_price,
                            sell_source=sell_src,
                            sell_price=sell_price,
                            spread=round(net_spread, 2),
                            spread_pct=round(net_spread_pct, 2),
                            item_id=buy_data["id"],
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            confidence=confidence
                        )
                        opportunities.append(opp)
        
        # Deduplicate by item_name + buy_source + sell_source, keep highest net spread
        seen = {}
        for opp in opportunities:
            key = f"{opp.item_name}:{opp.buy_source}:{opp.sell_source}"
            if key not in seen or opp.spread > seen[key].spread:
                seen[key] = opp
        
        return sorted(seen.values(), key=lambda x: x.spread_pct, reverse=True)
