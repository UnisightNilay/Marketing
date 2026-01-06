#!/bin/bash
# Development run script for Marketing Display Application

# Set development mode
export IS_DEVELOPMENT="true"
export BACKEND_API_URL="${BACKEND_API_URL:-http://localhost:5000}"

# Print configuration
echo "=========================================="
echo "Marketing Display - Development Mode"
echo "=========================================="
echo "Backend API: $BACKEND_API_URL"
echo "Development Mode: $IS_DEVELOPMENT"
echo "=========================================="
echo ""

# Check if dependencies are installed
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "Error: PyQt5 not installed"
    echo "Install with: pip3 install -r requirements.txt"
    exit 1
fi

# Run application
python3 app.py
