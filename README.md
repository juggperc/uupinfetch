# CS2 Price Scraper + Trading Bot

Open-source CS2 skin price scraper with a **built-in trading bot** that runs alongside the server. Fetches real-time prices from Steam Community Market, Youpin (悠悠有品), and Buff163. Detects arbitrage opportunities and generates investment signals tailored to the CS2 market.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://docker.com)

## One-Command Launch (Windows)

```bat
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
setup.bat    :: One-time setup
start.bat    :: Launches server + bot + opens browser
```

**That's it.** Your browser opens to the Trading Bot UI at `http://localhost:8000/bot`

## One-Command Launch (Linux/Mac)

```bash
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
./setup.sh   # One-time setup
./start.sh   # Launches server + bot + opens browser
```

## What You Get

### Trading Bot (Auto-Started)
The bot launches automatically with the server and continuously scans for:

| Feature | Description |
|---------|-------------|
| **Arbitrage Scanner** | Cross-marketplace price spreads (Steam vs Buff vs Youpin) |
| **Case Investments** | Drop-pool rotation analysis, expected ROI for case hoarding |
| **Sticker/Capsule** | Major timing strategy - buy during major, sell 3-6 months after |
| **Float Arbitrage** | Underpriced low-float items in wrong exterior tier |
| **Pattern Premiums** | Tracks doppler phases, fade %, case hardened patterns |
| **Market Insights** | Live intelligence on market momentum and opportunities |

### Web UI
- **Bot Dashboard** (`/bot`) - Live arbitrage ops, investment signals, market insights
- **Item Search** (`/search`) - Browse skins with price charts
- **API Docs** (`/api/docs`) - Interactive Swagger documentation
- **Dashboard** (`/dashboard`) - Server status, quick API tester

### REST API (Open - No Auth)
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

## Docker

```bash
docker compose up -d
```

Then open `http://localhost:8000/bot`

## Architecture

```
app/
  main.py                 # FastAPI entry + bot launcher
  api/v1/
    endpoints.py          # Price data API (open)
    bot.py                # Bot intelligence API
    auth.py               # Optional user auth
  services/
    bot_engine.py         # CS2 trading bot engine
    steam.py              # Steam scraper (public)
    youpin.py             # Youpin scraper (public endpoints)
    buff.py               # Buff scraper (needs auth)
    scraper.py            # Background price scraper
  models/                 # DB models
  schemas/                # Pydantic schemas
examples/
  basic_bot.py            # Simple bot example
  advanced_bot.py         # Trend analysis bot
templates/
  bot.html                # Trading bot UI
  index.html              # Landing page
  search.html             # Item search
  dashboard.html          # API tester dashboard
static/                   # CSS, JS, images
data/                     # SQLite databases (auto-created)
```

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
The API is open by default. To unlock Buff/Youpin search:
1. Log in to the platform via browser
2. Extract cookies/session tokens
3. Add to `app/services/buff.py` or `app/services/youpin.py`

## Configuration

Copy `.env.example` to `.env`:

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db
ENABLE_YOUPIN=true
ENABLE_BUFF=true
SCRAPE_INTERVAL_MINUTES=30
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, APScheduler
- **Bot Engine**: Async market scanner with CS2-specific heuristics
- **Frontend**: Liquid Glass UI, Chart.js, Jinja2
- **Database**: SQLite (server + bot share data)
- **Scraping**: httpx async HTTP client

## License

MIT - Use it freely for your trading bots.

## Disclaimer

This tool is for educational and personal trading research. Respect the Terms of Service of all marketplaces. Use at your own risk.
