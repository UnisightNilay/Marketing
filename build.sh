#!/bin/bash
# Build script to create standalone executable

echo "Building Marketing Display Application..."

# Activate virtual environment
source .venv/bin/activate

# Install PyInstaller if not already installed
pip install pyinstaller

# Build the application
pyinstaller --onefile \
    --name marketing-display \
    --add-data "Assets:Assets" \
    --add-data "test-media:test-media" \
    --add-data ".env.development:./" \
    --add-data ".env.staging:./" \
    --add-data ".env.production:./" \
    --hidden-import PyQt5 \
    --hidden-import vlc \
    --hidden-import PIL \
    --hidden-import aiohttp \
    --hidden-import signalrcore \
    --hidden-import dotenv \
    --windowed \
    app.py

echo ""
echo "Build complete!"
echo "Executable location: dist/marketing-display"
echo ""
echo "To deploy to Raspberry Pi:"
echo "  scp dist/marketing-display unisight@10.0.120.163:~/"
echo "  scp -r Assets test-media Config unisight@10.0.120.163:~/marketing-app/"
echo ""
