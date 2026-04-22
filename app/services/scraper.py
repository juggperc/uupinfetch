from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.models import Item, PriceHistory, RatioHistory, FloatSnapshot
from app.services.steam import steam_scraper
from app.services.buff import buff_scraper
from app.services.youpin import youpin_scraper
from app.services.skinport import skinport_scraper
from app.services.csfloat import csfloat_scraper
from app.services.market_fees import calculate_steam_ratio
from app.core.config import get_settings
from datetime import datetime
from typing import Optional
import asyncio
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class BackgroundScraper:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        if not self.is_running:
            self.scheduler.add_job(
                self.scrape_popular_items,
                IntervalTrigger(minutes=settings.SCRAPE_INTERVAL_MINUTES),
                id="scrape_popular",
                replace_existing=True,
            )
            self.scheduler.add_job(
                self.scrape_ratios,
                IntervalTrigger(minutes=settings.SCRAPE_INTERVAL_MINUTES * 2),
                id="scrape_ratios",
                replace_existing=True,
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("Background scraper started")
    
    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Background scraper stopped")
    
    async def scrape_popular_items(self):
        """Scrape popular CS2 items from Steam and store in DB with price history."""
        logger.info("Starting background scrape...")
        db = SessionLocal()
        try:
            keywords = ["AK-47", "M4A4", "AWP", "Desert Eagle", "Knife", "Gloves",
                        "Case", "Sticker", "USP-S", "Glock-18", "M4A1-S", "MP9"]
            total_scraped = 0
            
            for keyword in keywords:
                try:
                    items = await steam_scraper.search_items(keyword, page=1, page_size=5)
                    for item_data in items:
                        existing = db.query(Item).filter(
                            Item.source == "steam",
                            Item.external_id == item_data["external_id"]
                        ).first()
                        
                        price = item_data.get("price")
                        
                        if existing:
                            # Record price history before updating
                            if price and existing.price and price != existing.price:
                                self._record_price_history(db, existing.id, "steam", price, 
                                                           item_data.get("volume"))
                            existing.price = price
                            existing.lowest_price = price
                            existing.updated_at = datetime.now()
                        else:
                            new_item = Item(
                                source="steam",
                                external_id=item_data["external_id"],
                                name=item_data["name"],
                                hash_name=item_data.get("hash_name"),
                                price=price,
                                lowest_price=price,
                                image_url=item_data.get("image_url"),
                                exterior=item_data.get("exterior"),
                                rarity=item_data.get("rarity"),
                                weapon_name=item_data.get("weapon_name"),
                            )
                            db.add(new_item)
                            db.flush()  # Get the ID
                            if price:
                                self._record_price_history(db, new_item.id, "steam", price,
                                                           item_data.get("volume"))
                        
                        total_scraped += 1
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Error scraping {keyword}: {e}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
            
            # Also scrape float data from CSFloat for key items
            await self._scrape_float_data(db)
            
            logger.info(f"Scraped {total_scraped} items")
        finally:
            db.close()
    
    def _record_price_history(self, db: Session, item_id: int, source: str, 
                              price: float, volume: Optional[int] = None):
        """Record a price history entry."""
        try:
            entry = PriceHistory(
                item_id=item_id,
                source=source,
                price=price,
                volume=volume,
                recorded_at=datetime.now(),
            )
            db.add(entry)
        except Exception as e:
            logger.debug(f"Failed to record price history: {e}")
    
    async def _scrape_float_data(self, db: Session):
        """Scrape float data from CSFloat for tracked items."""
        if not settings.ENABLE_CSFLOAT:
            return
        
        try:
            # Get recently updated items from DB
            items = db.query(Item).filter(
                Item.source == "steam",
                Item.price.isnot(None)
            ).order_by(Item.updated_at.desc()).limit(15).all()
            
            for item in items:
                if not item.hash_name:
                    continue
                try:
                    listings = await csfloat_scraper.search_listings(item.hash_name, limit=3)
                    for listing in listings:
                        if listing.get("float_value") is not None:
                            snapshot = FloatSnapshot(
                                item_name=item.name,
                                source="csfloat",
                                external_id=str(listing.get("id")),
                                float_value=listing.get("float_value"),
                                paint_seed=listing.get("paint_seed"),
                                paint_index=listing.get("paint_index"),
                                price=listing.get("price"),
                                stickers=listing.get("stickers"),
                                inspect_link=listing.get("inspect_link"),
                                recorded_at=datetime.now(),
                            )
                            db.add(snapshot)
                    db.commit()
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Float scrape failed for {item.name}: {e}")
                    db.rollback()
        except Exception as e:
            logger.warning(f"Float data scrape failed: {e}")
    
    async def scrape_ratios(self):
        """Scrape 挂刀 ratios for popular items and persist."""
        logger.info("Starting ratio scrape...")
        db = SessionLocal()
        try:
            from app.services.ratio_engine import POPULAR_RATIO_ITEMS, RatioEngine
            
            engine = RatioEngine()
            results = await engine.scan_ratios(POPULAR_RATIO_ITEMS[:30], max_items=30)
            
            for result in results:
                try:
                    hist = RatioHistory(
                        item_name=result["item_name"],
                        steam_price=result.get("steam_price"),
                        steam_volume=result.get("steam_volume"),
                        buff_price=result.get("buff_price"),
                        buff_ratio=result.get("buff_ratio"),
                        youpin_price=result.get("youpin_price"),
                        youpin_ratio=result.get("youpin_ratio"),
                        skinport_price=result.get("skinport_price"),
                        skinport_ratio=result.get("skinport_ratio"),
                        csfloat_price=result.get("csfloat_price"),
                        csfloat_ratio=result.get("csfloat_ratio"),
                        recorded_at=datetime.now(),
                    )
                    db.add(hist)
                except Exception as e:
                    logger.debug(f"Failed to save ratio history: {e}")
            
            db.commit()
            logger.info(f"Saved {len(results)} ratio entries")
        except Exception as e:
            logger.error(f"Ratio scrape failed: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_popular_items(self, limit: int = 8):
        """Get popular items from DB."""
        db = SessionLocal()
        try:
            items = db.query(Item).filter(
                Item.source == "steam",
                Item.price.isnot(None)
            ).order_by(Item.updated_at.desc()).limit(limit).all()
            return items
        finally:
            db.close()
    
    async def get_price_history(self, item_id: int, source: str = "steam", limit: int = 100):
        """Get price history for an item."""
        db = SessionLocal()
        try:
            history = db.query(PriceHistory).filter(
                PriceHistory.item_id == item_id,
                PriceHistory.source == source
            ).order_by(PriceHistory.recorded_at.desc()).limit(limit).all()
            return history
        finally:
            db.close()
    
    async def get_ratio_history(self, item_name: str, source: str = "buff", limit: int = 100):
        """Get ratio history for an item."""
        db = SessionLocal()
        try:
            ratio_col = getattr(RatioHistory, f"{source}_ratio", None)
            if ratio_col is None:
                return []
            history = db.query(RatioHistory).filter(
                RatioHistory.item_name == item_name,
                ratio_col.isnot(None)
            ).order_by(RatioHistory.recorded_at.desc()).limit(limit).all()
            return history
        finally:
            db.close()
    
    async def get_latest_ratios(self, source: str = "buff", limit: int = 50):
        """Get latest ratio snapshot per item."""
        db = SessionLocal()
        try:
            # Subquery to get latest record per item
            from sqlalchemy import func
            subq = db.query(
                RatioHistory.item_name,
                func.max(RatioHistory.recorded_at).label("max_date")
            ).group_by(RatioHistory.item_name).subquery()
            
            results = db.query(RatioHistory).join(
                subq,
                (RatioHistory.item_name == subq.c.item_name) &
                (RatioHistory.recorded_at == subq.c.max_date)
            ).limit(limit).all()
            return results
        finally:
            db.close()

# Singleton
background_scraper = BackgroundScraper()
