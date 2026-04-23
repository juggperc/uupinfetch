"""
Portfolio API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.schemas import PortfolioItemCreate, PortfolioItemResponse
from app.services.portfolio_engine import PortfolioEngine

router = APIRouter()

@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    items = engine.get_all_items()
    return [PortfolioItemResponse.model_validate(item) for item in items]

@router.post("/portfolio")
async def add_portfolio_item(data: PortfolioItemCreate, db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    item = engine.add_item(data.model_dump())
    return PortfolioItemResponse.model_validate(item)

@router.put("/portfolio/{item_id}")
async def update_portfolio_item(item_id: int, data: PortfolioItemCreate, db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    item = engine.update_item(item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    return PortfolioItemResponse.model_validate(item)

@router.delete("/portfolio/{item_id}")
async def delete_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    if not engine.remove_item(item_id):
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    return {"status": "removed"}

@router.post("/portfolio/{item_id}/sell")
async def sell_portfolio_item(item_id: int, quantity: int, sell_price: float, db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    item = engine.sell_partial(item_id, quantity, sell_price)
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found or insufficient quantity")
    return PortfolioItemResponse.model_validate(item) if item else {"status": "sold_out"}

@router.get("/portfolio/summary")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    return engine.get_summary()

@router.post("/portfolio/refresh")
async def refresh_portfolio_prices(db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    updated = engine.refresh_prices()
    return {"updated": updated}

@router.get("/portfolio/transactions")
async def get_portfolio_transactions(item_id: Optional[int] = None, db: Session = Depends(get_db)):
    engine = PortfolioEngine(db)
    txns = engine.get_transactions(item_id)
    from app.schemas.schemas import TransactionResponse
    return [TransactionResponse.model_validate(t) for t in txns]
