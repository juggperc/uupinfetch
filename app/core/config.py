from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Youpin CS2 Scraper"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = False
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    DATABASE_URL: str = "sqlite:///./data/cs2_scraper.db"
    
    YOUPIN_BASE_URL: str = "https://api.youpin898.com"
    BUFF_BASE_URL: str = "https://buff.163.com"
    SCRAPE_INTERVAL_MINUTES: int = 30
    REQUEST_TIMEOUT: int = 15
    
    ENABLE_YOUPIN: bool = True
    ENABLE_BUFF: bool = True
    
    # Auth
    SECRET_KEY: str = "your-secret-key-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 168  # 7 days
    
    # Polar.sh
    POLAR_ACCESS_TOKEN: str = ""
    POLAR_SERVER: str = "sandbox"  # sandbox or production
    POLAR_WEBHOOK_SECRET: str = ""
    POLAR_PRO_PRODUCT_ID: str = ""
    POLAR_ENTERPRISE_PRODUCT_ID: str = ""
    POLAR_SUCCESS_URL: str = "http://localhost:8000/dashboard/billing"
    
    # Rate limiting
    FREE_TIER_DAILY_LIMIT: int = 100
    PRO_TIER_DAILY_LIMIT: int = 5000
    ENTERPRISE_TIER_DAILY_LIMIT: int = 50000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
