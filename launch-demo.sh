#!/bin/bash
# APProved Medical Writing Platform — Launch Script
# Starts the Flask development server and opens the landing page in your browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  APProved Medical Writing Platform"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9 or later."
    exit 1
fi

PY_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Python $PY_VERSION"

# Check dependencies
echo "✓ Checking dependencies…"
python3 -c "import flask, sqlalchemy" 2>/dev/null || {
    echo "⚠ Installing dependencies with pip…"
    python3 -m pip install -q flask sqlalchemy python-pptx markupsafe
}

# Kill any existing server on port 5001
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠ Port 5001 already in use. Stopping existing process…"
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo ""
echo "🚀 Starting APProved server…"
echo ""

# Start the server
OPEN_BROWSER=1 python3 app.py &
PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server to start…"
for i in {1..30}; do
    if curl -s http://localhost:5001 > /dev/null 2>&1; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  ✅ Server running at http://localhost:5001"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  • Tool workspace: Start with a blank engagement"
        echo "  • CGM demo: Pre-loaded example with pivotal data"
        echo ""
        echo "  Press Ctrl+C to stop the server"
        echo ""
        break
    fi
    sleep 0.5
done

# Keep the script running
wait $PID
