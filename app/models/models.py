from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.sql import func
from app.db.database import Base

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), index=True, default="youpin")  # youpin, buff
    external_id = Column(String(100), index=True)
    template_id = Column(String(100), index=True, nullable=True)
    name = Column(String(255), index=True)
    hash_name = Column(String(255), nullable=True)
    
    # Pricing
    price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    lowest_price = Column(Float, nullable=True)
    highest_price = Column(Float, nullable=True)
    
    # Lease pricing
    lease_unit_price = Column(Float, nullable=True)
    lease_deposit = Column(Float, nullable=True)
    long_lease_unit_price = Column(Float, nullable=True)
    
    # Item properties
    game_id = Column(Integer, default=730)
    item_type = Column(String(100), nullable=True)
    weapon_name = Column(String(100), nullable=True)
    exterior = Column(String(50), nullable=True)
    rarity = Column(String(50), nullable=True)
    quality = Column(String(50), nullable=True)
    
    # Wear & stickers
    paint_seed = Column(Integer, nullable=True)
    paint_index = Column(Integer, nullable=True)
    abrade = Column(Float, nullable=True)
    stickers = Column(JSON, nullable=True)
    name_tags = Column(Text, nullable=True)
    
    # Media
    image_url = Column(Text, nullable=True)
    inspect_link = Column(Text, nullable=True)
    
    # Status
    is_sold = Column(Boolean, default=False)
    on_lease = Column(Boolean, default=False)
    status = Column(Integer, default=10)
    
    # Metadata
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
