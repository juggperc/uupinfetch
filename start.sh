#!/bin/bash
echo "Starting CS2 Price Scraper..."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
