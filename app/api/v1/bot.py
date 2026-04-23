"""
Trading bot API endpoints.
Refactored to use SQLAlchemy models instead of raw sqlite3.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.models import (
    BotStatus, ArbitrageOpportunity, InvestmentRecommendation,
    MarketInsight, WatchlistItem, OpportunityHistory, WebhookConfig,
)
from app.services.bot_engine import get_bot_sync
from app.services.job_queue import job_queue
from app.services.bot.webhook_notifier import WebhookNotifier

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])

@router.get("/status")
async def bot_status(db: Session = Depends(get_db)):
    """Get bot running status."""
    row = db.query(BotStatus).filter(BotStatus.id == 1).first()
    if row:
        return {
            "running": row.running,
            "last_scan": row.last_scan.isoformat() if row.last_scan else None,
            "arbitrage_count": row.arbitrage_count,
            "recommendation_count": row.recommendation_count,
            "scan_count": row.scan_count,
        }
    return {"running": False, "last_scan": None, "arbitrage_count": 0, "recommendation_count": 0, "scan_count": 0}

@router.get("/arbitrage")
async def get_arbitrage(limit: int = 20, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get current arbitrage opportunities."""
    rows = db.query(ArbitrageOpportunity).order_by(ArbitrageOpportunity.spread_pct.desc()).limit(limit).all()
    return [
        {
            "item_name": r.item_name,
            "buy_source": r.buy_source,
            "buy_price": r.buy_price,
            "sell_source": r.sell_source,
            "sell_price": r.sell_price,
            "spread": r.spread,
            "spread_pct": r.spread_pct,
            "item_id": r.item_id,
            "confidence": r.confidence,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]

@router.get("/recommendations")
async def get_recommendations(
    item_type: str = None,
    confidence: str = None,
    limit: int = 30,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get investment recommendations."""
    query = db.query(InvestmentRecommendation)
    if item_type:
        query = query.filter(InvestmentRecommendation.item_type == item_type)
    if confidence:
        query = query.filter(InvestmentRecommendation.confidence == confidence)
    rows = query.order_by(InvestmentRecommendation.expected_roi_pct.desc()).limit(limit).all()
    return [
        {
            "item_name": r.item_name,
            "item_type": r.item_type,
            "current_price": r.current_price,
            "target_price": r.target_price,
            "reasoning": r.reasoning,
            "confidence": r.confidence,
            "timeframe": r.timeframe,
            "expected_roi_pct": r.expected_roi_pct,
            "source": r.source,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]

@router.get("/insights")
async def get_insights(limit: int = 10, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get market insights."""
    rows = db.query(MarketInsight).order_by(
        MarketInsight.severity.desc(), MarketInsight.id.desc()
    ).limit(limit).all()
    return [
        {
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "severity": r.severity,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]

async def _run_scan_task():
    """Background task for bot scan via job queue."""
    from app.services.bot_engine import get_bot_sync
    bot = get_bot_sync()
    try:
        await bot.run_scan()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Manual bot scan failed: {e}")

@router.post("/trigger-scan")
async def trigger_scan():
    """Manually trigger a bot scan. Runs via job queue so HTTP responds immediately."""
    job_id = job_queue.submit("bot_scan", _run_scan_task)
    return {"status": "success", "message": "Scan queued", "job_id": job_id}

@router.get("/stats")
async def bot_stats(db: Session = Depends(get_db)):
    """Get aggregated bot statistics."""
    arb_count = db.query(ArbitrageOpportunity).count()
    rec_count = db.query(InvestmentRecommendation).count()
    high_conf = db.query(InvestmentRecommendation).filter(InvestmentRecommendation.confidence == "high").count()
    avg_roi = db.query(InvestmentRecommendation.expected_roi_pct).scalar() or 0
    by_type = {}
    for row in db.query(InvestmentRecommendation.item_type, InvestmentRecommendation.id).all():
        by_type[row[0]] = by_type.get(row[0], 0) + 1
    
    return {
        "arbitrage_opportunities": arb_count,
        "total_recommendations": rec_count,
        "high_confidence": high_conf,
        "average_expected_roi": round(avg_roi, 2),
        "by_type": by_type,
    }

# Watchlist endpoints

@router.get("/watchlist")
async def get_watchlist(db: Session = Depends(get_db)):
    """Get active watchlist items."""
    from app.services.bot.watchlist_manager import WatchlistManager
    return WatchlistManager.get_items(db, active_only=True)

@router.post("/watchlist")
async def add_watchlist_item(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Add an item to the watchlist."""
    from app.services.bot.watchlist_manager import WatchlistManager
    try:
        row_id = WatchlistManager.add_item(
            db,
            item_name=data.get("item_name", ""),
            target_price=float(data.get("target_price", 0)),
            condition=data.get("condition", "below")
        )
        return {"id": row_id, "status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/watchlist/{watch_id}")
async def remove_watchlist_item(watch_id: int, db: Session = Depends(get_db)):
    """Remove an item from the watchlist."""
    from app.services.bot.watchlist_manager import WatchlistManager
    if WatchlistManager.remove_item(db, watch_id):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Watchlist item not found")

# Webhook endpoints

@router.get("/webhooks")
async def get_webhooks(db: Session = Depends(get_db)):
    """Get all webhook configurations."""
    return WebhookNotifier.get_webhooks(db, active_only=False)

@router.post("/webhooks")
async def add_webhook(data: Dict[str, Any], db: Session = Depends(get_db)):
    """Add a webhook for external notifications (Discord, Telegram, generic)."""
    try:
        row_id = WebhookNotifier.add_webhook(
            db,
            name=data.get("name", ""),
            webhook_type=data.get("webhook_type", "generic"),
            url=data.get("url", ""),
            events=data.get("events", "watchlist_trigger,high_confidence_arbitrage"),
        )
        return {"id": row_id, "status": "added"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/webhooks/{webhook_id}")
async def remove_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Remove a webhook configuration."""
    if WebhookNotifier.remove_webhook(db, webhook_id):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Webhook not found")

@router.post("/webhooks/test/{webhook_id}")
async def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Send a test notification to a webhook."""
    wh = db.query(WebhookConfig).filter(WebhookConfig.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    success = await WebhookNotifier._send_single(
        {"url": wh.url, "webhook_type": wh.webhook_type},
        {"event": "test", "message": "CS2 Price Scraper test notification — your webhook is working!"},
    )
    if success:
        return {"status": "delivered"}
    return {"status": "failed", "detail": "Webhook delivery failed. Check the URL and try again."}

# Opportunity history endpoint

@router.get("/history")
async def get_opportunity_history(days: int = 30, db: Session = Depends(get_db)):
    """Get daily opportunity history for charting."""
    rows = db.query(OpportunityHistory).order_by(OpportunityHistory.date.desc()).limit(days).all()
    return [
        {
            "date": r.date,
            "arbitrage_count": r.arbitrage_count,
            "recommendation_count": r.recommendation_count,
            "avg_roi": r.avg_roi,
        }
        for r in rows
    ]

# CSV Export endpoints

@router.get("/export/arbitrage")
async def export_arbitrage_csv(db: Session = Depends(get_db)):
    """Export arbitrage opportunities as CSV."""
    import csv
    import io
    
    rows = db.query(ArbitrageOpportunity).order_by(ArbitrageOpportunity.spread_pct.desc()).all()
    output = io.StringIO()
    if rows:
        fieldnames = ["item_name", "buy_source", "buy_price", "sell_source", "sell_price", "spread", "spread_pct", "confidence"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "item_name": r.item_name, "buy_source": r.buy_source, "buy_price": r.buy_price,
                "sell_source": r.sell_source, "sell_price": r.sell_price,
                "spread": r.spread, "spread_pct": r.spread_pct, "confidence": r.confidence,
            })
    
    return {
        "filename": f"arbitrage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
        "content": output.getvalue(),
    }

@router.get("/export/recommendations")
async def export_recommendations_csv(db: Session = Depends(get_db)):
    """Export investment recommendations as CSV."""
    import csv
    import io
    
    rows = db.query(InvestmentRecommendation).order_by(InvestmentRecommendation.expected_roi_pct.desc()).all()
    output = io.StringIO()
    if rows:
        fieldnames = ["item_name", "item_type", "current_price", "target_price", "expected_roi_pct", "confidence", "timeframe"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "item_name": r.item_name, "item_type": r.item_type,
                "current_price": r.current_price, "target_price": r.target_price,
                "expected_roi_pct": r.expected_roi_pct, "confidence": r.confidence, "timeframe": r.timeframe,
            })
    
    return {
        "filename": f"recommendations_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
        "content": output.getvalue(),
    }
