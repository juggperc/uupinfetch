"""
Backward-compatible bot engine wrapper.
Delegates to the refactored BotOrchestrator + SQLAlchemy models.
This file preserves the public API so existing imports don't break.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.bot.bot_orchestrator import BotOrchestrator, get_orchestrator
from app.services.bot.webhook_notifier import WebhookNotifier
from app.services.bot.watchlist_manager import WatchlistManager
from app.db.database import SessionLocal

logger = logging.getLogger("cs2_bot")

class CS2TradingBot:
    """Backward-compatible wrapper. All logic delegated to BotOrchestrator."""
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.running = False
        self.scan_interval = 60
        self.scan_count = 0
        self._orchestrator = get_orchestrator()
    
    def _get_db(self):
        return SessionLocal()
    
    # Watchlist (backward compatible)
    def add_watchlist(self, item_name: str, target_price: float, condition: str = "below") -> int:
        db = self._get_db()
        try:
            return WatchlistManager.add_item(db, item_name, target_price, condition)
        finally:
            db.close()
    
    def remove_watchlist(self, watch_id: int) -> bool:
        db = self._get_db()
        try:
            return WatchlistManager.remove_item(db, watch_id)
        finally:
            db.close()
    
    def get_watchlist(self, active_only: bool = True) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            return WatchlistManager.get_items(db, active_only)
        finally:
            db.close()
    
    # Webhooks (backward compatible)
    def add_webhook(self, name: str, webhook_type: str, url: str, events: str) -> int:
        db = self._get_db()
        try:
            return WebhookNotifier.add_webhook(db, name, webhook_type, url, events)
        finally:
            db.close()
    
    def remove_webhook(self, webhook_id: int) -> bool:
        db = self._get_db()
        try:
            return WebhookNotifier.remove_webhook(db, webhook_id)
        finally:
            db.close()
    
    def get_webhooks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            return WebhookNotifier.get_webhooks(db, active_only)
        finally:
            db.close()
    
    async def _send_webhook(self, webhook: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        return await WebhookNotifier._send_single(webhook, payload)
    
    async def notify_webhooks(self, event_type: str, data: Dict[str, Any]):
        db = self._get_db()
        try:
            await WebhookNotifier.notify(db, event_type, data)
        finally:
            db.close()
    
    async def check_watchlist(self):
        db = self._get_db()
        try:
            return await WatchlistManager.check_all(db, self._orchestrator._direct_search)
        finally:
            db.close()
    
    async def run_scan(self):
        await self._orchestrator.run_scan()
    
    async def run(self):
        """Main bot loop — runs scans continuously."""
        self.running = True
        logger.info("CS2 Trading Bot started")
        
        try:
            await self.run_scan()
        except Exception as e:
            logger.error(f"Initial scan error: {e}")
        
        while self.running:
            try:
                await self.run_scan()
                logger.info(f"Sleeping {self.scan_interval}s...")
            except Exception as e:
                logger.error(f"Scan error: {e}")
            await asyncio.sleep(self.scan_interval)
    
    def stop(self):
        self.running = False
        logger.info("Bot stopping...")
    
    async def close(self):
        pass

# Singleton instance management
_bot_instance: Optional[CS2TradingBot] = None
_bot_lock = asyncio.Lock()

async def get_bot(api_base: str = "http://localhost:8000") -> CS2TradingBot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CS2TradingBot(api_base=api_base)
    return _bot_instance

def get_bot_sync(api_base: str = "http://localhost:8000") -> CS2TradingBot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CS2TradingBot(api_base=api_base)
    return _bot_instance
