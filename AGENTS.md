# Youpin CS2 Scraper - Agent Guide

## Project Overview

FastAPI-based CS2 skin price scraper and API serving data from Youpin (悠悠有品), Buff163, and Steam Community Market. Features a stunning liquid glass design landing page with CN/EN i18n support.

## Tech Stack

- **Backend**: FastAPI 0.111, SQLAlchemy 2.0, Pydantic 2.7, APScheduler
- **Frontend**: Vanilla JS, Chart.js, Jinja2 Templates
- **Design**: Liquid Glass CSS (backdrop-filter, CSS animations, aurora backgrounds)
- **Scraping**: httpx (async HTTP client)
- **Deployment**: Docker, Docker Compose
- **Database**: SQLite (configurable to PostgreSQL)

## Directory Structure

```
app/
  api/v1/endpoints.py    # REST API routes
  core/config.py         # Pydantic settings
  db/database.py         # SQLAlchemy engine & session
  models/models.py       # DB models (Item, PriceHistory, SearchQuery)
  schemas/schemas.py     # Pydantic request/response models
  services/
    youpin.py            # Youpin API scraper
    buff.py              # Buff163 scraper
    steam.py             # Steam Community Market scraper
    scraper.py           # Background scraper service
  main.py                # FastAPI entry point
static/
  js/i18n.js             # CN/EN translations
  images/placeholder.png # Item placeholder image
templates/
  base.html              # Liquid glass base template
  index.html             # Landing page
  search.html            # Search results page
  item.html              # Item detail with price chart
data/                    # SQLite database (created at runtime)
```

## Build & Run

### Docker (Production)
```bash
docker compose up -d
```

### Local Development
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# or
./start.bat  # Windows
./start.sh   # Linux/Mac
```

## Key API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/items/search?q=AK-47&source=steam` | Search items |
| `GET /api/v1/items/{id}?source=steam` | Item detail |
| `GET /api/v1/items/popular?limit=8` | Trending items from DB |
| `GET /api/v1/categories` | Item categories |
| `GET /api/v1/market/summary` | Market stats |
| `GET /api/docs` | Swagger UI |

## Reverse Engineered Endpoints

### Youpin (Working Public Endpoints)
- `GET /api/commodity/Commodity/Detail?id={id}` - Item details
- `GET /api/youpin/pc/query/filter/getSearchTags` - Categories
- `GET /api/trade/Order/OrderDeliverStatistics` - Delivery stats

### Buff163 (Requires Auth)
- `GET /api/market/goods` - Search
- `GET /api/market/goods/sell_order` - Sell orders
- `GET /api/market/goods/price_history` - Price history

### Steam (Fully Public)
- `GET /market/search/render` - Search
- `GET /market/priceoverview` - Price overview

## Auth Configuration

Youpin and Buff163 require authentication for search/listings. To enable:
1. Log in via browser
2. Extract cookies/session tokens
3. Configure in scraper services or env vars

Steam Community Market works without auth.

## Design System

- **Liquid Glass**: `backdrop-filter: blur(20px) saturate(180%)`
- **Colors**: Dark background (#0a0a0f), accent cyan (#00d4ff), purple (#a855f7)
- **Animations**: fadeInUp, float, pulse-glow, aurora background
- **i18n**: Toggle between EN/CN via `data-i18n` attributes

## Environment Variables

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db
ENABLE_YOUPIN=true
ENABLE_BUFF=true
SCRAPE_INTERVAL_MINUTES=30
```

## Notes for Agents

- **Routing Order**: Specific routes must come before parameterized routes in FastAPI
- **DB Path**: SQLite uses relative path `./data/cs2_scraper.db` - ensure working directory is correct
- **Background Scraper**: Runs via APScheduler, scrapes popular items every 30 min
- **Unicode**: Windows console may have encoding issues with Chinese characters; write to files instead
- **Rate Limiting**: Youpin's ALB blocks aggressive requests; add delays if extending scrapers
