from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Youpin CS2 Scraper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/cs2_scraper.db"
    
    # Scraper
    YOUPIN_BASE_URL: str = "https://api.youpin898.com"
    BUFF_BASE_URL: str = "https://buff.163.com"
    SCRAPE_INTERVAL_MINUTES: int = 30
    REQUEST_TIMEOUT: int = 15
    
    # Features
    ENABLE_YOUPIN: bool = True
    ENABLE_BUFF: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()
