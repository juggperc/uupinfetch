from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sqlite3
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])
BOT_DB_PATH = Path("./data/bot_analysis.db")

@router.get("/status")
async def bot_status():
    """Get bot running status."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_status WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {"running": 0, "last_scan": None, "arbitrage_count": 0, "recommendation_count": 0, "scan_count": 0}
    except:
        return {"running": 0, "last_scan": None, "arbitrage_count": 0, "recommendation_count": 0, "scan_count": 0}

@router.get("/arbitrage")
async def get_arbitrage(limit: int = 20) -> List[Dict[str, Any]]:
    """Get current arbitrage opportunities."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM arbitrage_opportunities ORDER BY spread_pct DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        return []

@router.get("/recommendations")
async def get_recommendations(
    item_type: str = None,
    confidence: str = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """Get investment recommendations."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM investment_recommendations WHERE 1=1"
        params = []
        
        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)
        if confidence:
            query += " AND confidence = ?"
            params.append(confidence)
        
        query += " ORDER BY expected_roi_pct DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        return []

@router.get("/insights")
async def get_insights(limit: int = 10) -> List[Dict[str, Any]]:
    """Get market insights."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM market_insights ORDER BY severity DESC, id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        return []

@router.post("/trigger-scan")
async def trigger_scan():
    """Manually trigger a bot scan."""
    from app.services.bot_engine import get_bot_sync
    
    bot = get_bot_sync()
    try:
        await bot.run_scan()
        return {"status": "success", "message": "Scan completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/stats")
async def bot_stats():
    """Get aggregated bot statistics."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM arbitrage_opportunities")
        arb_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM investment_recommendations")
        rec_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM investment_recommendations WHERE confidence = 'high'")
        high_conf = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(expected_roi_pct) FROM investment_recommendations")
        avg_roi = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT item_type, COUNT(*) as count FROM investment_recommendations GROUP BY item_type")
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "arbitrage_opportunities": arb_count,
            "total_recommendations": rec_count,
            "high_confidence": high_conf,
            "average_expected_roi": round(avg_roi, 2),
            "by_type": by_type,
        }
    except:
        return {
            "arbitrage_opportunities": 0,
            "total_recommendations": 0,
            "high_confidence": 0,
            "average_expected_roi": 0,
            "by_type": {},
        }

# Watchlist endpoints

@router.get("/watchlist")
async def get_watchlist():
    """Get active watchlist items."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist WHERE active = 1 ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class WatchlistCreate:
    item_name: str
    target_price: float
    condition: str = "below"

@router.post("/watchlist")
async def add_watchlist_item(data: Dict[str, Any]):
    """Add an item to the watchlist."""
    from app.services.bot_engine import get_bot_sync
    bot = get_bot_sync()
    try:
        row_id = bot.add_watchlist(
            item_name=data.get("item_name", ""),
            target_price=float(data.get("target_price", 0)),
            condition=data.get("condition", "below")
        )
        return {"id": row_id, "status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/watchlist/{watch_id}")
async def remove_watchlist_item(watch_id: int):
    """Remove an item from the watchlist."""
    from app.services.bot_engine import get_bot_sync
    bot = get_bot_sync()
    if bot.remove_watchlist(watch_id):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Watchlist item not found")

# Opportunity history endpoint

@router.get("/history")
async def get_opportunity_history(days: int = 30):
    """Get daily opportunity history for charting."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM opportunity_history ORDER BY date DESC LIMIT ?",
            (days,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CSV Export endpoints

@router.get("/export/arbitrage")
async def export_arbitrage_csv():
    """Export arbitrage opportunities as CSV."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM arbitrage_opportunities ORDER BY spread_pct DESC")
        rows = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            writer.writerows([dict(r) for r in rows])
        
        return {
            "filename": f"arbitrage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
            "content": output.getvalue()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/recommendations")
async def export_recommendations_csv():
    """Export investment recommendations as CSV."""
    try:
        conn = sqlite3.connect(BOT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM investment_recommendations ORDER BY expected_roi_pct DESC")
        rows = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
            writer.writeheader()
            writer.writerows([dict(r) for r in rows])
        
        return {
            "filename": f"recommendations_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
            "content": output.getvalue()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
