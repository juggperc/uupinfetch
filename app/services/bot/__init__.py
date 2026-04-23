"""
Bot sub-package initialization.
"""

from .arbitrage_scanner import ArbitrageScanner, ArbitrageOpportunity
from .case_analyzer import CaseAnalyzer, InvestmentRecommendation
from .sticker_analyzer import StickerAnalyzer
from .watchlist_manager import WatchlistManager
from .webhook_notifier import WebhookNotifier

__all__ = [
    "ArbitrageScanner",
    "ArbitrageOpportunity",
    "CaseAnalyzer",
    "InvestmentRecommendation",
    "StickerAnalyzer",
    "WatchlistManager",
    "WebhookNotifier",
]
