"""
Marketplace fee configuration for cross-market intelligence.
All fees are expressed as decimals (0.15 = 15%).

Sources:
- Steam: https://steamcommunity.com/market/fee_structure/
- Buff163: ~2.5% seller fee
- Youpin: varies by item, ~2-5%
- Skinport: 12% seller fee (can reduce to 6% with premium)
- CSFloat: 2% seller fee
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class MarketplaceFees:
    """Fee structure for a marketplace."""
    name: str
    name_zh: str
    seller_fee: float = 0.0
    buyer_fee: float = 0.0
    # Steam has a tiered fee structure
    steam_tiered: bool = False
    # Minimum fee in currency units
    min_fee: float = 0.0
    # Additional fixed fee per transaction
    fixed_fee: float = 0.0


# Fee configurations per marketplace
FEES: Dict[str, MarketplaceFees] = {
    "steam": MarketplaceFees(
        name="Steam",
        name_zh="Steam市场",
        seller_fee=0.05,  # 5% base
        buyer_fee=0.10,   # 10% + 5% = 15% total on buyer side
        steam_tiered=True,
        min_fee=0.01,
    ),
    "buff": MarketplaceFees(
        name="Buff163",
        name_zh="网易BUFF",
        seller_fee=0.025,
        buyer_fee=0.0,
    ),
    "youpin": MarketplaceFees(
        name="Youpin",
        name_zh="悠悠有品",
        seller_fee=0.025,
        buyer_fee=0.0,
    ),
    "skinport": MarketplaceFees(
        name="Skinport",
        name_zh="Skinport",
        seller_fee=0.12,
        buyer_fee=0.0,
    ),
    "csfloat": MarketplaceFees(
        name="CSFloat",
        name_zh="CSFloat",
        seller_fee=0.02,
        buyer_fee=0.0,
        fixed_fee=0.0,
    ),
    "ecosteam": MarketplaceFees(
        name="ECOsteam",
        name_zh="ECOsteam",
        seller_fee=0.025,
        buyer_fee=0.0,
    ),
    "c5game": MarketplaceFees(
        name="C5Game",
        name_zh="C5Game",
        seller_fee=0.025,
        buyer_fee=0.0,
    ),
}


def get_fee(source: str) -> MarketplaceFees:
    """Get fee configuration for a marketplace."""
    return FEES.get(source.lower(), MarketplaceFees(name=source, name_zh=source))


def calculate_steam_fee(price: float) -> float:
    """
    Calculate Steam transaction fee.
    Steam charges 5% game fee + 10% Steam fee = 15% total.
    However, the way it's calculated: buyer pays price, seller receives price * 0.85.
    Actually Steam's formula: if you want to receive X, you list at X / 0.85.
    If an item lists at P, Steam fee is P - (P * 0.85) = P * 0.15.
    """
    return price * 0.15


def net_revenue(source: str, price: float) -> float:
    """Calculate net revenue after seller fees."""
    fee = get_fee(source)
    if fee.steam_tiered:
        return price - calculate_steam_fee(price)
    return price * (1 - fee.seller_fee) - fee.fixed_fee


def net_cost(source: str, price: float) -> float:
    """Calculate net cost after buyer fees."""
    fee = get_fee(source)
    return price * (1 + fee.buyer_fee)


def calculate_spread(buy_source: str, buy_price: float,
                     sell_source: str, sell_price: float) -> Dict[str, float]:
    """
    Calculate true arbitrage spread after all fees.
    Returns dict with gross_spread, net_spread, net_spread_pct.
    """
    cost = net_cost(buy_source, buy_price)
    revenue = net_revenue(sell_source, sell_price)
    gross_spread = sell_price - buy_price
    net_spread = revenue - cost
    net_spread_pct = (net_spread / cost * 100) if cost > 0 else 0

    return {
        "gross_spread": round(gross_spread, 2),
        "net_spread": round(net_spread, 2),
        "net_spread_pct": round(net_spread_pct, 2),
        "buy_cost": round(cost, 2),
        "sell_revenue": round(revenue, 2),
    }


def calculate_steam_ratio(steam_price: float, third_party_price: float,
                          third_party_source: str) -> Dict[str, float]:
    """
    Calculate 挂刀 (Steam balance conversion) ratio.
    
    Ratio < 1.0 means you spend less than ¥1 on Steam to get ¥1 worth on the third-party site.
    Lower ratio = better deal for converting Steam balance.
    
    Returns:
        raw_ratio: third_party_price / steam_price (before fees)
        net_ratio: net revenue from selling on third_party / steam cost
        steam_net: what you actually get from Steam after 15% fee
        tp_net: what you actually get from third party after their fees
    """
    if steam_price <= 0 or third_party_price <= 0:
        return {"raw_ratio": 0.0, "net_ratio": 0.0, "steam_net": 0.0, "tp_net": 0.0}

    raw_ratio = third_party_price / steam_price

    steam_net = net_revenue("steam", steam_price)
    tp_net = net_revenue(third_party_source, third_party_price)

    # For 挂刀: you SELL on Steam (receive steam_net), BUY on third_party (pay third_party_price)
    # Ratio = what you get on third_party per ¥1 Steam spent
    # Actually the common definition: ratio = third_party_price / steam_price
    # With fees: effective_ratio = third_party_price / (steam_price / 0.85)
    effective_ratio = third_party_price / (steam_price / 0.85)

    # Net ratio considering you'd sell on third_party and buy on Steam
    # Or more commonly: buy on Steam, sell on third_party
    net_ratio = tp_net / (steam_price / 0.85) if steam_price > 0 else 0

    return {
        "raw_ratio": round(raw_ratio, 4),
        "net_ratio": round(net_ratio, 4),
        "effective_ratio": round(effective_ratio, 4),
        "steam_net": round(steam_net, 2),
        "tp_net": round(tp_net, 2),
    }


def ratio_grade(ratio: float) -> str:
    """Grade a 挂刀 ratio. Lower is better."""
    if ratio <= 0.65:
        return "excellent"  # Outstanding deal
    elif ratio <= 0.75:
        return "good"       # Very profitable
    elif ratio <= 0.85:
        return "fair"       # Worth considering
    elif ratio <= 0.95:
        return "poor"       # Marginal
    else:
        return "bad"        # Not worth it


def ratio_grade_zh(ratio: float) -> str:
    """Chinese grade labels."""
    grade = ratio_grade(ratio)
    grades = {
        "excellent": "极佳",
        "good": "优秀",
        "fair": "一般",
        "poor": "较差",
        "bad": "不值得",
    }
    return grades.get(grade, grade)
