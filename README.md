# CS2 Price Scraper

Open-source CS2 skin price scraper built for trading bot developers. Fetches real-time prices from Steam Community Market, Youpin (悠悠有品), and Buff163. Run it locally on your machine or deploy to a VPS - your data stays yours.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://docker.com)

## Quick Start

### Local (30 seconds)

**Linux/Mac:**
```bash
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
./setup.sh     # One-time setup
./start.sh     # Start server
```

**Windows:**
```powershell
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
setup.bat      # One-time setup
start.bat      # Start server
```

**Visit:** `http://localhost:8000`

### Docker

```bash
docker compose up -d
```

### Manual (if you prefer)

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Connect Your Trading Bot

All API endpoints are **open by default** - no auth, no API keys, no rate limits. Just query and go.

### Python Example

```python
import requests

BASE = "http://localhost:8000"

# Search for items
r = requests.get(f"{BASE}/api/v1/items/search", params={
    "q": "AK-47",
    "source": "steam",
    "page_size": 20
})
data = r.json()

for item in data["items"]:
    print(f"{item['name']}: {item['price']} CNY")

# Get item detail
item_id = data["items"][0]["external_id"]
r = requests.get(f"{BASE}/api/v1/items/{item_id}?source=steam")
detail = r.json()
print(f"Lowest price: {detail['item']['lowest_price']}")
```

See `examples/` for complete trading bot implementations:
- `examples/basic_bot.py` - Price search, monitoring, arbitrage detection
- `examples/advanced_bot.py` - SQLite-backed trend analysis with alerts

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/health` | - | Health check |
| `GET /api/v1/items/search?q=AK-47` | - | Search items across sources |
| `GET /api/v1/items/{id}?source=steam` | - | Item detail with price history |
| `GET /api/v1/items/popular?limit=8` | - | Trending items from DB |
| `GET /api/v1/items/{id}/price-history` | - | Historical price chart data |
| `GET /api/v1/categories` | - | Item categories/filters |
| `GET /api/v1/market/summary` | - | Market statistics |
| `GET /api/docs` | - | Interactive Swagger UI |

### Query Parameters

- `q` - Search query (required for search)
- `source` - Data source: `steam`, `buff`, `youpin`, or `all`
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 20, max: 100)
- `days` - Price history range (default: 7)

### Data Sources

| Source | Auth Required | Status |
|--------|--------------|--------|
| **Steam Community Market** | No | Fully working |
| **Youpin (悠悠有品)** | No (public endpoints) | Item detail, categories |
| **Buff163** | Yes (cookies) | Structured, needs auth |

## Reverse Engineered Endpoints

### Youpin (api.youpin898.com)
- `GET /api/commodity/Commodity/Detail?id={id}` - Item details
- `GET /api/youpin/pc/query/filter/getSearchTags` - Categories
- `GET /api/trade/Order/OrderDeliverStatistics` - Delivery stats

### Buff163 (buff.163.com)
- `GET /api/market/goods` - Search items
- `GET /api/market/goods/sell_order` - Sell orders
- `GET /api/market/goods/price_history` - Price history

### Steam Community Market
- `GET /market/search/render` - Public search
- `GET /market/priceoverview` - Price overview

## Authentication (Optional)

The API is open by default. If you want to add auth for Buff/Youpin search endpoints:

1. Log in to the platform in your browser
2. Extract cookies/session tokens from browser dev tools
3. Add them to `app/services/buff.py` or `app/services/youpin.py`

## Architecture

```
app/
  api/v1/endpoints.py     # REST API routes (open, no auth)
  core/config.py          # Settings & env vars
  core/logging.py         # Logging setup
  db/database.py          # SQLAlchemy engine
  models/models.py        # DB models
  schemas/schemas.py      # Pydantic models
  services/
    steam.py              # Steam scraper (public, working)
    youpin.py             # Youpin scraper (public endpoints)
    buff.py               # Buff scraper (needs auth)
    scraper.py            # Background scraper
  main.py                 # FastAPI entry point
examples/
  basic_bot.py            # Simple bot example
  advanced_bot.py         # Trend analysis bot
static/                   # CSS, JS, images
templates/                # Jinja2 HTML pages
data/                     # SQLite database (auto-created)
```

## Configuration

Copy `.env.example` to `.env` and customize:

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db
ENABLE_YOUPIN=true
ENABLE_BUFF=true
SCRAPE_INTERVAL_MINUTES=30
```

## Design

- **Liquid Glass UI**: Frosted glass with `backdrop-filter`, aurora backgrounds, smooth animations
- **CN/EN i18n**: One-click language switching
- **Responsive**: Works on desktop and mobile

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic, APScheduler
- **Frontend**: Vanilla JS, Chart.js, Jinja2 Templates
- **Scraping**: httpx (async HTTP)
- **Database**: SQLite (default), PostgreSQL supported
- **Deployment**: Docker, Docker Compose

## License

MIT - Use it freely for your trading bots.

## Disclaimer

This tool is for educational and personal trading research. Respect the Terms of Service of all marketplaces. Use at your own risk.
