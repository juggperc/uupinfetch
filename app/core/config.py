from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "CS2 Price Scraper"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    DATABASE_URL: str = "sqlite:///./data/cs2_scraper.db"
    
    YOUPIN_BASE_URL: str = "https://api.youpin898.com"
    BUFF_BASE_URL: str = "https://buff.163.com"
    SKINPORT_BASE_URL: str = "https://api.skinport.com/v1"
    CSFLOAT_BASE_URL: str = "https://csfloat.com/api/v1"
    ECOSTEAM_BASE_URL: str = "https://openapi.ecosteam.cn"
    C5GAME_BASE_URL: str = "https://www.c5game.com"
    SCRAPE_INTERVAL_MINUTES: int = 30
    REQUEST_TIMEOUT: int = 15
    
    ENABLE_YOUPIN: bool = True
    ENABLE_BUFF: bool = True
    ENABLE_SKINPORT: bool = True
    ENABLE_CSFLOAT: bool = False
    ENABLE_ECOSTEAM: bool = False
    ENABLE_C5GAME: bool = False
    
    # Marketplace auth (optional — required for live Buff/Youpin search)
    BUFF_SESSION_COOKIE: str = ""
    YOUPIN_TOKEN: str = ""
    YOUPIN_DEVICE_ID: str = ""
    
    # Optional auth (for usage tracking if desired)
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 168
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
