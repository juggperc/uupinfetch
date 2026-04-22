from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, Index, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), index=True, default="youpin")
    external_id = Column(String(100), index=True)
    template_id = Column(String(100), index=True, nullable=True)
    name = Column(String(255), index=True)
    hash_name = Column(String(255), nullable=True)
    
    price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    lowest_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    
    lease_unit_price = Column(Float, nullable=True)
    lease_deposit = Column(Float, nullable=True)
    long_lease_unit_price = Column(Float, nullable=True)
    
    game_id = Column(Integer, default=730)
    item_type = Column(String(100), nullable=True)
    weapon_name = Column(String(100), nullable=True)
    exterior = Column(String(50), nullable=True)
    rarity = Column(String(50), nullable=True)
    quality = Column(String(50), nullable=True)
    
    paint_seed = Column(Integer, nullable=True)
    paint_index = Column(Integer, nullable=True)
    abrade = Column(Float, nullable=True)
    stickers = Column(JSON, nullable=True)
    name_tags = Column(Text, nullable=True)
    
    image_url = Column(Text, nullable=True)
    inspect_link = Column(Text, nullable=True)
    
    is_sold = Column(Boolean, default=False)
    on_lease = Column(Boolean, default=False)
    status = Column(Integer, default=10)
    
    seller_id = Column(String(100), nullable=True)
    seller_name = Column(String(255), nullable=True)
    commodity_type = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_item_source_external', 'source', 'external_id', unique=True),
        Index('idx_item_price', 'price'),
        Index('idx_item_name_source', 'name', 'source'),
    )

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, index=True)
    source = Column(String(50), index=True)
    
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    lowest_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_price_history_item_date', 'item_id', 'recorded_at'),
    )

class SearchQuery(Base):
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), index=True)
    source = Column(String(50), default="youpin")
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    
    api_key = Column(String(255), unique=True, index=True, nullable=True)
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RatioHistory(Base):
    __tablename__ = "ratio_history"
    
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(255), index=True, nullable=False)
    steam_price = Column(Float, nullable=True)
    steam_volume = Column(Integer, nullable=True)
    
    buff_price = Column(Float, nullable=True)
    buff_ratio = Column(Float, nullable=True)
    
    youpin_price = Column(Float, nullable=True)
    youpin_ratio = Column(Float, nullable=True)
    
    skinport_price = Column(Float, nullable=True)
    skinport_ratio = Column(Float, nullable=True)
    
    csfloat_price = Column(Float, nullable=True)
    csfloat_ratio = Column(Float, nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_ratio_history_item_date', 'item_name', 'recorded_at'),
    )

class FloatSnapshot(Base):
    __tablename__ = "float_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(255), index=True, nullable=False)
    source = Column(String(50), index=True, nullable=False)
    external_id = Column(String(100), nullable=True)
    
    float_value = Column(Float, nullable=True)
    paint_seed = Column(Integer, nullable=True)
    paint_index = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    
    stickers = Column(JSON, nullable=True)
    inspect_link = Column(Text, nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_float_item_source', 'item_name', 'source'),
    )

class PortfolioItem(Base):
    __tablename__ = "portfolio_items"
    
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(255), index=True, nullable=False)
    source = Column(String(50), default="buff")
    
    quantity = Column(Integer, default=1)
    buy_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    
    exterior = Column(String(50), nullable=True)
    float_value = Column(Float, nullable=True)
    paint_seed = Column(Integer, nullable=True)
    stickers = Column(JSON, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_portfolio_name', 'item_name'),
    )

class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_item_id = Column(Integer, ForeignKey("portfolio_items.id"), index=True)
    
    transaction_type = Column(String(20), nullable=False)  # buy, sell, update
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
