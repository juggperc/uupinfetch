#!/bin/bash
echo "Starting Youpin CS2 Scraper..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
