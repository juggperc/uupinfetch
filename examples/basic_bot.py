#!/usr/bin/env python3
"""
Example: Basic Trading Bot Integration
Connects to the local CS2 Price Scraper API to monitor prices.
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def search_items(query: str, source: str = "steam") -> list:
    """Search for CS2 items across marketplaces."""
    r = requests.get(f"{BASE_URL}/api/v1/items/search", params={
        "q": query,
        "source": source,
        "page": 1,
        "page_size": 20,
    })
    r.raise_for_status()
    return r.json()["items"]


def get_item_detail(item_id: str, source: str = "steam") -> dict:
    """Get detailed price info for a specific item."""
    r = requests.get(f"{BASE_URL}/api/v1/items/{item_id}", params={"source": source})
    r.raise_for_status()
    return r.json()["item"]


def monitor_price(item_name: str, target_price: float, source: str = "steam"):
    """Monitor an item and alert when price drops below target."""
    print(f"Monitoring '{item_name}' for price <= {target_price} CNY...")
    
    while True:
        try:
            items = search_items(item_name, source)
            if items:
                cheapest = min(items, key=lambda x: x.get("price") or float("inf"))
                price = cheapest.get("price")
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {cheapest['name']}: {price} CNY")
                
                if price and price <= target_price:
                    print(f"ALERT: Price target reached! {price} CNY <= {target_price} CNY")
                    return cheapest
                    
        except requests.RequestException as e:
            print(f"Error: {e}")
        
        time.sleep(30)  # Check every 30 seconds


def find_arbitrage(item_name: str):
    """Compare prices across sources to find arbitrage opportunities."""
    sources = ["steam"]  # Add "buff", "youpin" if authenticated
    prices = {}
    
    for source in sources:
        try:
            items = search_items(item_name, source)
            if items:
                cheapest = min(items, key=lambda x: x.get("price") or float("inf"))
                prices[source] = cheapest.get("price")
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    
    if len(prices) >= 2:
        min_source = min(prices, key=prices.get)
        max_source = max(prices, key=prices.get)
        spread = prices[max_source] - prices[min_source]
        spread_pct = (spread / prices[min_source]) * 100
        
        print(f"\nArbitrage: {item_name}")
        for src, price in prices.items():
            print(f"  {src}: {price} CNY")
        print(f"  Spread: {spread:.2f} CNY ({spread_pct:.1f}%)")
        
        if spread_pct > 5:
            print(f"  OPPORTUNITY DETECTED!")
    else:
        print("Need multiple sources for arbitrage comparison")


if __name__ == "__main__":
    # Example 1: Simple price search
    print("=== Search Example ===")
    items = search_items("AK-47", source="steam")
    for item in items[:5]:
        print(f"  {item['name']}: {item.get('price', 'N/A')} CNY")
    
    # Example 2: Price monitoring
    print("\n=== Price Monitor ===")
    # monitor_price("AK-47 | Redline", target_price=300.0)
    
    # Example 3: Arbitrage finder
    print("\n=== Arbitrage Check ===")
    find_arbitrage("AK-47")
