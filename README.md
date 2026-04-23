# CS2 Price Scraper + Trading Intelligence Platform

**English** | [中文](README_CN.md)

Open-source CS2 skin price scraper and trading intelligence platform built for traders and bot developers. Fetches real-time prices from **Steam Community Market, Youpin (悠悠有品), Buff163, and Skinport**. Features a built-in trading bot, portfolio tracker, backtesting engine, trade-up contract calculator, pattern detection engine, 挂刀 (Steam balance conversion) ratio engine, and **webhook notifications** for Discord/Telegram.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://docker.com)

## Quick Start (Pick One)

### Option 1: Standalone EXE (Easiest — No Python Required)

Download and unzip `CS2PriceScraper.zip` from [Releases](https://github.com/juggperc/uupinfetch/releases), then double-click `CS2PriceScraper.exe`.

- Runs in your **system tray**
- **Auto-opens** your browser to the Bot UI
- Server + trading bot start automatically
- Right-click tray icon for: Dashboard, Bot UI, Trigger Scan, View Logs, Quit

### Option 2: One-Command Launch (Windows)

```bat
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
start-easy.bat    :: Auto-installs deps, starts server, opens browser
```

**That's it.** Your browser opens to the Trading Bot UI at `http://localhost:8000/bot`

### Option 3: One-Command Launch (Linux/Mac)

```bash
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
./start-easy.sh   # Auto-installs deps, starts server, opens browser
```

### Option 4: Docker

```bash
docker compose up -d
```

Then open `http://localhost:8000/bot`

## What You Get

### Trading Bot (Auto-Started)
The bot launches automatically with the server and continuously scans for:

| Feature | Description |
|---------|-------------|
| **Arbitrage Scanner** | Cross-marketplace price spreads with fee-adjusted net profit (Steam vs Buff vs Youpin vs Skinport) |
| **Case Investments** | Drop-pool rotation analysis, expected ROI for case hoarding |
| **Sticker/Capsule** | Major timing strategy — buy during major, sell 3-6 months after |
| **Float Arbitrage** | Underpriced low-float items in wrong exterior tier |
| **Pattern Premiums** | Tracks doppler phases, fade %, case hardened patterns |
| **Webhook Alerts** | Instant Discord/Telegram notifications for watchlist hits & high-confidence arbitrage |
| **Market Insights** | Live intelligence on market momentum and opportunities |

### Web UI
- **Bot Dashboard** (`/bot`) - Live arbitrage ops, investment signals, market insights, watchlist, webhook management
- **Portfolio Tracker** (`/portfolio`) - Holdings, P&L, allocation chart, transaction history
- **Backtest Simulator** (`/backtest`) - Run buy-and-hold, mean reversion, momentum, and DCA strategies on historical data
- **挂刀 Ratios** (`/ratios`) - Best Steam balance conversion items ranked by ratio
- **Trade-Up Calculator** (`/tradeup`) - EV calculator and profitable contract scanner
- **Item Search** (`/search`) - Browse skins with price charts
- **API Docs** (`/api/docs`) - Interactive Swagger documentation
- **Dashboard** (`/dashboard`) - Server status, quick API tester

### REST API (Open — No Auth Required)
All endpoints are open. Connect your trading bot instantly.

```python
import requests

BASE = "http://localhost:8000"

# Search items
r = requests.get(f"{BASE}/api/v1/items/search?q=AK-47")
for item in r.json()["items"]:
    print(f"{item['name']}: {item['price']} CNY")

# Get bot arbitrage opportunities
r = requests.get(f"{BASE}/api/v1/bot/arbitrage")
for opp in r.json():
    print(f"Buy {opp['item_name']} @ {opp['buy_price']} → Sell @ {opp['sell_price']}")

# Get investment recommendations
r = requests.get(f"{BASE}/api/v1/bot/recommendations")
for rec in r.json():
    print(f"{rec['item_name']}: +{rec['expected_roi_pct']}% ROI expected")
```

## API Endpoints

### Price Data
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/items/search?q=AK-47` | Search items across sources |
| `GET /api/v1/items/{id}` | Item detail with price history |
| `GET /api/v1/items/popular` | Trending items from DB |
| `GET /api/v1/items/compare?q=AK-47` | Compare prices across all sources instantly |
| `GET /api/v1/categories` | Item categories/filters |

### Bot Intelligence
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/bot/status` | Bot running status |
| `GET /api/v1/bot/arbitrage` | Live arbitrage opportunities |
| `GET /api/v1/bot/recommendations` | Investment recommendations |
| `GET /api/v1/bot/insights` | Market insights & intelligence |
| `GET /api/v1/bot/stats` | Aggregated bot statistics |
| `POST /api/v1/bot/trigger-scan` | Manually trigger a scan |
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

### Portfolio & Backtest
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/portfolio` | Portfolio holdings |
| `POST /api/v1/portfolio` | Add portfolio item |
| `DELETE /api/v1/portfolio/{id}` | Remove portfolio item |
| `GET /api/v1/portfolio/summary` | P&L and allocation summary |
| `POST /api/v1/portfolio/refresh` | Refresh prices from DB |
| `GET /api/v1/backtest/strategies` | Available strategies |
| `POST /api/v1/backtest/run` | Run strategy backtest |

### Utilities
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/ratios` | 挂刀 Steam balance conversion ratios |
| `GET /api/v1/tradeup/scan` | Scan profitable trade-ups |
| `POST /api/v1/tradeup/calculate` | Calculate trade-up EV |
| `GET /api/v1/patterns/analyze` | Analyze skin pattern value |
| `GET /api/v1/alerts/stream` | SSE real-time alert stream |

## Trading Bot Examples

See `examples/` for ready-to-use bot integrations:

### `examples/basic_bot.py`
Simple trading bot that monitors prices and detects arbitrage:
```bash
python examples/basic_bot.py
```

### `examples/advanced_bot.py`
SQLite-backed bot with trend analysis, watchlists, and alerts:
```bash
python examples/advanced_bot.py
```

## Architecture

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
  basic_bot.py            # Simple bot example
  advanced_bot.py         # Trend analysis bot
templates/
  bot.html                # Trading bot UI with SSE alerts & webhook management
  portfolio.html          # Portfolio tracker with P&L & allocation chart
  backtest.html           # Strategy backtest simulator
  ratios.html             # 挂刀 ratio ranking table
  tradeup.html            # Trade-up contract scanner
  search.html             # Item search
  dashboard.html          # API tester dashboard
static/                   # CSS, JS, images
data/                     # SQLite databases (auto-created)
```

## Production Features

| Feature | Description |
|---------|-------------|
| **Rate Limiting** | Per-IP sliding window: 60 req/min general, 30 req/min search, 10 req/min scans |
| **Circuit Breakers** | Automatic fail-fast when Steam/Buff/Youpin APIs are down; returns cached/demo data |
| **Job Queue** | Background tasks with retry (exponential backoff) and admin visibility at `/api/v1/admin/jobs` |
| **Webhook Security** | SSRF protection — rejects private IP ranges (10.x, 172.x, 192.168.x, 127.x) |
| **Graceful Shutdown** | SIGTERM handling for Docker; bot stops cleanly with the server |
| **Health Checks** | Docker `HEALTHCHECK` endpoint + `/api/v1/health` |
| **PostgreSQL Ready** | SQLite for dev, PostgreSQL for production Docker — one-line switch |
| **Alembic Migrations** | Versioned database schema upgrades |

## Competitive Comparison

We compared our platform against the most popular open-source CS2 trading bots on GitHub to ensure it is genuinely useful, as or more powerful, and easier to use.

| Feature | **CS2 Price Scraper** | [Netease-Buff-Trade-Bot](https://github.com/SolitudeRA/Netease-Buff-Trade-Bot) | [CS2-Skin-Arbitrage-Bot](https://github.com/Pupsickk/CS2-Skin-Arbitrage-Bot-for-Buff163---Commercial-Solution) | [cs2_skins_trading_arbitrage](https://github.com/dev-kostiuk/cs2_skins_trading_arbitrage) |
|---------|:---------------------:|:-------------------------------------------------------------------------------:|:-----------------------------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------:|
| **Markets** | 4 (Steam, Buff, Youpin, Skinport) | 1 (Buff only) | 1 (Buff only) | 2 (DMarket, WhiteMarket) |
| **Web UI** | Full dashboard + 8 pages | None (Chrome extension) | None | None |
| **Portfolio Tracker** | P&L, allocation, transactions | No | No | No |
| **Backtesting** | 4 strategies, Sharpe, drawdown | No | No | No |
| **Trade-Up Calculator** | EV engine + scanner | No | No | No |
| **Pattern Detection** | Blue gems, doppler, fade | No | No | No |
| **挂刀 Ratios** | Yes, concurrent scan | No | No | No |
| **Notifications** | **Discord + Telegram + SSE** | None | Telegram only | Telegram only |
| **Rate Limiting** | **Built-in** | No | No | No |
| **Circuit Breakers** | **Built-in** | No | No | No |
| **Open API** | Yes, all endpoints public | No | No | No |
| **i18n** | English + Chinese | English only | English only | English + Ukrainian |
| **Setup** | One command or double-click EXE | Manual Chrome extension load | Manual Python + Chrome setup | 4 repos + PM2 + databases |
| **License** | MIT (fully open) | GPL-3.0 | Commercial feel | Open source |

**Bottom line:** Our platform is the only open-source solution that combines multi-market coverage, a full web UI, portfolio tracking, backtesting, trade-up calculation, pattern detection, webhook notifications, rate limiting, circuit breakers, and instant setup — all with a genuinely open API.

## CS2 Market Intelligence

The bot understands CS2-specific mechanics:

### Case Investment Logic
- **Common drop cases** (< 1 CNY): 20-40% annual appreciation as they rotate out
- **Active drop cases** (1-5 CNY): 10-20% gains during major updates
- **Rare cases** (> 20 CNY): Premium holding, stable appreciation

### Sticker Capsule Strategy
- Buy capsules **during** the major (while they're dropping)
- Sell **3-6 months after** the major ends
- Historical ROI: 50-200% for recent majors

### Float/Wear Arbitrage
- Low-float Field-Tested skins trade near Minimal Wear prices
- Check float values on Buff163 for true arbitrage
- Pattern index matters for doppler, fade, case hardened

### Authentication (Optional)
The API is open by default. To unlock **live** Buff/Youpin search:

1. Log in to Buff163 or Youpin via your browser
2. Open browser DevTools → Network tab
3. Find any authenticated request and copy:
   - **Buff**: the `Cookie` header value → paste into `BUFF_SESSION_COOKIE`
   - **Youpin**: the `Authorization` Bearer token → paste into `YOUPIN_TOKEN`
4. Restart the server

If auth is not configured, the app gracefully falls back to Steam + Skinport data and shows a banner in the UI.

## Configuration

Copy `.env.example` to `.env`:

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db

# Scraper Sources
ENABLE_YOUPIN=true
ENABLE_BUFF=true
ENABLE_SKINPORT=true
ENABLE_CSFLOAT=false

# Marketplace Auth (optional — required for live Buff/Youpin search)
BUFF_SESSION_COOKIE=your_buff_cookie_here
YOUPIN_TOKEN=your_youpin_token_here
YOUPIN_DEVICE_ID=your_device_id_here

# Background Scraper
SCRAPE_INTERVAL_MINUTES=30

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### PostgreSQL (Docker Production)

The `docker-compose.yml` includes a PostgreSQL service by default. No config changes needed — just run:

```bash
docker compose up -d
```

For local development, keep SQLite (default). For production Docker, PostgreSQL is used automatically.

### Database Migrations

```bash
# After pulling updates that change models
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, APScheduler
- **Bot Engine**: Async market scanner with CS2-specific heuristics
- **Frontend**: Solid dark theme, Chart.js, Jinja2 templates
- **Database**: SQLite (server + bot share data)
- **Scraping**: httpx async HTTP client

## License

MIT - Use it freely for your trading bots.

## Disclaimer

This tool is for educational and personal trading research. Respect the Terms of Service of all marketplaces. Use at your own risk.
