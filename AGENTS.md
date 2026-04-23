# CS2 Price Scraper - Agent Guide

## Project Overview

Open-source CS2 skin price scraper and trading intelligence platform built for trading bot developers. Fetches real-time prices from Steam Community Market, Youpin (悠悠有品), Buff163, and Skinport. Features a built-in trading bot, portfolio tracker, backtesting engine, trade-up calculator, pattern detection, and 挂刀 (Steam balance conversion) ratio engine. Run it locally on your machine or deploy to a VPS.

## Tech Stack

- **Backend**: FastAPI 0.111, SQLAlchemy 2.0, Pydantic 2.7, APScheduler
- **Frontend**: Vanilla JS, Chart.js, Jinja2 Templates
- **Design**: Solid dark theme (#0b0b0f), single blue accent (#3b82f6), no gradients, no animations
- **Scraping**: httpx (async HTTP client)
- **Deployment**: Docker, Docker Compose
- **Database**: SQLite (dev) / PostgreSQL (production Docker)

## Directory Structure

```
app/
  main.py                 # FastAPI entry + APScheduler bot launcher (no threads)
  api/v1/
    endpoints.py          # Thin aggregator: health, SSE, admin, imports domain routers
    bot.py                # Bot intelligence + webhook APIs (SQLAlchemy, no raw SQL)
    auth.py               # Optional user auth
    routes/               # Domain-specific routers (split from god file)
      search.py           # Item search, compare, detail, categories
      ratios.py           # 挂刀 ratio engine endpoints
      tradeup.py          # Trade-up contract calculator
      patterns.py         # Pattern detection endpoints
      portfolio.py        # Portfolio CRUD + summary
      backtest.py         # Strategy backtest simulator
  services/
    bot/                  # Refactored bot sub-package
      bot_orchestrator.py # Main orchestrator (APScheduler job, no threading)
      arbitrage_scanner.py# Cross-marketplace arbitrage detection
      case_analyzer.py    # Case investment analysis
      sticker_analyzer.py # Sticker/capsule investment analysis
      watchlist_manager.py# Price watchlist management
      webhook_notifier.py # Discord/Telegram/generic notifications
    bot_engine.py         # Backward-compatible wrapper (delegates to bot/)
    job_queue.py          # Background job queue with retry + admin visibility
    portfolio_engine.py   # Portfolio holdings & P&L tracker
    backtest_engine.py    # Strategy backtesting on historical data
    ratio_engine.py       # 挂刀 ratio engine with concurrent scanning
    tradeup_engine.py     # Trade-up contract calculator + EV engine
    pattern_engine.py     # Pattern detection (blue gems, doppler phases, fade)
    market_fees.py        # Fee tables + fee-aware spread calculation
    steam.py              # Steam scraper (public)
    youpin.py             # Youpin scraper (auth via YOUPIN_TOKEN env)
    buff.py               # Buff scraper (auth via BUFF_SESSION_COOKIE env)
    skinport.py           # Skinport API scraper (public, Brotli required)
    csfloat.py            # CSFloat scraper (float data, stickers)
    scraper.py            # Background price scraper
    _http_utils.py        # Retry, rate limiting, circuit breaker pattern
  core/middleware/
    rate_limit.py         # Per-IP sliding window rate limiting
    circuit_breaker.py    # Circuit breaker for external APIs
  models/                 # DB models (SQLAlchemy, includes bot tables)
  schemas/                # Pydantic schemas
  db/
    database.py           # SQLAlchemy engine & session (SQLite or PostgreSQL)
alembic/                  # Database migrations
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
  bot.html                # Trading bot UI with SSE alerts & webhook mgmt
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

### Docker (PostgreSQL Production)
```bash
docker compose up -d
```

### Manual
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Database Migrations
```bash
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

## Key API Endpoints

All endpoints are **open by default** - no auth required.

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check (shows auth availability for Buff/Youpin) |
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
| `GET /api/v1/bot/recommendations` | Investment recommendations |
| `GET /api/v1/bot/insights` | Market insights |
| `POST /api/v1/bot/trigger-scan` | Manual bot scan (via job queue) |
| `GET /api/v1/bot/watchlist` | Price alert watchlist |
| `POST /api/v1/bot/watchlist` | Add watchlist item |
| `DELETE /api/v1/bot/watchlist/{id}` | Remove watchlist item |
| `GET /api/v1/bot/webhooks` | List webhook configurations |
| `POST /api/v1/bot/webhooks` | Add Discord/Telegram/generic webhook |
| `DELETE /api/v1/bot/webhooks/{id}` | Remove webhook |
| `POST /api/v1/bot/webhooks/test/{id}` | Send test notification |
| `GET /api/v1/bot/history` | Daily opportunity history |
| `GET /api/v1/bot/export/arbitrage` | CSV export of arbitrage |
| `GET /api/v1/bot/export/recommendations` | CSV export of recommendations |
| `GET /api/v1/admin/jobs` | Background job queue status |
| `GET /api/docs` | Swagger UI |

## Reverse Engineered Endpoints

### Youpin (api.youpin898.com) - Public + Auth
- `GET /api/commodity/Commodity/Detail?id={id}` - Item details (public)
- `GET /api/youpin/pc/query/filter/getSearchTags` - Categories (public)
- `GET /api/trade/Order/OrderDeliverStatistics` - Delivery stats (public)
- Search requires `YOUPIN_TOKEN` env var

### Buff163 (buff.163.com) - Requires Auth
- `GET /api/market/goods` - Search
- `GET /api/market/goods/sell_order` - Sell orders
- `GET /api/market/goods/price_history` - Price history
- Requires `BUFF_SESSION_COOKIE` env var

### Skinport (api.skinport.com/v1) - Public, Brotli Required
- `GET /v1/items?app_id=730&currency=CNY&tradable=0` - Full item catalog (20k+ items, cached 5 min)
- `Accept-Encoding: br` header is **required**
- Rate limit: 8 requests per 5 minutes

### Steam (Fully Public)
- `GET /market/search/render` - Search
- `GET /market/priceoverview` - Price overview

### CSFloat (csfloat.com) - Cloudflare Protected
- `GET /api/v1/listings` - Float listings with stickers
- Public API is behind Cloudflare; scraper disabled by default (`ENABLE_CSFLOAT=false`)

## Auth Configuration (Optional)

The API is open by default. Skinport works without auth. To enable Buff/Youpin search:

1. Log in via browser
2. Open DevTools → Network tab
3. Copy session cookie (Buff) or Authorization token (Youpin)
4. Set in `.env`:
   ```env
   BUFF_SESSION_COOKIE=your_cookie_here
   YOUPIN_TOKEN=your_token_here
   YOUPIN_DEVICE_ID=your_device_id_here
   ```

## Design System

- **Solid Dark**: Background `#0b0b0f`, elevated `#151519`, hover `#1e1e24`
- **Single Accent**: Blue `#3b82f6` only — no gradients, no glass, no animations
- **Spacing System**: xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48)
- **i18n**: Toggle between EN/CN via `data-i18n` attributes
- **Toast Notifications**: Top-right, success/error/warning/info
- **Skeleton Loaders**: Static placeholder (no shimmer animation)
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

# Marketplace Auth (optional)
BUFF_SESSION_COOKIE=
YOUPIN_TOKEN=
YOUPIN_DEVICE_ID=

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

## Notes for Agents

- **Routing Order**: Specific routes MUST come before parameterized routes in FastAPI
- **DB Path**: SQLite uses relative path `./data/cs2_scraper.db` - ensure working directory is correct
- **Background Scraper**: Runs via APScheduler, scrapes popular items every 30 min, ratios every 60 min
- **Bot Engine**: Runs as APScheduler job in the same event loop as the server (no threading). Scan interval is 60s.
- **Unicode**: Windows console may have encoding issues with Chinese characters; write to files instead
- **Rate Limiting**: Youpin's ALB blocks aggressive requests; add delays if extending scrapers
- **Open API**: All endpoints are public by design - no auth required for bot integration
- **PyInstaller Paths**: In launcher.py, `sys._MEIPASS` points to `_internal/` (bundled code+assets). Data/logs live next to the EXE.
- **Skinport Caching**: The `/v1/items` endpoint returns 20k+ items. The scraper caches them in-memory for 5 minutes and filters client-side.
- **Launcher Behavior**: Starts uvicorn as subprocess (dev) or background thread (frozen EXE), polls `/api/v1/health` for readiness, then auto-opens browser to `/bot`
- **SSE Alerts**: `/api/v1/alerts/stream` pushes watchlist alerts via Server-Sent Events. Bot UI auto-connects on load.
- **Portfolio Prices**: Call `POST /api/v1/portfolio/refresh` to update current prices from the latest price history entries.
- **Backtest Fallback**: If no price history exists in DB, synthetic deterministic data is generated for demo purposes.
- **Circuit Breakers**: External API calls are wrapped in circuit breakers. After 5 failures in 60s, the breaker opens and returns fallback data for 120s.
- **Webhook Security**: URLs are validated to prevent SSRF. Private IP ranges (10.x, 172.x, 192.168.x, 127.x) are rejected.
- **Job Queue**: Background scans are submitted to an in-memory priority queue with retry. View status at `/api/v1/admin/jobs`.
- **Docker**: Production Docker uses PostgreSQL by default. Local dev uses SQLite. Switch by changing `DATABASE_URL`.
- **Migrations**: Use Alembic for schema changes. Run `alembic upgrade head` after pulling updates that modify models.
