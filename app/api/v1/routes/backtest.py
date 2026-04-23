"""
Backtest API routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.database import get_db
from app.services.backtest_engine import BacktestEngine

router = APIRouter()

@router.get("/backtest/strategies")
async def get_backtest_strategies():
    return {"strategies": BacktestEngine.get_strategies()}

@router.post("/backtest/run")
async def run_backtest(data: Dict[str, Any], db: Session = Depends(get_db)):
    engine = BacktestEngine(db)
    result = engine.run_backtest(
        strategy=data.get("strategy", "buy_and_hold"),
        item_name=data.get("item_name", ""),
        source=data.get("source", "steam"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        initial_capital=data.get("initial_capital", 1000.0),
        parameters=data.get("parameters"),
    )
    return result
