import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import PortfolioItem, PortfolioTransaction, PriceHistory
from datetime import datetime

logger = logging.getLogger(__name__)

class PortfolioEngine:
    """Portfolio management: holdings, P&L tracking, allocation analysis."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_items(self) -> List[PortfolioItem]:
        return self.db.query(PortfolioItem).order_by(PortfolioItem.created_at.desc()).all()
    
    def get_item(self, item_id: int) -> Optional[PortfolioItem]:
        return self.db.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
    
    def add_item(self, data: Dict[str, Any]) -> PortfolioItem:
        item = PortfolioItem(**data)
        self.db.add(item)
        self.db.flush()
        
        # Record buy transaction
        txn = PortfolioTransaction(
            portfolio_item_id=item.id,
            transaction_type="buy",
            quantity=item.quantity,
            price=item.buy_price,
            total=item.buy_price * item.quantity,
            notes=item.notes,
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def update_item(self, item_id: int, data: Dict[str, Any]) -> Optional[PortfolioItem]:
        item = self.get_item(item_id)
        if not item:
            return None
        
        for key, value in data.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)
        
        item.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(item)
        return item
    
    def remove_item(self, item_id: int) -> bool:
        item = self.get_item(item_id)
        if not item:
            return False
        
        # Record sell transaction at current price if available
        sell_price = item.current_price or item.buy_price
        txn = PortfolioTransaction(
            portfolio_item_id=item.id,
            transaction_type="sell",
            quantity=item.quantity,
            price=sell_price,
            total=sell_price * item.quantity,
            notes="Portfolio removal",
        )
        self.db.add(txn)
        self.db.delete(item)
        self.db.commit()
        return True
    
    def sell_partial(self, item_id: int, quantity: int, sell_price: float, notes: str = "") -> Optional[PortfolioItem]:
        item = self.get_item(item_id)
        if not item or item.quantity < quantity:
            return None
        
        txn = PortfolioTransaction(
            portfolio_item_id=item.id,
            transaction_type="sell",
            quantity=quantity,
            price=sell_price,
            total=sell_price * quantity,
            notes=notes or f"Sold {quantity} units",
        )
        self.db.add(txn)
        
        item.quantity -= quantity
        if item.quantity <= 0:
            self.db.delete(item)
        
        self.db.commit()
        return item
    
    def get_transactions(self, item_id: Optional[int] = None) -> List[PortfolioTransaction]:
        query = self.db.query(PortfolioTransaction)
        if item_id:
            query = query.filter(PortfolioTransaction.portfolio_item_id == item_id)
        return query.order_by(PortfolioTransaction.created_at.desc()).all()
    
    def get_summary(self) -> Dict[str, Any]:
        items = self.get_all_items()
        
        total_invested = sum(i.buy_price * i.quantity for i in items)
        total_value = sum((i.current_price or i.buy_price) * i.quantity for i in items)
        
        unrealized_pnl = total_value - total_invested
        unrealized_pnl_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
        
        allocation = {}
        for i in items:
            src = i.source or "unknown"
            val = (i.current_price or i.buy_price) * i.quantity
            allocation[src] = allocation.get(src, 0) + val
        
        return {
            "total_invested": round(total_invested, 2),
            "total_value": round(total_value, 2),
            "total_unrealized_pnl": round(unrealized_pnl, 2),
            "total_unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "item_count": len(items),
            "allocation_by_source": {k: round(v, 2) for k, v in allocation.items()},
        }
    
    def refresh_prices(self) -> int:
        """Try to refresh current prices from price history."""
        items = self.get_all_items()
        updated = 0
        
        for item in items:
            # Find latest price history for this item name
            latest = self.db.query(PriceHistory).filter(
                PriceHistory.item_id.in_(
                    self.db.query(PortfolioItem.id).filter(PortfolioItem.item_name == item.item_name)
                )
            ).order_by(PriceHistory.recorded_at.desc()).first()
            
            # Fallback: search by matching item names in items table
            if not latest:
                from app.models.models import Item
                db_item = self.db.query(Item).filter(
                    Item.name.ilike(f"%{item.item_name}%"),
                    Item.price.isnot(None)
                ).order_by(Item.updated_at.desc()).first()
                
                if db_item and db_item.price:
                    item.current_price = db_item.price
                    updated += 1
                    continue
            
            if latest:
                item.current_price = latest.price
                updated += 1
        
        self.db.commit()
        return updated
