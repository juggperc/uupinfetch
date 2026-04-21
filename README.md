# Youpin CS2 Scraper

A beautiful, self-hosted API and landing page for scraping CS2 skin prices from Youpin (悠悠有品), Buff163, and Steam Community Market. Built for Chinese and Western traders with full CN/EN support.

![Liquid Glass Design](https://img.shields.io/badge/Design-Liquid%20Glass-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)

## Features

- **Multi-Source Support**: Youpin, Buff163, and Steam Community Market
- **Price History**: Track trends with interactive Chart.js visualizations
- **Smart Search**: Search across marketplaces instantly
- **Liquid Glass UI**: Stunning frosted-glass design with aurora backgrounds and animations
- **CN/EN i18n**: One-click language switching for Chinese and Western traders
- **REST API**: Auto-generated Swagger docs at `/api/docs`
- **SQLite Persistence**: Local database for cached data
- **Docker Deploy**: Single command deployment anywhere

## Quick Start

### Docker (Recommended)

```bash
git clone <repo-url>
cd youpin-cs2-scraper
docker compose up -d
```

Visit `http://localhost:8000`

### Manual

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/items/search` | GET | Search items across sources |
| `/api/v1/items/{id}` | GET | Item detail with price history |
| `/api/v1/items/{id}/price-history` | GET | Price history chart data |
| `/api/v1/categories` | GET | Item categories/filters |
| `/api/v1/market/summary` | GET | Market statistics |
| `/api/docs` | GET | Swagger UI |

### Search Example

```bash
curl "http://localhost:8000/api/v1/items/search?q=AK-47&source=steam"
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

## Authentication (Optional)

Youpin and Buff163 APIs require authentication for full access. To enable:

1. Log in to the respective platform in your browser
2. Extract cookies/session tokens
3. Set them as environment variables or pass to the scraper service

## Architecture

```
.
├── app/
│   ├── api/v1/         # REST API endpoints
│   ├── core/           # Config & settings
│   ├── db/             # SQLAlchemy database
│   ├── models/         # Database models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Scrapers (Youpin, Buff, Steam)
│   └── main.py         # FastAPI entry point
├── static/             # CSS, JS, images
├── templates/          # Jinja2 HTML templates
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Reverse Engineered Endpoints

### Youpin (api.youpin898.com)
- `GET /api/commodity/Commodity/Detail?id={id}` - Item details (public)
- `GET /api/youpin/pc/query/filter/getSearchTags` - Categories (public)
- `GET /api/trade/Order/OrderDeliverStatistics` - Delivery stats (public)
- Search/listings require authentication

### Buff163 (buff.163.com)
- `GET /api/market/goods` - Search items (requires auth)
- `GET /api/market/goods/sell_order` - Item sell orders (requires auth)
- `GET /api/market/goods/price_history` - Price history (requires auth)

### Steam Community Market
- `GET /market/search/render` - Public search
- `GET /market/priceoverview` - Public price overview

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, APScheduler
- **Frontend**: Vanilla JS, Chart.js, Jinja2 Templates
- **Design**: Liquid Glass CSS with backdrop-filter, CSS animations
- **Scraping**: httpx (async HTTP client)
- **Deployment**: Docker, Docker Compose

## License

MIT

## Disclaimer

This tool is for educational and personal trading research purposes. Respect the Terms of Service of all marketplaces. Use at your own risk.
