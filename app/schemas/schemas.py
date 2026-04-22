from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ItemBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    price: Optional[float] = None
    image_url: Optional[str] = None
    exterior: Optional[str] = None
    rarity: Optional[str] = None
    weapon_name: Optional[str] = None

class ItemCreate(ItemBase):
    external_id: str
    source: str = "youpin"
    template_id: Optional[str] = None
    hash_name: Optional[str] = None
    original_price: Optional[float] = None
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    lease_unit_price: Optional[float] = None
    lease_deposit: Optional[float] = None
    long_lease_unit_price: Optional[float] = None
    item_type: Optional[str] = None
    quality: Optional[str] = None
    paint_seed: Optional[int] = None
    paint_index: Optional[int] = None
    abrade: Optional[float] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    name_tags: Optional[str] = None
    inspect_link: Optional[str] = None
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    commodity_type: Optional[str] = None
    on_lease: bool = False
    status: int = 10

class ItemResponse(ItemBase):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: Optional[int] = None
    external_id: str
    source: str
    template_id: Optional[str] = None
    hash_name: Optional[str] = None
    lowest_price: Optional[float] = None
    lease_unit_price: Optional[float] = None
    lease_deposit: Optional[float] = None
    seller_name: Optional[str] = None
    on_lease: bool = False
    created_at: Optional[datetime] = None

class PriceHistoryBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    price: float
    volume: Optional[int] = None
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None

class PriceHistoryCreate(PriceHistoryBase):
    item_id: int
    source: str = "youpin"

class PriceHistoryResponse(PriceHistoryBase):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: Optional[int] = None
    item_id: Optional[int] = None
    source: str = "youpin"
    recorded_at: Optional[datetime] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    source: Optional[str] = "all"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class SearchResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int

class ItemDetailResponse(BaseModel):
    item: ItemResponse
    price_history: List[PriceHistoryResponse]
    related_items: List[ItemResponse]

class HealthResponse(BaseModel):
    status: str
    version: str
    youpin_enabled: bool
    buff_enabled: bool
    skinport_enabled: bool

class YoupinDetailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    Code: int
    Msg: str
    Data: Optional[Dict[str, Any]] = None

class ScrapeStatus(BaseModel):
    last_scrape: Optional[datetime] = None
    items_scraped: int = 0
    status: str = "idle"

class PortfolioItemCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    item_name: str
    source: str = "buff"
    quantity: int = 1
    buy_price: float
    current_price: Optional[float] = None
    exterior: Optional[str] = None
    float_value: Optional[float] = None
    paint_seed: Optional[int] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None

class PortfolioItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: int
    item_name: str
    source: str
    quantity: int
    buy_price: float
    current_price: Optional[float] = None
    exterior: Optional[str] = None
    float_value: Optional[float] = None
    paint_seed: Optional[int] = None
    stickers: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PortfolioSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_invested: float
    total_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    item_count: int
    allocation_by_source: Dict[str, float]

class TransactionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: int
    portfolio_item_id: int
    transaction_type: str
    quantity: int
    price: float
    total: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    strategy: str = "buy_and_hold"
    item_name: str
    source: str = "steam"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 1000.0
    parameters: Optional[Dict[str, Any]] = None

class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    strategy: str
    item_name: str
    initial_capital: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    trades: int
    win_rate: float
    avg_trade_return: float
    sharpe_ratio: float
    equity_curve: List[Dict[str, Any]]
    trades_list: List[Dict[str, Any]]
