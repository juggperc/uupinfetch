from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.models import Item, PriceHistory
from app.services.steam import steam_scraper
from app.services.youpin import youpin_scraper
from app.core.config import get_settings
from datetime import datetime
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
            self.scheduler.start()
            self.is_running = True
            logger.info("Background scraper started")
    
    def stop(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Background scraper stopped")
    
    async def scrape_popular_items(self):
        """Scrape popular CS2 items from Steam and store in DB."""
        logger.info(f"Starting background scrape...")
        db = SessionLocal()
        try:
            keywords = ["AK-47", "M4A4", "AWP", "Desert Eagle", "Knife", "Gloves"]
            total_scraped = 0
            
            for keyword in keywords:
                try:
                    items = await steam_scraper.search_items(keyword, page=1, page_size=5)
                    for item_data in items:
                        existing = db.query(Item).filter(
                            Item.source == "steam",
                            Item.external_id == item_data["external_id"]
                        ).first()
                        
                        if existing:
                            existing.price = item_data.get("price")
                            existing.lowest_price = item_data.get("price")
                            existing.updated_at = datetime.now()
                        else:
                            new_item = Item(
                                source="steam",
                                external_id=item_data["external_id"],
                                name=item_data["name"],
                                hash_name=item_data.get("hash_name"),
                                price=item_data.get("price"),
                                lowest_price=item_data.get("price"),
                                image_url=item_data.get("image_url"),
                                exterior=item_data.get("exterior"),
                                rarity=item_data.get("rarity"),
                                weapon_name=item_data.get("weapon_name"),
                            )
                            db.add(new_item)
                        
                        total_scraped += 1
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Error scraping {keyword}: {e}")
                    db.rollback()
            
            logger.info(f"Scraped {total_scraped} items")
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

# Singleton
background_scraper = BackgroundScraper()
