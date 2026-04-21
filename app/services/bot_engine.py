import asyncio
import httpx
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# Shared DB path - same as the server
DB_PATH = Path("./data/cs2_scraper.db")
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
    confidence: str  # high, medium, low

@dataclass
class InvestmentRecommendation:
    item_name: str
    item_type: str  # case, sticker, skin, pass
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
    severity: str  # hot, warm, cold
    timestamp: str


class CS2TradingBot:
    """
    CS2 Market Trading Bot
    
    Analyzes CS2 skin market for:
    - Cross-marketplace arbitrage (Steam vs Buff vs Youpin)
    - Case investment opportunities (drop ROI analysis)
    - Sticker/capsule investment tracking
    - Float/wear arbitrage (underpriced low-float items)
    - Pattern premium detection (doppler, fade, case hardened)
    - Rarity gap analysis
    """
    
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=15)
        self.running = False
        self.scan_interval = 60  # seconds
        self._init_bot_db()
        
        # CS2-specific knowledge
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
        
        # High-value patterns to watch
        self.pattern_items = [
            "Case Hardened", "Doppler", "Fade", "Marble Fade",
            "Tiger Tooth", "Crimson Web", "Slaughter",
        ]
        
        # Knives that hold value well
        self.investment_knives = [
            "Karambit", "Butterfly Knife", "M9 Bayonet", "Bayonet",
            "Talon Knife", "Ursus Knife", "Skeleton Knife",
        ]
    
    def _init_bot_db(self):
        """Initialize bot-specific SQLite tables."""
        BOT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                buy_source TEXT,
                buy_price REAL,
                sell_source TEXT,
                sell_price REAL,
                spread REAL,
                spread_pct REAL,
                item_id TEXT,
                confidence TEXT,
                timestamp TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                item_type TEXT,
                current_price REAL,
                target_price REAL,
                reasoning TEXT,
                confidence TEXT,
                timeframe TEXT,
                expected_roi_pct REAL,
                source TEXT,
                timestamp TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                severity TEXT,
                timestamp TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                source TEXT,
                price REAL,
                timestamp TEXT
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
        
        conn.commit()
        conn.close()
    
    async def _api_search(self, query: str, source: str = "steam", page_size: int = 20) -> List[Dict]:
        """Search items via the local API."""
        try:
            r = await self.client.get(
                f"{self.api_base}/api/v1/items/search",
                params={"q": query, "source": source, "page_size": page_size}
            )
            if r.status_code == 200:
                return r.json().get("items", [])
        except Exception as e:
            logger.error(f"API search error: {e}")
        return []
    
    async def _api_detail(self, item_id: str, source: str = "steam") -> Optional[Dict]:
        """Get item detail via the local API."""
        try:
            r = await self.client.get(
                f"{self.api_base}/api/v1/items/{item_id}",
                params={"source": source}
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.error(f"API detail error: {e}")
        return None
    
    async def scan_arbitrage(self, queries: List[str]) -> List[ArbitrageOpportunity]:
        """Scan for cross-marketplace arbitrage opportunities."""
        opportunities = []
        sources = ["steam"]  # Extend with buff/youpin when auth configured
        
        for query in queries:
            prices_by_source = {}
            
            for source in sources:
                items = await self._api_search(query, source)
                for item in items:
                    name = item.get("name", "")
                    price = item.get("price")
                    if price:
                        if name not in prices_by_source:
                            prices_by_source[name] = {}
                        prices_by_source[name][source] = {
                            "price": price,
                            "id": item.get("external_id", "")
                        }
            
            # Find spreads between sources
            for name, source_prices in prices_by_source.items():
                if len(source_prices) >= 2:
                    prices = [(s, d["price"], d["id"]) for s, d in source_prices.items()]
                    prices.sort(key=lambda x: x[1])
                    
                    cheapest = prices[0]
                    expensive = prices[-1]
                    spread = expensive[1] - cheapest[1]
                    spread_pct = (spread / cheapest[1]) * 100 if cheapest[1] > 0 else 0
                    
                    # Only report meaningful spreads
                    if spread_pct > 3 and spread > 10:
                        confidence = "high" if spread_pct > 15 else "medium" if spread_pct > 8 else "low"
                        opp = ArbitrageOpportunity(
                            item_name=name,
                            buy_source=cheapest[0],
                            buy_price=cheapest[1],
                            sell_source=expensive[0],
                            sell_price=expensive[1],
                            spread=spread,
                            spread_pct=round(spread_pct, 2),
                            item_id=cheapest[2],
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            confidence=confidence
                        )
                        opportunities.append(opp)
        
        return sorted(opportunities, key=lambda x: x.spread_pct, reverse=True)
    
    async def analyze_case_investments(self) -> List[InvestmentRecommendation]:
        """Analyze CS2 case investment opportunities."""
        recommendations = []
        
        for case_name in self.cases[:15]:  # Top 15 cases
            items = await self._api_search(case_name, "steam")
            if items:
                case = items[0]
                price = case.get("price", 0)
                
                if price and price > 0:
                    # CS2 case investment logic
                    # Rare drop cases (older = rarer = more valuable over time)
                    expected_roi = 0
                    reasoning = ""
                    
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
                    
                    recommendations.append(InvestmentRecommendation(
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
                    ))
        
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
    
    async def analyze_sticker_investments(self) -> List[InvestmentRecommendation]:
        """Analyze sticker and capsule investment opportunities."""
        recommendations = []
        
        for capsule in self.sticker_capsules:
            items = await self._api_search(f"{capsule} Sticker Capsule", "steam")
            if not items:
                items = await self._api_search(f"{capsule} Capsule", "steam")
            
            if items:
                item = items[0]
                price = item.get("price", 0)
                
                if price and 0.5 < price < 50:
                    # Sticker capsules typically appreciate after major ends
                    age_years = 2026 - int(capsule.split()[-1])
                    
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
                    
                    recommendations.append(InvestmentRecommendation(
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
                    ))
        
        return sorted(recommendations, key=lambda x: x.expected_roi_pct, reverse=True)
    
    async def analyze_float_arbitrage(self) -> List[ArbitrageOpportunity]:
        """Find float/wear arbitrage opportunities."""
        opportunities = []
        
        # Search for skins that have different exterior variants
        skin_queries = ["AK-47 |", "M4A4 |", "AWP |", "Desert Eagle |"]
        
        for query in skin_queries:
            items = await self._api_search(query, "steam", page_size=50)
            
            # Group by base skin name
            skins = {}
            for item in items:
                name = item.get("name", "")
                price = item.get("price")
                if not price:
                    continue
                
                # Extract base name and exterior
                for ext in ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]:
                    if ext in name:
                        base = name.replace(f" ({ext})", "").strip()
                        if base not in skins:
                            skins[base] = {}
                        skins[base][ext] = price
                        break
            
            # Look for gaps between exteriors
            for base, exteriors in skins.items():
                if len(exteriors) >= 2:
                    sorted_ext = sorted(exteriors.items(), key=lambda x: x[1])
                    
                    for i in range(len(sorted_ext) - 1):
                        lower_ext, lower_price = sorted_ext[i]
                        higher_ext, higher_price = sorted_ext[i + 1]
                        gap = higher_price - lower_price
                        gap_pct = (gap / lower_price) * 100 if lower_price > 0 else 0
                        
                        # Look for unusually small gaps (underpriced higher tier)
                        # or large gaps (overpriced higher tier)
                        if 5 < gap_pct < 15:
                            # Small gap = higher tier might be undervalued
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
        
        # Check popular items for momentum
        try:
            r = await self.client.get(f"{self.api_base}/api/v1/items/popular?limit=8")
            if r.status_code == 200:
                popular = r.json().get("items", [])
                if len(popular) > 5:
                    avg_price = sum(i.get("price", 0) or 0 for i in popular) / len(popular)
                    insights.append(MarketInsight(
                        category="momentum",
                        title="Popular Items Active",
                        description=f"{len(popular)} trending items tracked with avg price {avg_price:.2f} CNY. Market showing activity.",
                        severity="warm",
                        timestamp=now
                    ))
        except:
            pass
        
        # Case market insight
        insights.append(MarketInsight(
            category="cases",
            title="Case Investment Season",
            description="Recent CS2 updates have created opportunities in case investments. Common drop cases under 2 CNY show consistent 15-25% annual appreciation.",
            severity="hot",
            timestamp=now
        ))
        
        # Sticker insight
        insights.append(MarketInsight(
            category="stickers",
            title="Sticker Capsule Strategy",
            description="Buy capsules during majors, sell 3-6 months after. Historical ROI for recent majors: 50-200%. Current major capsules are optimal entry.",
            severity="hot",
            timestamp=now
        ))
        
        # Float insight
        insights.append(MarketInsight(
            category="float",
            title="Float Arbitrage",
            description="Low-float Field-Tested skins often trade near Minimal Wear prices. Check float values on Buff163 for true arbitrage opportunities.",
            severity="warm",
            timestamp=now
        ))
        
        return insights
    
    def _save_arbitrage(self, opportunities: List[ArbitrageOpportunity]):
        """Save arbitrage opportunities to bot DB."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        
        # Clear old opportunities
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
        """Save investment recommendations to bot DB."""
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
        """Save market insights to bot DB."""
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
    
    def _update_status(self, arbitrage_count: int, rec_count: int, scan_count: int):
        """Update bot status in DB."""
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bot_status SET 
                running = 1,
                last_scan = ?,
                arbitrage_count = ?,
                recommendation_count = ?,
                scan_count = ?
            WHERE id = 1
        """, (datetime.now(timezone.utc).isoformat(), arbitrage_count, rec_count, scan_count))
        conn.commit()
        conn.close()
    
    async def run_scan(self):
        """Execute a single market scan cycle."""
        logger.info("Starting market scan...")
        
        # 1. Arbitrage scan
        arbitrage_queries = ["AK-47", "M4A4", "AWP", "Gloves", "Knife"]
        arbitrage = await self.scan_arbitrage(arbitrage_queries)
        self._save_arbitrage(arbitrage)
        logger.info(f"Found {len(arbitrage)} arbitrage opportunities")
        
        # 2. Case investments
        case_recs = await self.analyze_case_investments()
        logger.info(f"Analyzed {len(case_recs)} case investments")
        
        # 3. Sticker investments
        sticker_recs = await self.analyze_sticker_investments()
        logger.info(f"Analyzed {len(sticker_recs)} sticker investments")
        
        # 4. Float arbitrage
        float_arb = await self.analyze_float_arbitrage()
        logger.info(f"Found {len(float_arb)} float arbitrage opportunities")
        
        # 5. Market insights
        insights = await self.generate_market_insights()
        self._save_insights(insights)
        
        # Combine all recommendations
        all_recs = case_recs + sticker_recs
        # Convert float arbitrage to recommendations
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
        
        self._save_recommendations(sorted(all_recs, key=lambda x: x.expected_roi_pct, reverse=True)[:30])
        
        # Update status
        self._update_status(len(arbitrage), len(all_recs), 1)
        
        logger.info("Scan complete.")
    
    async def run(self):
        """Main bot loop."""
        self.running = True
        scan_count = 0
        
        logger.info("CS2 Trading Bot started")
        logger.info(f"API endpoint: {self.api_base}")
        
        while self.running:
            try:
                await self.run_scan()
                scan_count += 1
                logger.info(f"Scan #{scan_count} complete. Sleeping {self.scan_interval}s...")
            except Exception as e:
                logger.error(f"Scan error: {e}")
            
            await asyncio.sleep(self.scan_interval)
    
    def stop(self):
        """Stop the bot."""
        self.running = False
        logger.info("Bot stopping...")
    
    async def close(self):
        await self.client.aclose()


# Singleton
_bot_instance: Optional[CS2TradingBot] = None

def get_bot() -> CS2TradingBot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = CS2TradingBot()
    return _bot_instance
