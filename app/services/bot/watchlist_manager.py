"""
Watchlist manager and checker.
Extracted from the monolithic bot_engine.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import WatchlistItem

logger = logging.getLogger("cs2_bot.watchlist")

class WatchlistManager:
    """Manage price watchlist and check for triggered alerts."""
    
    @staticmethod
    def get_items(db: Session, active_only: bool = True) -> List[Dict[str, Any]]:
        query = db.query(WatchlistItem)
        if active_only:
            query = query.filter(WatchlistItem.active == True)
        rows = query.order_by(WatchlistItem.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "item_name": r.item_name,
                "target_price": r.target_price,
                "condition": r.condition,
                "active": r.active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    
    @staticmethod
    def add_item(db: Session, item_name: str, target_price: float, condition: str = "below") -> int:
        item = WatchlistItem(item_name=item_name, target_price=target_price, condition=condition)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id
    
    @staticmethod
    def remove_item(db: Session, watch_id: int) -> bool:
        item = db.query(WatchlistItem).filter(WatchlistItem.id == watch_id).first()
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True
    
    @staticmethod
    async def check_all(db: Session, search_func) -> List[Dict[str, Any]]:
        """Check active watchlist items against current prices."""
        items = WatchlistManager.get_items(db, active_only=True)
        
        async def check_one(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            try:
                results = await search_func(item["item_name"], source="all", page_size=10)
                for result in results:
                    price = result.get("price")
                    if price is None:
                        continue
                    condition = item.get("condition", "below")
                    target = item["target_price"]
                    
                    triggered = False
                    if condition == "below" and price <= target:
                        triggered = True
                    elif condition == "above" and price >= target:
                        triggered = True
                    
                    if triggered:
                        return {
                            "watch_id": item["id"],
                            "item_name": item["item_name"],
                            "current_price": price,
                            "target_price": target,
                            "condition": condition,
                            "source": result.get("source", "unknown"),
                        }
            except Exception as e:
                logger.warning(f"Watchlist check failed for {item['item_name']}: {e}")
            return None
        
        results = await asyncio.gather(*[check_one(item) for item in items])
        return [r for r in results if r is not None]
