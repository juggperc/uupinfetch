import asyncio
import httpx
import sqlite3
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.market_fees import calculate_spread, get_fee
from app.services.pattern_engine import get_pattern_alert

BOT_DB_PATH = Path("./data/bot_analysis.db")

logger = logging.getLogger("cs2_bot")

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

@dataclass
class MarketInsight:
    category: str
    title: str
    description: str
    severity: str
    timestamp: str


class CS2TradingBot:
    """CS2 Market Trading Bot with retry logic, caching, and rate limiting."""
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=15)
        self.running = False
        self.scan_interval = 60
        self.scan_count = 0
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 30  # seconds
        self._last_api_call = 0
        self._min_api_delay = 0.5  # Rate limit: 500ms between API calls
        self._init_bot_db()
        
        self.cases = [
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
        
        self.sticker_capsules = [
            "Copenhagen 2024", "Paris 2023", "Rio 2022", "Antwerp 2022",
            "Stockholm 2021", "Berlin 2019", "Katowice 2019",
        ]
        
        self.pattern_items = [
            "Case Hardened", "Doppler", "Fade", "Marble Fade",
            "Tiger Tooth", "Crimson Web", "Slaughter",
        ]
        
        self.investment_knives = [
            "Karambit", "Butterfly Knife", "M9 Bayonet", "Bayonet",
            "Talon Knife", "Ursus Knife", "Skeleton Knife",
        ]
    
    def _init_bot_db(self):
        BOT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT, buy_source TEXT, buy_price REAL,
                sell_source TEXT, sell_price REAL, spread REAL, spread_pct REAL,
                item_id TEXT, confidence TEXT, timestamp TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT, item_type TEXT, current_price REAL,
                target_price REAL, reasoning TEXT, confidence TEXT,
                timeframe TEXT, expected_roi_pct REAL, source TEXT,
                timestamp TEXT, discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, title TEXT, description TEXT,
                severity TEXT, timestamp TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT, source TEXT, price REAL, timestamp TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                running INTEGER DEFAULT 0,
                last_scan TEXT,
                arbitrage_count INTEGER DEFAULT 0,
                recommendation_count INTEGER DEFAULT 0,
                scan_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO bot_status (id) VALUES (1)")
        
        # New: watchlist table for price alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                target_price REAL,
                condition TEXT DEFAULT 'below',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # New: opportunity history for charts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                arbitrage_count INTEGER,
                recommendation_count INTEGER,
                avg_roi REAL
            )
        """)
        
        # New: webhooks for external notifications (Telegram, Discord, generic)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                webhook_type TEXT DEFAULT 'generic',
                url TEXT NOT NULL,
                events TEXT DEFAULT 'watchlist_trigger,high_confidence_arbitrage',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def _rate_limited_api_call(self, method: str, url: str, **kwargs):
        """Make API call with rate limiting and exponential backoff retry."""
        now = time.time()
        elapsed = now - self._last_api_call
        if elapsed < self._min_api_delay:
            await asyncio.sleep(self._min_api_delay - elapsed)
        
        for attempt in range(3):
            try:
                self._last_api_call = time.time()
                if method == "GET":
                    r = await self.client.get(url, **kwargs)
                else:
                    r = await self.client.post(url, **kwargs)
                return r
            except Exception as e:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"API call failed (attempt {attempt+1}/3), retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
        
        return None
    
    async def _direct_search(self, query: str, source: str = "steam", page_size: int = 20) -> List[Dict]:
        """Search items by calling scraper services directly (no HTTP loopback).
        Much faster and more reliable than calling the local API."""
        cache_key = f"search:{query}:{source}:{page_size}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached["time"] < self._cache_ttl):
            return cached["data"]
        
        from app.services.steam import steam_scraper
        from app.services.skinport import skinport_scraper
        from app.services.buff import buff_scraper
        from app.services.youpin import youpin_scraper
        from app.core.config import get_settings
        settings = get_settings()
        
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
        
        self._cache[cache_key] = {"data": all_items, "time": time.time()}
        return all_items
    
    async def _direct_detail(self, item_id: str, source: str = "steam") -> Optional[Dict]:
        """Get item detail by calling scraper services directly."""
        cache_key = f"detail:{item_id}:{source}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached["time"] < self._cache_ttl):
            return cached["data"]
        
        from app.services.steam import steam_scraper
        result = None
        
        try:
            if source == "steam":
                price_data = await steam_scraper.get_price_overview(item_id)
                if price_data:
                    result = {
                        "source": "steam",
                        "external_id": item_id,
                        "name": item_id.replace("%20", " "),
                        "price": price_data.get("lowest_price"),
                        "image_url": f"https://steamcommunity-a.akamaihd.net/economy/image/{item_id}",
                        "hash_name": item_id,
                    }
        except Exception as e:
            logger.debug(f"Direct detail fetch failed: {e}")
        
        if result:
            self._cache[cache_key] = {"data": result, "time": time.time()}
        return result
    
    async def scan_arbitrage(self, queries: List[str]) -> List[ArbitrageOpportunity]:
        """Scan for cross-marketplace arbitrage opportunities across all enabled sources.
        Uses fee-adjusted net spread for accurate profitability calculation.
        Searches are run concurrently for speed."""
        
        # Fetch all queries concurrently
        async def search_one(query: str):
            try:
                return await self._direct_search(query, source="all", page_size=50)
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
    
    async def analyze_case_investments(self) -> List[InvestmentRecommendation]:
        """Analyze CS2 case investment opportunities. Searches are concurrent."""
        async def analyze_one(case_name: str):
            try:
                items = await self._direct_search(case_name, "steam")
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
        
        results = await asyncio.gather(*[analyze_one(c) for c in self.cases[:15]])
        recommendations = [r for r in results if r is not None]
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
    
    async def analyze_sticker_investments(self) -> List[InvestmentRecommendation]:
        """Analyze sticker and capsule investment opportunities. Searches are concurrent."""
        async def analyze_one(capsule: str):
            try:
                items = await self._direct_search(f"{capsule} Sticker Capsule", "steam")
                if not items:
                    items = await self._direct_search(f"{capsule} Capsule", "steam")
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
        
        results = await asyncio.gather(*[analyze_one(c) for c in self.sticker_capsules])
        recommendations = [r for r in results if r is not None]
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
    
    async def analyze_float_arbitrage(self) -> List[ArbitrageOpportunity]:
        """Find float/wear arbitrage opportunities. Searches are concurrent."""
        skin_queries = ["AK-47 |", "M4A4 |", "AWP |", "Desert Eagle |"]
        
        async def search_one(query: str):
            try:
                return await self._direct_search(query, "steam", page_size=50)
            except Exception:
                return []
        
        all_results = await asyncio.gather(*[search_one(q) for q in skin_queries])
        opportunities = []
        
        for items in all_results:
            skins = {}
            for item in items:
                name = item.get("name", "")
                price = item.get("price")
                if not price:
                    continue
                
                for ext in ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]:
                    if ext in name:
                        base = name.replace(f" ({ext})", "").strip()
                        if base not in skins:
                            skins[base] = {}
                        skins[base][ext] = price
                        break
            
            for base, exteriors in skins.items():
                if len(exteriors) >= 2:
                    sorted_ext = sorted(exteriors.items(), key=lambda x: x[1])
                    
                    for i in range(len(sorted_ext) - 1):
                        lower_ext, lower_price = sorted_ext[i]
                        higher_ext, higher_price = sorted_ext[i + 1]
                        gap = higher_price - lower_price
                        gap_pct = (gap / lower_price) * 100 if lower_price > 0 else 0
                        
                        if 5 < gap_pct < 15:
                            opportunities.append(ArbitrageOpportunity(
                                item_name=f"{base} ({higher_ext})",
                                buy_source="steam",
                                buy_price=higher_price,
                                sell_source="expected",
                                sell_price=round(higher_price * 1.2, 2),
                                spread=round(gap, 2),
                                spread_pct=round(gap_pct, 2),
                                item_id="",
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                confidence="medium"
                            ))
        
        return opportunities[:20]
    
    async def generate_market_insights(self) -> List[MarketInsight]:
        """Generate CS2 market insights."""
        insights = []
        now = datetime.now(timezone.utc).isoformat()
        
        insights.append(MarketInsight(
            category="cases",
            title="Case Investment Season",
            description="Recent CS2 updates have created opportunities in case investments. Common drop cases under 2 CNY show consistent 15-25% annual appreciation.",
            severity="hot",
            timestamp=now
        ))
        
        insights.append(MarketInsight(
            category="stickers",
            title="Sticker Capsule Strategy",
            description="Buy capsules during majors, sell 3-6 months after. Historical ROI for recent majors: 50-200%. Current major capsules are optimal entry.",
            severity="hot",
            timestamp=now
        ))
        
        insights.append(MarketInsight(
            category="float",
            title="Float Arbitrage",
            description="Low-float Field-Tested skins often trade near Minimal Wear prices. Check float values on Buff163 for true arbitrage opportunities.",
            severity="warm",
            timestamp=now
        ))
        
        return insights
    
    def _save_arbitrage(self, opportunities: List[ArbitrageOpportunity]):
        """Save arbitrage opportunities. If the list is empty, preserve existing data
        to avoid wiping the UI when APIs are rate-limited or down."""
        if not opportunities:
            logger.warning("Arbitrage scan returned empty — preserving existing data")
            return
        
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM arbitrage_opportunities")
        
        for opp in opportunities:
            cursor.execute("""
                INSERT INTO arbitrage_opportunities 
                (item_name, buy_source, buy_price, sell_source, sell_price, spread, spread_pct, item_id, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (opp.item_name, opp.buy_source, opp.buy_price, opp.sell_source, opp.sell_price,
                  opp.spread, opp.spread_pct, opp.item_id, opp.confidence, opp.timestamp))
        
        conn.commit()
        conn.close()
    
    def _save_recommendations(self, recommendations: List[InvestmentRecommendation]):
        """Save recommendations. If the list is empty, preserve existing data."""
        if not recommendations:
            logger.warning("Recommendation scan returned empty — preserving existing data")
            return
        
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM investment_recommendations")
        
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO investment_recommendations
                (item_name, item_type, current_price, target_price, reasoning, confidence, timeframe, expected_roi_pct, source, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rec.item_name, rec.item_type, rec.current_price, rec.target_price,
                  rec.reasoning, rec.confidence, rec.timeframe, rec.expected_roi_pct, rec.source, rec.timestamp))
        
        conn.commit()
        conn.close()
    
    def _save_insights(self, insights: List[MarketInsight]):
        """Save market insights. If the list is empty, preserve existing data."""
        if not insights:
            logger.warning("Insights generation returned empty — preserving existing data")
            return
        
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM market_insights")
        
        for insight in insights:
            cursor.execute("""
                INSERT INTO market_insights (category, title, description, severity, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (insight.category, insight.title, insight.description, insight.severity, insight.timestamp))
        
        conn.commit()
        conn.close()
    
    def _update_status(self, arbitrage_count: int, rec_count: int):
        """Update bot status in DB with actual scan_count."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bot_status SET 
                running = 1,
                last_scan = ?,
                arbitrage_count = ?,
                recommendation_count = ?,
                scan_count = scan_count + 1
            WHERE id = 1
        """, (datetime.now(timezone.utc).isoformat(), arbitrage_count, rec_count))
        conn.commit()
        conn.close()
    
    def _record_opportunity_history(self, arb_count: int, rec_count: int, avg_roi: float):
        """Record daily opportunity history for charts."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        cursor.execute(
            "INSERT OR REPLACE INTO opportunity_history (date, arbitrage_count, recommendation_count, avg_roi) VALUES (?, ?, ?, ?)",
            (today, arb_count, rec_count, avg_roi)
        )
        conn.commit()
        conn.close()
    
    # Watchlist management
    def add_watchlist(self, item_name: str, target_price: float, condition: str = "below") -> int:
        """Add an item to the watchlist."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO watchlist (item_name, target_price, condition) VALUES (?, ?, ?)",
            (item_name, target_price, condition)
        )
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id
    
    def remove_watchlist(self, watch_id: int) -> bool:
        """Remove an item from the watchlist."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE id = ?", (watch_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed
    
    def get_watchlist(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get watchlist items."""
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM watchlist WHERE active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM watchlist ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    # Webhook management
    def add_webhook(self, name: str, webhook_type: str, url: str, events: str) -> int:
        """Add a webhook configuration."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO webhooks (name, webhook_type, url, events) VALUES (?, ?, ?, ?)",
            (name, webhook_type, url, events)
        )
        row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return row_id
    
    def remove_webhook(self, webhook_id: int) -> bool:
        """Remove a webhook configuration."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed
    
    def get_webhooks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get webhook configurations."""
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM webhooks WHERE active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM webhooks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    async def _send_webhook(self, webhook: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        """Send a notification to a single webhook. Failures are logged, not raised."""
        import httpx
        url = webhook.get("url", "")
        wh_type = webhook.get("webhook_type", "generic")
        if not url:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                if wh_type == "discord":
                    # Discord expects {content: str} or embeds
                    content = payload.get("message", "")
                    await client.post(url, json={"content": content})
                elif wh_type == "telegram":
                    # Telegram bot API: https://api.telegram.org/bot<TOKEN>/sendMessage
                    # User provides full URL including bot token
                    text = payload.get("message", "")
                    # If URL contains /bot, assume it's a proper Telegram API endpoint
                    if "/bot" in url and "sendMessage" not in url:
                        tg_url = f"{url}/sendMessage" if not url.endswith("/") else f"{url}sendMessage"
                    else:
                        tg_url = url
                    await client.post(tg_url, json={"text": text, "parse_mode": "HTML"})
                else:
                    await client.post(url, json=payload)
            return True
        except Exception as e:
            logger.warning(f"Webhook delivery failed for {wh_type}: {e}")
            return False
    
    async def notify_webhooks(self, event_type: str, data: Dict[str, Any]):
        """Notify all webhooks subscribed to a given event type."""
        webhooks = self.get_webhooks(active_only=True)
        if not webhooks:
            return
        
        for wh in webhooks:
            events = wh.get("events", "")
            if event_type not in events:
                continue
            
            wh_type = wh.get("webhook_type", "generic")
            message = data.get("message", "")
            payload = {"event": event_type, "message": message, "data": data}
            
            # Format message for chat platforms
            if wh_type in ("discord", "telegram"):
                payload["message"] = message
            
            asyncio.create_task(self._send_webhook(wh, payload))
    
    async def scan_pattern_deals(self) -> List[Dict[str, Any]]:
        """Scan for pattern skins that may be underpriced. Searches are concurrent."""
        pattern_queries = ["Case Hardened", "Doppler", "Fade", "Crimson Web", "Marble Fade"]
        
        async def search_one(query: str):
            try:
                items = await self._direct_search(query, source="all", page_size=15)
                alerts = []
                for item in items:
                    name = item.get("name", "")
                    price = item.get("price")
                    seed = item.get("paint_seed")
                    if not price:
                        continue
                    alert = get_pattern_alert(name, price, seed)
                    if alert and alert["tier"] in ("good", "excellent", "god"):
                        alert["source"] = item.get("source", "unknown")
                        alerts.append(alert)
                return alerts
            except Exception as e:
                logger.debug(f"Pattern scan failed for {query}: {e}")
                return []
        
        all_alerts = await asyncio.gather(*[search_one(q) for q in pattern_queries])
        alerts = []
        for batch in all_alerts:
            alerts.extend(batch)
        
        alerts.sort(key=lambda x: x.get("potential_premium_pct", 0), reverse=True)
        return alerts[:20]
    
    async def check_watchlist(self):
        """Check active watchlist items against current prices. Checks are concurrent.
        Sends webhook notifications for triggered alerts."""
        watchlist = self.get_watchlist(active_only=True)
        
        async def check_one(item: Dict[str, Any]):
            try:
                items = await self._direct_search(item["item_name"], source="all", page_size=10)
                for result in items:
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
                        alert = {
                            "watch_id": item["id"],
                            "item_name": item["item_name"],
                            "current_price": price,
                            "target_price": target,
                            "condition": condition,
                            "source": result.get("source", "unknown"),
                        }
                        # Fire webhook notification
                        await self.notify_webhooks("watchlist_trigger", {
                            "message": f"Watchlist Alert: {item['item_name']} is now ¥{price} ({condition} target ¥{target})",
                            "alert": alert,
                        })
                        return alert
            except Exception as e:
                logger.warning(f"Watchlist check failed for {item['item_name']}: {e}")
            return None
        
        results = await asyncio.gather(*[check_one(item) for item in watchlist])
        return [r for r in results if r is not None]
    
    async def run_scan(self):
        """Execute a single market scan cycle with per-step exception handling
        so a failure in one analysis doesn't wipe all data."""
        logger.info("Starting market scan...")
        self.scan_count += 1
        
        # 1. Arbitrage scan
        arbitrage = []
        try:
            arbitrage_queries = ["AK-47", "M4A4", "AWP", "Gloves", "Knife"]
            arbitrage = await self.scan_arbitrage(arbitrage_queries)
            self._save_arbitrage(arbitrage)
            logger.info(f"Found {len(arbitrage)} arbitrage opportunities")
            
            # Notify webhooks for high-confidence arbitrage
            high_conf_arb = [a for a in arbitrage if a.confidence == "high" and a.spread_pct > 10]
            if high_conf_arb:
                top = high_conf_arb[0]
                await self.notify_webhooks("high_confidence_arbitrage", {
                    "message": f"High-Confidence Arbitrage: {top.item_name}\nBuy ¥{top.buy_price} @ {top.buy_source} → Sell ¥{top.sell_price} @ {top.sell_source} ({top.spread_pct}% spread)",
                    "opportunity": {
                        "item_name": top.item_name,
                        "buy_price": top.buy_price,
                        "buy_source": top.buy_source,
                        "sell_price": top.sell_price,
                        "sell_source": top.sell_source,
                        "spread_pct": top.spread_pct,
                    },
                })
        except Exception as e:
            logger.error(f"Arbitrage scan failed: {e}")
        
        # 2. Case investments
        case_recs = []
        try:
            case_recs = await self.analyze_case_investments()
            logger.info(f"Analyzed {len(case_recs)} case investments")
        except Exception as e:
            logger.error(f"Case investment scan failed: {e}")
        
        # 3. Sticker investments
        sticker_recs = []
        try:
            sticker_recs = await self.analyze_sticker_investments()
            logger.info(f"Analyzed {len(sticker_recs)} sticker investments")
        except Exception as e:
            logger.error(f"Sticker investment scan failed: {e}")
        
        # 4. Float arbitrage
        float_arb = []
        try:
            float_arb = await self.analyze_float_arbitrage()
            logger.info(f"Found {len(float_arb)} float arbitrage opportunities")
        except Exception as e:
            logger.error(f"Float arbitrage scan failed: {e}")
        
        # 5. Market insights
        try:
            insights = await self.generate_market_insights()
            self._save_insights(insights)
        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
        
        # 6. Pattern deal alerts
        try:
            pattern_alerts = await self.scan_pattern_deals()
            if pattern_alerts:
                logger.info(f"Pattern deals found: {len(pattern_alerts)} items")
                for pa in pattern_alerts[:5]:
                    logger.info(f"  PATTERN: {pa['item_name']} - {pa['pattern_subtype']} ({pa['tier']}) - potential +{pa['potential_premium_pct']}% premium")
        except Exception as e:
            logger.error(f"Pattern scan failed: {e}")
        
        # 7. Watchlist alerts
        try:
            alerts = await self.check_watchlist()
            if alerts:
                logger.info(f"Watchlist alerts triggered: {len(alerts)} items")
                for alert in alerts:
                    logger.info(f"  ALERT: {alert['item_name']} at {alert['current_price']} (target: {alert['condition']} {alert['target_price']})")
        except Exception as e:
            logger.error(f"Watchlist check failed: {e}")
        
        # Combine all recommendations
        all_recs = case_recs + sticker_recs
        for fa in float_arb[:10]:
            all_recs.append(InvestmentRecommendation(
                item_name=fa.item_name,
                item_type="skin",
                current_price=fa.buy_price,
                target_price=fa.sell_price,
                reasoning=f"Float/wear arbitrage: {fa.item_name} shows {fa.spread_pct}% spread suggesting mispricing.",
                confidence=fa.confidence,
                timeframe="1-4 weeks",
                expected_roi_pct=fa.spread_pct,
                timestamp=fa.timestamp,
                source="float_analysis"
            ))
        
        all_recs = sorted(all_recs, key=lambda x: x.expected_roi_pct, reverse=True)[:30]
        self._save_recommendations(all_recs)
        
        # Record history
        avg_roi = sum(r.expected_roi_pct for r in all_recs) / len(all_recs) if all_recs else 0
        self._record_opportunity_history(len(arbitrage), len(all_recs), avg_roi)
        
        # Update status with proper scan count
        self._update_status(len(arbitrage), len(all_recs))
        
        logger.info(f"Scan #{self.scan_count} complete.")
    
    def _seed_demo_data(self):
        """Seed the bot DB with demo data so the UI isn't empty on first load.
        Each table is seeded independently so partial data doesn't block seeding."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        seeded_any = False
        
        cursor.execute("SELECT COUNT(*) FROM investment_recommendations")
        if cursor.fetchone()[0] == 0:
            demo_recs = [
                ("Revolution Case", "case", 0.85, 1.20, "Common drop case under 1 CNY. Historically appreciates 20-40% annually as it rotates out of active drop pool.", "medium", "6-12 months", 25.0, "steam", now),
                ("Kilowatt Case", "case", 1.50, 2.00, "Mid-tier case with consistent demand. Expected 15-20% gains during major updates.", "medium", "3-6 months", 18.0, "steam", now),
                ("Copenhagen 2024 Capsule", "sticker", 2.50, 4.50, "Current major capsule. Buy before the major ends and they stop dropping. Historical ROI: 50-200% post-major.", "high", "3-6 months post-major", 45.0, "steam", now),
                ("Paris 2023 Capsule", "sticker", 1.80, 2.70, "No longer dropping. Supply is fixed. Demand increases as crafts use them up.", "high", "6-12 months", 25.0, "steam", now),
                ("AK-47 | Redline (Field-Tested)", "skin", 45.0, 55.0, "Stable skin with consistent volume. Low-float FT versions trade near MW prices.", "low", "3-6 months", 12.0, "float_analysis", now),
            ]
            cursor.executemany("""
                INSERT INTO investment_recommendations
                (item_name, item_type, current_price, target_price, reasoning, confidence, timeframe, expected_roi_pct, source, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, demo_recs)
            seeded_any = True
        
        cursor.execute("SELECT COUNT(*) FROM arbitrage_opportunities")
        if cursor.fetchone()[0] == 0:
            demo_arb = [
                ("AK-47 | Redline (Field-Tested)", "buff", 42.50, "skinport", 48.00, 5.50, 12.9, "", "high", now),
                ("M4A4 | Desolate Space (Minimal Wear)", "youpin", 18.00, "buff", 21.50, 3.50, 19.4, "", "medium", now),
                ("AWP | Hyper Beast (Field-Tested)", "skinport", 35.00, "buff", 40.00, 5.00, 14.3, "", "medium", now),
            ]
            cursor.executemany("""
                INSERT INTO arbitrage_opportunities
                (item_name, buy_source, buy_price, sell_source, sell_price, spread, spread_pct, item_id, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, demo_arb)
            seeded_any = True
        
        cursor.execute("SELECT COUNT(*) FROM market_insights")
        if cursor.fetchone()[0] == 0:
            demo_insights = [
                ("cases", "Case Investment Season", "Recent CS2 updates have created opportunities in case investments. Common drop cases under 2 CNY show consistent 15-25% annual appreciation.", "hot", now),
                ("stickers", "Sticker Capsule Strategy", "Buy capsules during majors, sell 3-6 months after. Historical ROI for recent majors: 50-200%. Current major capsules are optimal entry.", "hot", now),
                ("float", "Float Arbitrage", "Low-float Field-Tested skins often trade near Minimal Wear prices. Check float values on Buff163 for true arbitrage opportunities.", "warm", now),
            ]
            cursor.executemany("""
                INSERT INTO market_insights (category, title, description, severity, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, demo_insights)
            seeded_any = True
        
        cursor.execute("SELECT COUNT(*) FROM opportunity_history")
        if cursor.fetchone()[0] == 0:
            demo_hist = [
                ("2026-04-20", 3, 5, 15.2),
                ("2026-04-21", 2, 8, 18.5),
                ("2026-04-22", 3, 5, 14.8),
            ]
            cursor.executemany("""
                INSERT INTO opportunity_history (date, arbitrage_count, recommendation_count, avg_roi)
                VALUES (?, ?, ?, ?)
            """, demo_hist)
            seeded_any = True
        
        cursor.execute("UPDATE bot_status SET recommendation_count = 5, arbitrage_count = 3 WHERE id = 1")
        conn.commit()
        conn.close()
        if seeded_any:
            logger.info("Seeded demo bot data")
    
    async def run(self):
        """Main bot loop."""
        self.running = True
        
        logger.info("CS2 Trading Bot started")
        logger.info(f"API endpoint: {self.api_base}")
        
        # Seed demo data on first startup so UI isn't empty
        self._seed_demo_data()
        
        # Run an initial scan immediately
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
        await self.client.aclose()


# Singleton instance management
_bot_instance: Optional[CS2TradingBot] = None
_bot_lock = asyncio.Lock()

async def get_bot(api_base: str = "http://localhost:8000") -> CS2TradingBot:
    """Get or create the shared bot singleton instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CS2TradingBot(api_base=api_base)
    return _bot_instance

def get_bot_sync(api_base: str = "http://localhost:8000") -> CS2TradingBot:
    """Synchronous version for use outside async contexts (e.g., background threads)."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CS2TradingBot(api_base=api_base)
    return _bot_instance
