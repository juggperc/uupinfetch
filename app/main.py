"""
FastAPI entry point with APScheduler bot (no threading),
rate limiting middleware, job queue, and graceful shutdown.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys
import asyncio
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware.rate_limit import RateLimitMiddleware
from app.db.database import engine, Base
from app.api.v1.endpoints import router as api_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bot import router as bot_router
from app.services.youpin import youpin_scraper
from app.services.buff import buff_scraper
from app.services.steam import steam_scraper
from app.services.skinport import skinport_scraper
from app.services.csfloat import csfloat_scraper
from app.services.scraper import background_scraper
from app.services.job_queue import job_queue
from app.services.bot_engine import get_bot_sync

settings = get_settings()

Base.metadata.create_all(bind=engine)

# Resolve project root so static/templates work whether run from source or frozen EXE
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Global bot instance
_trading_bot = None

async def _bot_job():
    """APScheduler job that runs the bot scan."""
    global _trading_bot
    if _trading_bot and _trading_bot.running:
        try:
            await _trading_bot.run_scan()
        except Exception as e:
            logging.getLogger("cs2_bot").error(f"Scheduled bot scan error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("./data", exist_ok=True)
    setup_logging()
    background_scraper.start()
    job_queue.start()
    
    # Start trading bot via APScheduler (same event loop — no threading)
    global _trading_bot
    api_host = "127.0.0.1" if settings.HOST in ("0.0.0.0", "::") else settings.HOST
    _trading_bot = get_bot_sync(api_base=f"http://{api_host}:{settings.PORT}")
    _trading_bot.running = True
    
    # Schedule bot scans every 60 seconds
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    
    bot_scheduler = AsyncIOScheduler()
    bot_scheduler.add_job(
        _bot_job,
        IntervalTrigger(seconds=_trading_bot.scan_interval),
        id="bot_scan",
        replace_existing=True,
    )
    bot_scheduler.start()
    
    # Run initial scan
    asyncio.create_task(_bot_job())
    
    yield
    
    _trading_bot.stop()
    bot_scheduler.shutdown()
    background_scraper.stop()
    job_queue.stop()
    await youpin_scraper.close()
    await buff_scraper.close()
    await steam_scraper.close()
    await skinport_scraper.close()
    await csfloat_scraper.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source CS2 skin price scraper with built-in trading bot for traders and bot developers",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate limiting middleware (before CORS so it blocks early)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(bot_router)

@app.get("/")
async def landing_page(request: Request):
    return templates.TemplateResponse("bot.html", {"request": request})

@app.get("/search")
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/item/{item_id}")
async def item_page(request: Request, item_id: str):
    return templates.TemplateResponse("item.html", {"request": request, "item_id": item_id})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/bot")
async def bot_page(request: Request):
    return templates.TemplateResponse("bot.html", {"request": request})

@app.get("/ratios")
async def ratios_page(request: Request):
    return templates.TemplateResponse("ratios.html", {"request": request})

@app.get("/tradeup")
async def tradeup_page(request: Request):
    return templates.TemplateResponse("tradeup.html", {"request": request})

@app.get("/portfolio")
async def portfolio_page(request: Request):
    return templates.TemplateResponse("portfolio.html", {"request": request})

@app.get("/backtest")
async def backtest_page(request: Request):
    return templates.TemplateResponse("backtest.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
