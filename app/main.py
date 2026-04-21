from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import engine, Base
from app.api.v1.endpoints import router as api_router
from app.api.v1.auth import router as auth_router
from app.services.youpin import youpin_scraper
from app.services.buff import buff_scraper
from app.services.steam import steam_scraper
from app.services.scraper import background_scraper

settings = get_settings()

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("./data", exist_ok=True)
    setup_logging()
    background_scraper.start()
    yield
    background_scraper.stop()
    await youpin_scraper.close()
    await buff_scraper.close()
    await steam_scraper.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Open-source CS2 skin price scraper for traders and bot developers",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(api_router)
app.include_router(auth_router)

@app.get("/")
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
