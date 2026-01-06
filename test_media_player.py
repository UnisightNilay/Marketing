"""
Simple test for media player with local files
"""
import sys
import os
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from media_player_vlc import MediaPlayerApp
from config import Config
from utils import setup_logging

# Setup logging
setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)

# Load playlist from JSON file
playlist_file = os.path.join(os.path.dirname(__file__), 'test-playlist.json')

# Load and parse the playlist
try:
    with open(playlist_file, 'r') as f:
        playlist_data = json.load(f)
    
    test_playlist = playlist_data.get('items', [])
    
    # Convert relative paths to absolute
    base_dir = os.path.dirname(__file__)
    for item in test_playlist:
        if not os.path.isabs(item['path']):
            item['path'] = os.path.join(base_dir, item['path'])
    
    # Sort by order
    test_playlist.sort(key=lambda x: x.get('order', 0))
    
except json.JSONDecodeError as e:
    print(f"\n❌ ERROR: Invalid JSON in {playlist_file}")
    print(f"   {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERROR: Failed to load playlist: {e}")
    sys.exit(1)

if not test_playlist:
    print("\n" + "="*50)
    print("NO MEDIA ITEMS IN PLAYLIST!")
    print("="*50)
    print(f"\nThe playlist file is empty or has no items.")
    print(f"Please edit: {playlist_file}")
    print("="*50 + "\n")
    sys.exit(1)

# Validate all files exist
missing_files = []
for item in test_playlist:
    if not os.path.exists(item['path']):
        missing_files.append(item['path'])

if missing_files:
    print("\n" + "="*50)
    print("MISSING MEDIA FILES!")
    print("="*50)
    print("\nThe following files in the playlist were not found:")
    for path in missing_files:
        print(f"  ❌ {path}")
    print("\nPlease add these files or update the playlist.")
    print("="*50 + "\n")
    sys.exit(1)

print("\n" + "="*50)
print(f"Loaded playlist: {playlist_data.get('playlistId', 'Unknown')}")
print(f"Version: {playlist_data.get('version', 'N/A')}")
print(f"Media items: {len(test_playlist)}")
print("="*50)
for i, item in enumerate(test_playlist, 1):
    duration = f" ({item['duration']}s)" if item.get('duration') else ""
    filename = os.path.basename(item['path'])
    print(f"{i}. {item['type'].upper()}: {filename}{duration}")
print("="*50)
print("\nControls:")
print("  ESC          - Exit fullscreen or quit")
print("  F            - Toggle fullscreen")
print("  Space/Right  - Next media")
print("  Left         - Previous media")
print("="*50 + "\n")

# Create and run app
app = QApplication(sys.argv)

# Hide mouse cursor globally
app.setOverrideCursor(QCursor(Qt.BlankCursor))


player_app = MediaPlayerApp(test_playlist)

# Show fullscreen or windowed
if Config.FULLSCREEN:
    player_app.showFullScreen()
else:
    player_app.show()

sys.exit(app.exec_())
