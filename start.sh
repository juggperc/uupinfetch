#!/bin/bash
echo "============================================"
echo "  CS2 Price Scraper + Trading Bot"
echo "============================================"
echo ""

# Activate venv if exists
if [ -d "venv" ]; then
    echo "[1/4] Activating virtual environment..."
    source venv/bin/activate
else
    echo "[1/4] No venv found. Using system Python."
    echo "         Run ./setup.sh first if you encounter issues."
fi

# Ensure data directory
mkdir -p data

echo "[2/4] Starting FastAPI server + Trading Bot..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

echo "[3/4] Waiting for server to start..."
sleep 4

echo "[4/4] Opening Trading Bot UI..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000/bot
elif command -v open &> /dev/null; then
    open http://localhost:8000/bot
fi

echo ""
echo "============================================"
echo "  All systems running!"
echo ""
echo "  Bot UI:     http://localhost:8000/bot"
echo "  Search:     http://localhost:8000/search"
echo "  API Docs:   http://localhost:8000/api/docs"
echo "  Dashboard:  http://localhost:8000/dashboard"
echo ""
echo "  Press Ctrl+C to stop"
echo "============================================"
echo ""

wait $SERVER_PID
