#!/usr/bin/env python3
"""
Example: Advanced Trading Bot with SQLite Integration
Stores price history locally and detects trends.
"""

import requests
import sqlite3
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000"
DB_PATH = Path("bot_data.db")


def init_db():
    """Initialize local SQLite for the bot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            condition TEXT,
            target_price REAL,
            active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def record_price(item_name: str, source: str, price: float):
    """Record a price snapshot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_snapshots (item_name, source, price, timestamp) VALUES (?, ?, ?, ?)",
        (item_name, source, price, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_price_trend(item_name: str, source: str = "steam", hours: int = 24) -> dict:
    """Analyze price trend over time."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT price, timestamp FROM price_snapshots 
           WHERE item_name = ? AND source = ? 
           ORDER BY timestamp DESC LIMIT 50""",
        (item_name, source)
    )
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 2:
        return {"trend": "insufficient_data", "change_pct": 0}
    
    recent = rows[0][0]
    older = rows[-1][0]
    change_pct = ((recent - older) / older) * 100
    
    trend = "stable"
    if change_pct > 5:
        trend = "rising"
    elif change_pct < -5:
        trend = "falling"
    
    return {"trend": trend, "change_pct": change_pct, "samples": len(rows)}


def scan_market(watchlist: list, source: str = "steam"):
    """Scan multiple items and record prices."""
    for item_query in watchlist:
        try:
            r = requests.get(f"{BASE_URL}/api/v1/items/search", params={
                "q": item_query,
                "source": source,
                "page_size": 1,
            }, timeout=10)
            data = r.json()
            
            if data["items"]:
                item = data["items"][0]
                price = item.get("price")
                if price:
                    record_price(item["name"], source, price)
                    trend = get_price_trend(item["name"], source)
                    print(f"[{datetime.now().strftime('%H:%M')}] {item['name']}: {price} CNY | Trend: {trend['trend']} ({trend['change_pct']:+.1f}%)")
                    
        except Exception as e:
            print(f"Error scanning {item_query}: {e}")
        
        time.sleep(1)


if __name__ == "__main__":
    init_db()
    
    WATCHLIST = [
        "AK-47",
        "M4A4",
        "AWP",
        "Desert Eagle",
        "Gloves",
    ]
    
    print("Starting market scanner...")
    print(f"Watching: {', '.join(WATCHLIST)}")
    print("Press Ctrl+C to stop\n")
    
    while True:
        scan_market(WATCHLIST)
        time.sleep(60)  # Scan every minute
