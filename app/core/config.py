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
    SCRAPE_INTERVAL_MINUTES: int = 30
    REQUEST_TIMEOUT: int = 15
    
    ENABLE_YOUPIN: bool = True
    ENABLE_BUFF: bool = True
    
    # Optional auth (for usage tracking if desired)
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 168
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
