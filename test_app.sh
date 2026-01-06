#!/bin/bash
# Test script for Marketing Display App with local media

echo "=========================================="
echo "Marketing Display - Test Mode"
echo "=========================================="

# Create test media directory
mkdir -p ~/Documents/Marketing/test-media

echo ""
echo "Test media directory: ~/Documents/Marketing/test-media"
echo ""
echo "Instructions:"
echo "1. Add your test photos (jpg, png) to: ~/Documents/Marketing/test-media/"
echo "2. Add your test videos (mp4) to: ~/Documents/Marketing/test-media/"
echo ""
echo "Current media files:"
ls -lh ~/Documents/Marketing/test-media/ 2>/dev/null || echo "  (no files yet)"
echo ""

# Ask if user wants to run the app
read -p "Run the main application now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting application..."
    echo "Press Ctrl+C to stop"
    echo "Press ESC to exit fullscreen"
    echo ""
    
    # Set development mode
    export IS_DEVELOPMENT="true"
    export BACKEND_API_URL="http://localhost:5000"
    
    # Kill any existing instances
    pkill -9 python3 2>/dev/null
    
    # Run the app
    cd ~/Documents/Marketing
    python3 app.py
fi
