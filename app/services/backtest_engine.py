import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import PriceHistory, Item
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

STRATEGIES = {
    "buy_and_hold": "Buy at start, sell at end",
    "mean_reversion": "Buy when price drops N% from recent high, sell on recovery",
    "momentum": "Buy when price rises N% from recent low, sell on pullback",
    "dca": "Dollar-cost average: buy fixed amount at each data point",
}

class BacktestEngine:
    """Backtesting engine for trading strategies on historical price data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def get_strategies() -> Dict[str, str]:
        return STRATEGIES
    
    def _get_price_history(self, item_name: str, source: str = "steam", 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch price history from DB for an item."""
        # Find item ID by name
        item = self.db.query(Item).filter(
            Item.name.ilike(f"%{item_name}%"),
            Item.source == source
        ).first()
        
        if not item:
            # Fallback: try to find by hash_name or any source
            item = self.db.query(Item).filter(
                Item.name.ilike(f"%{item_name}%")
            ).first()
        
        query = self.db.query(PriceHistory)
        if item:
            query = query.filter(PriceHistory.item_id == item.id)
        
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(PriceHistory.recorded_at >= dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                dt = datetime.strptime(end_date, "%Y-%m-%d")
                query = query.filter(PriceHistory.recorded_at <= dt)
            except ValueError:
                pass
        
        history = query.order_by(PriceHistory.recorded_at.asc()).all()
        
        # If no history, generate synthetic data for demo
        if not history:
            return self._generate_synthetic_data(item_name, start_date, end_date)
        
        return [
            {
                "date": h.recorded_at.strftime("%Y-%m-%d") if h.recorded_at else "",
                "price": float(h.price) if h.price else 0,
                "volume": h.volume or 0,
            }
            for h in history
        ]
    
    def _generate_synthetic_data(self, item_name: str, start_date: Optional[str], 
                                  end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Generate synthetic price data for backtesting when no DB history exists."""
        import random
        
        # Deterministic pseudo-random based on item name
        seed = sum(ord(c) for c in item_name)
        rng = random.Random(seed)
        
        base_price = 50 + (seed % 500)
        days = 90
        if start_date and end_date:
            try:
                s = datetime.strptime(start_date, "%Y-%m-%d")
                e = datetime.strptime(end_date, "%Y-%m-%d")
                days = (e - s).days
            except ValueError:
                pass
        
        data = []
        price = base_price
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now() - timedelta(days=days)
        
        for i in range(max(days, 30)):
            change = rng.uniform(-0.03, 0.035)
            price = max(1, price * (1 + change))
            data.append({
                "date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                "price": round(price, 2),
                "volume": rng.randint(10, 500),
            })
        
        return data
    
    def run_backtest(self, strategy: str, item_name: str, source: str = "steam",
                     start_date: Optional[str] = None, end_date: Optional[str] = None,
                     initial_capital: float = 1000.0, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a backtest and return performance metrics."""
        prices = self._get_price_history(item_name, source, start_date, end_date)
        
        if len(prices) < 5:
            return {
                "strategy": strategy,
                "item_name": item_name,
                "error": "Insufficient price data (minimum 5 data points required)",
            }
        
        params = parameters or {}
        
        if strategy == "buy_and_hold":
            return self._backtest_buy_and_hold(prices, initial_capital)
        elif strategy == "mean_reversion":
            drop_pct = params.get("drop_pct", 5.0)
            return self._backtest_mean_reversion(prices, initial_capital, drop_pct)
        elif strategy == "momentum":
            rise_pct = params.get("rise_pct", 5.0)
            return self._backtest_momentum(prices, initial_capital, rise_pct)
        elif strategy == "dca":
            return self._backtest_dca(prices, initial_capital)
        else:
            return self._backtest_buy_and_hold(prices, initial_capital)
    
    def _backtest_buy_and_hold(self, prices: List[Dict[str, Any]], capital: float) -> Dict[str, Any]:
        entry_price = prices[0]["price"]
        exit_price = prices[-1]["price"]
        shares = capital / entry_price if entry_price > 0 else 0
        final_equity = shares * exit_price
        
        equity_curve = []
        for p in prices:
            equity_curve.append({
                "date": p["date"],
                "equity": round(shares * p["price"], 2),
            })
        
        total_return = ((final_equity - capital) / capital * 100) if capital > 0 else 0
        
        return {
            "strategy": "buy_and_hold",
            "item_name": prices[0].get("item_name", ""),
            "initial_capital": round(capital, 2),
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": self._calc_max_drawdown(equity_curve),
            "trades": 2,
            "win_rate": 100.0 if total_return > 0 else 0.0,
            "avg_trade_return": round(total_return, 2),
            "sharpe_ratio": self._calc_sharpe(equity_curve),
            "equity_curve": equity_curve,
            "trades_list": [
                {"date": prices[0]["date"], "action": "BUY", "price": entry_price, "shares": round(shares, 4)},
                {"date": prices[-1]["date"], "action": "SELL", "price": exit_price, "shares": round(shares, 4)},
            ],
        }
    
    def _backtest_mean_reversion(self, prices: List[Dict[str, Any]], capital: float, drop_pct: float = 5.0) -> Dict[str, Any]:
        equity = capital
        position = 0.0
        trades = []
        equity_curve = []
        recent_high = prices[0]["price"]
        
        for i, p in enumerate(prices):
            price = p["price"]
            
            if price > recent_high:
                recent_high = price
            
            drop_from_high = ((recent_high - price) / recent_high * 100) if recent_high > 0 else 0
            
            if position == 0 and drop_from_high >= drop_pct:
                # Buy signal
                shares = (equity * 0.95) / price  # Keep 5% cash
                position = shares
                equity = equity - (shares * price)
                trades.append({"date": p["date"], "action": "BUY", "price": price, "shares": round(shares, 4)})
            elif position > 0 and price >= recent_high * 0.98:
                # Sell signal (recovered to near high)
                equity += position * price
                trades.append({"date": p["date"], "action": "SELL", "price": price, "shares": round(position, 4)})
                position = 0
                recent_high = price
            
            current_equity = equity + (position * price)
            equity_curve.append({"date": p["date"], "equity": round(current_equity, 2)})
        
        # Close position at end
        if position > 0:
            equity += position * prices[-1]["price"]
            trades.append({"date": prices[-1]["date"], "action": "SELL", "price": prices[-1]["price"], "shares": round(position, 4)})
            position = 0
        
        final_equity = equity
        total_return = ((final_equity - capital) / capital * 100) if capital > 0 else 0
        
        win_trades = sum(1 for i in range(0, len(trades)-1, 2) if trades[i+1]["price"] > trades[i]["price"]) if len(trades) >= 2 else 0
        trade_pairs = len(trades) // 2
        
        return {
            "strategy": "mean_reversion",
            "item_name": prices[0].get("item_name", ""),
            "initial_capital": round(capital, 2),
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": self._calc_max_drawdown(equity_curve),
            "trades": len(trades),
            "win_rate": round(win_trades / trade_pairs * 100, 1) if trade_pairs > 0 else 0,
            "avg_trade_return": round(total_return / max(trade_pairs, 1), 2),
            "sharpe_ratio": self._calc_sharpe(equity_curve),
            "equity_curve": equity_curve,
            "trades_list": trades,
        }
    
    def _backtest_momentum(self, prices: List[Dict[str, Any]], capital: float, rise_pct: float = 5.0) -> Dict[str, Any]:
        equity = capital
        position = 0.0
        trades = []
        equity_curve = []
        recent_low = prices[0]["price"]
        
        for i, p in enumerate(prices):
            price = p["price"]
            
            if price < recent_low:
                recent_low = price
            
            rise_from_low = ((price - recent_low) / recent_low * 100) if recent_low > 0 else 0
            
            if position == 0 and rise_from_low >= rise_pct:
                shares = (equity * 0.95) / price
                position = shares
                equity = equity - (shares * price)
                trades.append({"date": p["date"], "action": "BUY", "price": price, "shares": round(shares, 4)})
            elif position > 0 and price <= recent_low * 1.02:
                equity += position * price
                trades.append({"date": p["date"], "action": "SELL", "price": price, "shares": round(position, 4)})
                position = 0
                recent_low = price
            
            current_equity = equity + (position * price)
            equity_curve.append({"date": p["date"], "equity": round(current_equity, 2)})
        
        if position > 0:
            equity += position * prices[-1]["price"]
            trades.append({"date": prices[-1]["date"], "action": "SELL", "price": prices[-1]["price"], "shares": round(position, 4)})
            position = 0
        
        final_equity = equity
        total_return = ((final_equity - capital) / capital * 100) if capital > 0 else 0
        
        win_trades = sum(1 for i in range(0, len(trades)-1, 2) if trades[i+1]["price"] > trades[i]["price"]) if len(trades) >= 2 else 0
        trade_pairs = len(trades) // 2
        
        return {
            "strategy": "momentum",
            "item_name": prices[0].get("item_name", ""),
            "initial_capital": round(capital, 2),
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": self._calc_max_drawdown(equity_curve),
            "trades": len(trades),
            "win_rate": round(win_trades / trade_pairs * 100, 1) if trade_pairs > 0 else 0,
            "avg_trade_return": round(total_return / max(trade_pairs, 1), 2),
            "sharpe_ratio": self._calc_sharpe(equity_curve),
            "equity_curve": equity_curve,
            "trades_list": trades,
        }
    
    def _backtest_dca(self, prices: List[Dict[str, Any]], capital: float) -> Dict[str, Any]:
        invest_per_period = capital / len(prices) if prices else 0
        total_shares = 0
        total_invested = 0
        trades = []
        equity_curve = []
        
        for p in prices:
            price = p["price"]
            if price > 0 and invest_per_period > 0:
                shares = invest_per_period / price
                total_shares += shares
                total_invested += invest_per_period
                trades.append({"date": p["date"], "action": "BUY", "price": price, "shares": round(shares, 4)})
            
            current_equity = total_shares * price
            equity_curve.append({"date": p["date"], "equity": round(current_equity, 2)})
        
        final_equity = total_shares * prices[-1]["price"] if prices else 0
        total_return = ((final_equity - capital) / capital * 100) if capital > 0 else 0
        
        return {
            "strategy": "dca",
            "item_name": prices[0].get("item_name", ""),
            "initial_capital": round(capital, 2),
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": self._calc_max_drawdown(equity_curve),
            "trades": len(trades),
            "win_rate": 100.0 if total_return > 0 else 0.0,
            "avg_trade_return": round(total_return / max(len(trades), 1), 2),
            "sharpe_ratio": self._calc_sharpe(equity_curve),
            "equity_curve": equity_curve,
            "trades_list": trades,
        }
    
    @staticmethod
    def _calc_max_drawdown(equity_curve: List[Dict[str, Any]]) -> float:
        peak = 0
        max_dd = 0
        for point in equity_curve:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)
    
    @staticmethod
    def _calc_sharpe(equity_curve: List[Dict[str, Any]], risk_free_rate: float = 0.0) -> float:
        if len(equity_curve) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i-1]["equity"]
            curr = equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)
        
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        if std_dev == 0:
            return 0.0
        
        sharpe = (avg_return - risk_free_rate / 252) / std_dev * math.sqrt(252)
        return round(sharpe, 2)
