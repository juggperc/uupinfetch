# CS2 Price Scraper - Agent Guide

## Project Overview

Open-source CS2 skin price scraper and trading intelligence platform built for trading bot developers. Fetches real-time prices from Steam Community Market, Youpin (悠悠有品), Buff163, and Skinport. Features a built-in trading bot, portfolio tracker, backtesting engine, trade-up calculator, pattern detection, and 挂刀 (Steam balance conversion) ratio engine. Run it locally on your machine or deploy to a VPS.

## Tech Stack

- **Backend**: FastAPI 0.111, SQLAlchemy 2.0, Pydantic 2.7, APScheduler
- **Frontend**: Vanilla JS, Chart.js, Jinja2 Templates
- **Design**: Solid dark theme (#0b0b0f), single blue accent (#3b82f6), no gradients, no animations
- **Scraping**: httpx (async HTTP client)
- **Deployment**: Docker, Docker Compose
- **Database**: SQLite (configurable to PostgreSQL)

## Directory Structure

```
app/
  api/v1/endpoints.py     # REST API routes (open, no auth required)
  api/v1/auth.py          # Optional user auth
  api/v1/bot.py           # Trading bot API endpoints
  core/config.py          # Pydantic settings
  core/auth.py            # JWT auth utilities
  core/logging.py         # Logging configuration
  db/database.py          # SQLAlchemy engine & session
  models/models.py        # DB models (Item, PriceHistory, SearchQuery, User, PortfolioItem, PortfolioTransaction, RatioHistory, FloatSnapshot)
  schemas/schemas.py      # Pydantic request/response models
  services/
    bot_engine.py         # CS2 trading bot engine
    portfolio_engine.py   # Portfolio holdings & P&L tracker
    backtest_engine.py    # Strategy backtesting on historical data
    ratio_engine.py       # 挂刀 (Steam balance conversion) ratio engine
    tradeup_engine.py     # Trade-up contract calculator + EV engine
    pattern_engine.py     # Pattern detection (blue gems, doppler phases, fade)
    market_fees.py        # Fee tables + fee-aware spread calculation
    steam.py              # Steam Community Market scraper (fully public)
    youpin.py             # Youpin API scraper (public endpoints)
    buff.py               # Buff163 scraper (needs auth)
    skinport.py           # Skinport API scraper (public, Brotli required)
    csfloat.py            # CSFloat scraper (float data, stickers)
    scraper.py            # Background scraper service
  main.py                 # FastAPI entry point
launcher.py               # System tray launcher (auto-browser, server mgmt)
build.py                  # PyInstaller build script for standalone EXE
examples/
  basic_bot.py            # Simple trading bot example
  advanced_bot.py         # SQLite-backed trend analysis bot
static/
  js/i18n.js              # CN/EN translations
  images/placeholder.png  # Item placeholder image
templates/
  base.html               # Base template (solid dark, mobile nav, toasts)
  bot.html                # Trading bot UI with SSE alerts
  portfolio.html          # Portfolio tracker with P&L & allocation chart
  ratios.html             # 挂刀 ratio ranking table
  tradeup.html            # Trade-up contract scanner
  backtest.html           # Strategy backtest simulator
  search.html             # Search results
  item.html               # Item detail with price chart
  dashboard.html          # Dashboard with API tester
  login.html              # Login page
  register.html           # Register page
data/                     # SQLite database (created at runtime)
```

## Build & Run

### Standalone EXE (Easiest — No Python Required)
```bash
python build.py
```
Output: `dist/CS2PriceScraper/CS2PriceScraper.exe` (≈110 MB folder). Double-click to run.
- Runs in system tray with auto-browser open
- Right-click tray icon for Dashboard, Bot UI, Scan, Logs, Quit

### Easy Launch (Auto-Installs Deps)

**Windows:**
```powershell
start-easy.bat   # Creates venv, installs deps, starts server, opens browser
```

**Linux/Mac:**
```bash
./start-easy.sh   # Creates venv, installs deps, starts server, opens browser
```

### Legacy Setup Scripts

**Windows:**
```powershell
setup.bat      # One-time setup
start.bat      # Start server
```

**Linux/Mac:**
```bash
./setup.sh     # One-time setup
./start.sh     # Start server
```

### Docker
```bash
docker compose up -d
```

### Manual
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Key API Endpoints

All endpoints are **open by default** - no auth required.

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/items/search?q=AK-47&source=steam` | Search items (all, steam, buff, youpin, skinport) |
| `GET /api/v1/items/{id}?source=steam` | Item detail |
| `GET /api/v1/items/popular?limit=8` | Trending items from DB |
| `GET /api/v1/categories` | Item categories |
| `GET /api/v1/market/summary` | Market stats |
| `GET /api/v1/ratios` | 挂刀 ratios (best Steam balance conversion items) |
| `GET /api/v1/ratios/summary` | Ratio scan summary stats |
| `POST /api/v1/ratios/scan` | Trigger ratio scan |
| `GET /api/v1/tradeup/collections` | Trade-up collections |
| `GET /api/v1/tradeup/scan` | Scan profitable trade-ups |
| `POST /api/v1/tradeup/calculate` | Calculate trade-up EV |
| `GET /api/v1/patterns/analyze` | Analyze skin pattern value |
| `GET /api/v1/patterns/scan` | Scan for pattern deals |
| `GET /api/v1/float/{item_name}` | CSFloat listings with float values |
| `GET /api/v1/portfolio` | Portfolio holdings |
| `POST /api/v1/portfolio` | Add portfolio item |
| `PUT /api/v1/portfolio/{id}` | Update portfolio item |
| `DELETE /api/v1/portfolio/{id}` | Remove portfolio item |
| `POST /api/v1/portfolio/{id}/sell` | Sell partial holding |
| `GET /api/v1/portfolio/summary` | Portfolio summary (P&L, allocation) |
| `POST /api/v1/portfolio/refresh` | Refresh prices from DB |
| `GET /api/v1/portfolio/transactions` | Transaction history |
| `GET /api/v1/backtest/strategies` | Available backtest strategies |
| `POST /api/v1/backtest/run` | Run strategy backtest |
| `GET /api/v1/alerts/stream` | SSE real-time alerts stream |
| `GET /api/v1/bot/status` | Bot running status |
| `GET /api/v1/bot/arbitrage` | Arbitrage opportunities |
| `GET /api/v1/bot/recommendations` | Investment signals |
| `GET /api/v1/bot/insights` | Market insights |
| `POST /api/v1/bot/trigger-scan` | Manual bot scan |
| `GET /api/v1/bot/watchlist` | Price alert watchlist |
| `POST /api/v1/bot/watchlist` | Add watchlist item |
| `DELETE /api/v1/bot/watchlist/{id}` | Remove watchlist item |
| `GET /api/v1/bot/history` | Opportunity history |
| `GET /api/v1/bot/export/arbitrage` | CSV export |
| `GET /api/v1/bot/export/recommendations` | CSV export |
| `GET /api/docs` | Swagger UI |

## Reverse Engineered Endpoints

### Youpin (api.youpin898.com) - Public
- `GET /api/commodity/Commodity/Detail?id={id}` - Item details
- `GET /api/youpin/pc/query/filter/getSearchTags` - Categories
- `GET /api/trade/Order/OrderDeliverStatistics` - Delivery stats

### Buff163 (buff.163.com) - Requires Auth
- `GET /api/market/goods` - Search
- `GET /api/market/goods/sell_order` - Sell orders
- `GET /api/market/goods/price_history` - Price history

### Skinport (api.skinport.com/v1) - Public, Brotli Required
- `GET /v1/items?app_id=730&currency=CNY&tradable=0` - Full item catalog (20k+ items, cached 5 min)
- `Accept-Encoding: br` header is **required**
- Rate limit: 8 requests per 5 minutes
- Returns: `market_hash_name`, `min_price`, `suggested_price`, `quantity`

### Steam (Fully Public)
- `GET /market/search/render` - Search
- `GET /market/priceoverview` - Price overview

### CSFloat (csfloat.com) - Cloudflare Protected
- `GET /api/v1/listings` - Float listings with stickers
- Public API is behind Cloudflare; scraper disabled by default (`ENABLE_CSFLOAT=false`)

## Auth Configuration (Optional)

The API is open by default. Skinport works without auth. To enable Buff/Youpin search:
1. Log in via browser
2. Extract cookies/session tokens
3. Configure in scraper services or env vars

## Design System

- **Solid Dark**: Background `#0b0b0f`, elevated `#151519`, hover `#1e1e24`
- **Single Accent**: Blue `#3b82f6` only — no gradients, no glass, no animations
- **Spacing System**: xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48)
- **i18n**: Toggle between EN/CN via `data-i18n` attributes
- **Toast Notifications**: Top-right, success/error/warning/info
- **Skeleton Loaders**: Shimmer on async data
- **Mobile Nav**: Hamburger menu with overlay

## Environment Variables

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db
ENABLE_YOUPIN=true
ENABLE_BUFF=true
ENABLE_SKINPORT=true
ENABLE_CSFLOAT=false
SCRAPE_INTERVAL_MINUTES=30
```

## Notes for Agents

- **Routing Order**: Specific routes must come before parameterized routes in FastAPI
- **DB Path**: SQLite uses relative path `./data/cs2_scraper.db` - ensure working directory is correct
- **Background Scraper**: Runs via APScheduler, scrapes popular items every 30 min, ratios every 60 min
- **Unicode**: Windows console may have encoding issues with Chinese characters; write to files instead
- **Rate Limiting**: Youpin's ALB blocks aggressive requests; add delays if extending scrapers
- **Open API**: All endpoints are public by design - no auth required for bot integration
- **PyInstaller Paths**: In launcher.py, `sys._MEIPASS` points to `_internal/` (bundled code+assets). Data/logs live next to the EXE.
- **Skinport Caching**: The `/v1/items` endpoint returns 20k+ items. The scraper caches them in-memory for 5 minutes and filters client-side. This is efficient and respects the API rate limit.
- **Launcher Behavior**: Starts uvicorn as subprocess (dev) or background thread (frozen EXE), polls `/api/v1/health` for readiness, then auto-opens browser to `/bot`
- **SSE Alerts**: `/api/v1/alerts/stream` pushes watchlist alerts via Server-Sent Events. Bot UI auto-connects on load.
- **Portfolio Prices**: Call `POST /api/v1/portfolio/refresh` to update current prices from the latest price history entries.
- **Backtest Fallback**: If no price history exists in DB, synthetic deterministic data is generated for demo purposes.
