"""
Bot orchestrator — runs all scanners via APScheduler (no background threads).
Replaces the monolithic CS2TradingBot with a clean orchestrator over focused services.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.bot import (
    ArbitrageScanner, CaseAnalyzer, StickerAnalyzer,
    WatchlistManager, WebhookNotifier, InvestmentRecommendation,
)
from app.services.bot.case_analyzer import CASES
from app.services.steam import steam_scraper
from app.services.pattern_engine import get_pattern_alert
from app.models.models import (
    BotStatus, ArbitrageOpportunity as ArbitrageOpportunityModel,
    InvestmentRecommendation as InvestmentRecommendationModel,
    MarketInsight, OpportunityHistory,
)
from app.db.database import SessionLocal

logger = logging.getLogger("cs2_bot")

# Demo seed data
_DEMO_RECS = [
    ("Revolution Case", "case", 0.85, 1.20, "Common drop case under 1 CNY. Historically appreciates 20-40% annually as it rotates out of active drop pool.", "medium", "6-12 months", 25.0, "steam"),
    ("Kilowatt Case", "case", 1.50, 2.00, "Mid-tier case with consistent demand. Expected 15-20% gains during major updates.", "medium", "3-6 months", 18.0, "steam"),
    ("Copenhagen 2024 Capsule", "sticker", 2.50, 4.50, "Current major capsule. Buy before the major ends and they stop dropping. Historical ROI: 50-200% post-major.", "high", "3-6 months post-major", 45.0, "steam"),
    ("Paris 2023 Capsule", "sticker", 1.80, 2.70, "No longer dropping. Supply is fixed. Demand increases as crafts use them up.", "high", "6-12 months", 25.0, "steam"),
    ("AK-47 | Redline (Field-Tested)", "skin", 45.0, 55.0, "Stable skin with consistent volume. Low-float FT versions trade near MW prices.", "low", "3-6 months", 12.0, "float_analysis"),
]

_DEMO_ARB = [
    ("AK-47 | Redline (Field-Tested)", "buff", 42.50, "skinport", 48.00, 5.50, 12.9, "", "high"),
    ("M4A4 | Desolate Space (Minimal Wear)", "youpin", 18.00, "buff", 21.50, 3.50, 19.4, "", "medium"),
    ("AWP | Hyper Beast (Field-Tested)", "skinport", 35.00, "buff", 40.00, 5.00, 14.3, "", "medium"),
]

_DEMO_INSIGHTS = [
    ("cases", "Case Investment Season", "Recent CS2 updates have created opportunities in case investments. Common drop cases under 2 CNY show consistent 15-25% annual appreciation.", "hot"),
    ("stickers", "Sticker Capsule Strategy", "Buy capsules during majors, sell 3-6 months after. Historical ROI for recent majors: 50-200%. Current major capsules are optimal entry.", "hot"),
    ("float", "Float Arbitrage", "Low-float Field-Tested skins often trade near Minimal Wear prices. Check float values on Buff163 for true arbitrage opportunities.", "warm"),
]

class BotOrchestrator:
    """Orchestrates all bot scanners and persists results via SQLAlchemy."""
    
    def __init__(self):
        self.scan_count = 0
        self.arbitrage_scanner = ArbitrageScanner()
        self.case_analyzer = CaseAnalyzer()
        self.sticker_analyzer = StickerAnalyzer()
        self.watchlist_manager = WatchlistManager()
        self.webhook_notifier = WebhookNotifier()
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    def _seed_demo_data(self, db: Session):
        """Seed demo data if tables are empty."""
        now = datetime.now(timezone.utc)
        seeded = False
        
        if db.query(InvestmentRecommendationModel).count() == 0:
            for rec in _DEMO_RECS:
                db.add(InvestmentRecommendationModel(
                    item_name=rec[0], item_type=rec[1], current_price=rec[2], target_price=rec[3],
                    reasoning=rec[4], confidence=rec[5], timeframe=rec[6], expected_roi_pct=rec[7], source=rec[8],
                    timestamp=now, discovered_at=now,
                ))
            seeded = True
        
        if db.query(ArbitrageOpportunityModel).count() == 0:
            for arb in _DEMO_ARB:
                db.add(ArbitrageOpportunityModel(
                    item_name=arb[0], buy_source=arb[1], buy_price=arb[2], sell_source=arb[3],
                    sell_price=arb[4], spread=arb[5], spread_pct=arb[6], item_id=arb[7], confidence=arb[8],
                    timestamp=now, discovered_at=now,
                ))
            seeded = True
        
        if db.query(MarketInsight).count() == 0:
            for ins in _DEMO_INSIGHTS:
                db.add(MarketInsight(
                    category=ins[0], title=ins[1], description=ins[2], severity=ins[3],
                    timestamp=now, discovered_at=now,
                ))
            seeded = True
        
        if db.query(OpportunityHistory).count() == 0:
            for date, arb_count, rec_count, avg_roi in [
                ("2026-04-20", 3, 5, 15.2),
                ("2026-04-21", 2, 8, 18.5),
                ("2026-04-22", 3, 5, 14.8),
            ]:
                db.add(OpportunityHistory(date=date, arbitrage_count=arb_count, recommendation_count=rec_count, avg_roi=avg_roi))
            seeded = True
        
        # Ensure bot status row exists
        status = db.query(BotStatus).filter(BotStatus.id == 1).first()
        if not status:
            db.add(BotStatus(id=1, running=True, arbitrage_count=3, recommendation_count=5))
        
        db.commit()
        if seeded:
            logger.info("Seeded demo bot data")
    
    async def _direct_search(self, query: str, source: str = "steam", page_size: int = 20) -> List[Dict[str, Any]]:
        """Search items directly via scrapers (no HTTP loopback)."""
        import time
        from app.services.skinport import skinport_scraper
        from app.services.buff import buff_scraper
        from app.services.youpin import youpin_scraper
        from app.core.config import get_settings
        
        settings = get_settings()
        cache_key = f"search:{query}:{source}:{page_size}"
        
        # Simple in-memory cache on the orchestrator instance
        cached = getattr(self, '_search_cache', {}).get(cache_key)
        if cached and (time.time() - cached["time"] < 30):
            return cached["data"]
        
        all_items = []
        
        try:
            if source in ("all", "steam"):
                items = await steam_scraper.search_items(query, page=1, page_size=page_size)
                for item in items:
                    item["source"] = "steam"
                all_items.extend(items)
        except Exception as e:
            logger.debug(f"Steam search failed for '{query}': {e}")
        
        try:
            if source in ("all", "skinport") and settings.ENABLE_SKINPORT:
                items = await skinport_scraper.search_items(query, page_size=page_size)
                for item in items:
                    item["source"] = "skinport"
                all_items.extend(items)
        except Exception as e:
            logger.debug(f"Skinport search failed for '{query}': {e}")
        
        try:
            if source in ("all", "buff") and settings.ENABLE_BUFF:
                items = await buff_scraper.search_items(query, page=1, page_size=page_size)
                for item in items:
                    item["source"] = "buff"
                all_items.extend(items)
        except Exception as e:
            logger.debug(f"Buff search failed for '{query}': {e}")
        
        try:
            if source in ("all", "youpin") and settings.ENABLE_YOUPIN:
                items = await youpin_scraper.search_items(query, page=1, page_size=page_size)
                for item in items:
                    item["source"] = "youpin"
                all_items.extend(items)
        except Exception as e:
            logger.debug(f"Youpin search failed for '{query}': {e}")
        
        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        self._search_cache[cache_key] = {"data": all_items, "time": time.time()}
        return all_items
    
    async def run_scan(self):
        """Execute a single market scan cycle."""
        logger.info("Starting market scan...")
        self.scan_count += 1
        db = self._get_db()
        
        try:
            self._seed_demo_data(db)
            
            # 1. Arbitrage scan
            arbitrage = []
            try:
                arbitrage = await self.arbitrage_scanner.scan(
                    self._direct_search, ["AK-47", "M4A4", "AWP", "Gloves", "Knife"]
                )
                if arbitrage:
                    db.query(ArbitrageOpportunityModel).delete()
                    for opp in arbitrage:
                        db.add(ArbitrageOpportunityModel(
                            item_name=opp.item_name, buy_source=opp.buy_source, buy_price=opp.buy_price,
                            sell_source=opp.sell_source, sell_price=opp.sell_price,
                            spread=opp.spread, spread_pct=opp.spread_pct,
                            item_id=opp.item_id, confidence=opp.confidence,
                            timestamp=datetime.fromisoformat(opp.timestamp) if opp.timestamp else datetime.now(timezone.utc),
                        ))
                    db.commit()
                    logger.info(f"Found {len(arbitrage)} arbitrage opportunities")
                    
                    # Webhook notify for high-confidence
                    high_conf = [a for a in arbitrage if a.confidence == "high" and a.spread_pct > 10]
                    if high_conf:
                        top = high_conf[0]
                        await self.webhook_notifier.notify(db, "high_confidence_arbitrage", {
                            "message": f"High-Confidence Arbitrage: {top.item_name}\nBuy ¥{top.buy_price} @ {top.buy_source} → Sell ¥{top.sell_price} @ {top.sell_source} ({top.spread_pct}% spread)",
                            "opportunity": {
                                "item_name": top.item_name, "buy_price": top.buy_price,
                                "buy_source": top.buy_source, "sell_price": top.sell_price,
                                "sell_source": top.sell_source, "spread_pct": top.spread_pct,
                            },
                        })
            except Exception as e:
                logger.error(f"Arbitrage scan failed: {e}")
            
            # 2. Case investments
            case_recs = []
            try:
                case_recs = await self.case_analyzer.analyze(self._direct_search)
                logger.info(f"Analyzed {len(case_recs)} case investments")
            except Exception as e:
                logger.error(f"Case investment scan failed: {e}")
            
            # 3. Sticker investments
            sticker_recs = []
            try:
                sticker_recs = await self.sticker_analyzer.analyze(self._direct_search)
                logger.info(f"Analyzed {len(sticker_recs)} sticker investments")
            except Exception as e:
                logger.error(f"Sticker investment scan failed: {e}")
            
            # 4. Market insights
            try:
                db.query(MarketInsight).delete()
                now = datetime.now(timezone.utc)
                for category, title, description, severity in _DEMO_INSIGHTS:
                    db.add(MarketInsight(
                        category=category, title=title, description=description,
                        severity=severity, timestamp=now, discovered_at=now,
                    ))
                db.commit()
            except Exception as e:
                logger.error(f"Insights generation failed: {e}")
            
            # 5. Watchlist alerts
            try:
                alerts = await self.watchlist_manager.check_all(db, self._direct_search)
                if alerts:
                    logger.info(f"Watchlist alerts triggered: {len(alerts)} items")
                    for alert in alerts:
                        await self.webhook_notifier.notify(db, "watchlist_trigger", {
                            "message": f"Watchlist Alert: {alert['item_name']} is now ¥{alert['current_price']} ({alert['condition']} target ¥{alert['target_price']})",
                            "alert": alert,
                        })
            except Exception as e:
                logger.error(f"Watchlist check failed: {e}")
            
            # Combine and save recommendations
            all_recs = case_recs + sticker_recs
            all_recs = sorted(all_recs, key=lambda x: x.expected_roi_pct, reverse=True)[:30]
            
            if all_recs:
                db.query(InvestmentRecommendationModel).delete()
                for rec in all_recs:
                    db.add(InvestmentRecommendationModel(
                        item_name=rec.item_name, item_type=rec.item_type,
                        current_price=rec.current_price, target_price=rec.target_price,
                        reasoning=rec.reasoning, confidence=rec.confidence,
                        timeframe=rec.timeframe, expected_roi_pct=rec.expected_roi_pct,
                        source=rec.source,
                        timestamp=datetime.fromisoformat(rec.timestamp) if rec.timestamp else datetime.now(timezone.utc),
                    ))
                db.commit()
            
            # Record history
            avg_roi = sum(r.expected_roi_pct for r in all_recs) / len(all_recs) if all_recs else 0
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            hist = db.query(OpportunityHistory).filter(OpportunityHistory.date == today).first()
            if hist:
                hist.arbitrage_count = len(arbitrage)
                hist.recommendation_count = len(all_recs)
                hist.avg_roi = avg_roi
            else:
                db.add(OpportunityHistory(date=today, arbitrage_count=len(arbitrage), recommendation_count=len(all_recs), avg_roi=avg_roi))
            
            # Update status
            status = db.query(BotStatus).filter(BotStatus.id == 1).first()
            if status:
                status.running = True
                status.last_scan = datetime.now(timezone.utc)
                status.arbitrage_count = len(arbitrage)
                status.recommendation_count = len(all_recs)
                status.scan_count = status.scan_count + 1
            
            db.commit()
            logger.info(f"Scan #{self.scan_count} complete.")
        finally:
            db.close()

# Singleton
_orchestrator: Optional[BotOrchestrator] = None

def get_orchestrator() -> BotOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BotOrchestrator()
    return _orchestrator
