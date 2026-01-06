# Raspberry Pi Marketing Display Application

A Python-based digital signage application for Raspberry Pi 5 that displays marketing photos and videos with real-time content updates via SignalR.

## Features

### Core Functionality
- ✅ Display photos with configurable duration
- ✅ Display videos (full playback, no controls visible)
- ✅ Fetch content playlist from backend API (JSON)
- ✅ Download media from Azure Blob Storage URLs
- ✅ Local media caching (64GB storage)
- ✅ Real-time updates via SignalR/WebSocket
- ✅ Automatic content refresh when backend signals changes
- ✅ Fullscreen kiosk mode

### Network Management
- ✅ Automatic internet connectivity check on startup
- ✅ WiFi selection UI when no internet connection
- ✅ Scan and display available WiFi networks
- ✅ Show signal strength and security status
- ✅ Password input for secured networks
- ✅ Automatic transition to main app after connection

### Platform Support
- ✅ Cross-platform development (Linux development machine → Raspberry Pi deployment)
- ✅ Environment detection (development vs production)
- ✅ Hardware acceleration support on Raspberry Pi
- ✅ Optimized for 2GB RAM

## System Requirements

### Hardware
- Raspberry Pi 5 (2GB RAM)
- 64GB microSD card or SSD
- HDMI display/TV
- WiFi connection
- Power supply

### Software
- Raspberry Pi OS Lite (64-bit) with X11
- Python 3.9+
- NetworkManager (for WiFi management)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Entry Point                   │
│                         (app.py)                             │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────▼──────────┐
        │  Internet Check      │
        └───────┬──────────────┘
                │
        ┌───────▼──────────────────────────────────┐
        │                                           │
        │  No Internet             Internet OK     │
        │       │                       │           │
        │       ▼                       ▼           │
        │  WiFi Setup UI        Main Display App   │
        │  (wifi_setup.py)      (media_player.py)  │
        │       │                       │           │
        │       └───────┬───────────────┘           │
        │               │                           │
        └───────────────┼───────────────────────────┘
                        │
        ┌───────────────▼──────────────────────────┐
        │         Main Display Loop                │
        │  ┌────────────────────────────────┐      │
        │  │  Media Playback Engine         │      │
        │  │  - Video Player (QMediaPlayer) │      │
        │  │  - Image Display (QLabel)      │      │
        │  │  - Transition Controller       │      │
        │  └────────────────────────────────┘      │
        │                                           │
        │  ┌────────────────────────────────┐      │
        │  │  Background Services           │      │
        │  │  - SignalR Client              │      │
        │  │  - Media Downloader (async)    │      │
        │  │  - Cache Manager               │      │
        │  │  - Playlist Manager            │      │
        │  └────────────────────────────────┘      │
        └───────────────────────────────────────────┘
```

## API Contract

### Backend JSON Format

```json
{
  "playlistId": "playlist-123",
  "version": "1.0.0",
  "lastUpdated": "2026-01-02T10:30:00Z",
  "items": [
    {
      "id": "item-1",
      "type": "photo",
      "url": "https://storage.blob.core.windows.net/media/photo1.jpg",
      "duration": 10,
      "order": 1
    },
    {
      "id": "item-2",
      "type": "video",
      "url": "https://storage.blob.core.windows.net/media/video1.mp4",
      "order": 2
    },
    {
      "id": "item-3",
      "type": "photo",
      "url": "https://storage.blob.core.windows.net/media/photo2.jpg",
      "duration": 15,
      "order": 3
    }
  ]
}
```

### SignalR Messages

**Hub Connection:**
- Hub URL: `{backend_url}/marketingHub`

**Messages from Backend:**
```json
{
  "type": "PlaylistUpdated",
  "playlistId": "playlist-123",
  "action": "refresh"
}
```

**Actions:**
- `refresh` - Fetch and reload entire playlist
- `add` - Add new item to playlist
- `remove` - Remove item from playlist
- `update` - Update specific item

## Project Structure

```
marketing-display/
├── README.md                      # This file
├── REQUIREMENTS.md                # Detailed requirements
├── requirements.txt               # Python dependencies
├── config.py                      # Configuration settings
├── app.py                         # Main entry point
├── wifi_setup.py                  # WiFi configuration UI
├── media_player.py                # Media playback engine
├── signalr_client.py              # SignalR connection handler
├── media_downloader.py            # Download and cache manager
├── playlist_manager.py            # Playlist state management
├── utils.py                       # Helper functions
├── install.sh                     # Raspberry Pi installation script
├── deploy.sh                      # Deployment script from dev machine
├── run_dev.sh                     # Development run script
├── systemd/
│   └── marketing-display.service  # Systemd service file
└── tests/
    ├── test_media_player.py
    ├── test_downloader.py
    └── sample_playlist.json       # Test data
```

## Installation

### Development Machine (Linux)

```bash
# Clone repository
cd ~/Documents/Marketing
git clone <repository-url> marketing-display
cd marketing-display

# Install dependencies
pip3 install -r requirements.txt

# Run in development mode
./run_dev.sh
```

### Raspberry Pi

```bash
# Copy files to Pi
scp -r marketing-display/ pi@raspberrypi.local:~/

# SSH into Pi
ssh pi@raspberrypi.local
cd ~/marketing-display

# Run installation script
chmod +x install.sh
./install.sh

# Enable and start service
sudo systemctl enable marketing-display
sudo systemctl start marketing-display
```

## Configuration

Edit `config.py` to configure:
- Backend API URL
- SignalR Hub URL
- Media cache directory
- Cache size limits
- Retry policies
- Logging settings

## Development

### Run in Development Mode
```bash
./run_dev.sh
```

### Deploy to Raspberry Pi
```bash
./deploy.sh
```

### Check Logs
```bash
# On Raspberry Pi
sudo journalctl -u marketing-display -f
```

## Memory Optimization

- OS + X11: ~200MB
- Application: ~150-250MB
- Video Cache: ~200-400MB
- **Total: ~600-850MB** (plenty of headroom on 2GB RAM)

## Troubleshooting

### WiFi Not Connecting
- Check NetworkManager is running: `sudo systemctl status NetworkManager`
- Manual connection: `nmcli device wifi connect "SSID" password "PASSWORD"`

### Video Not Playing
- Check VLC installed: `vlc --version`
- Check video codecs: `sudo apt install -y libavcodec-extra`

### Service Not Starting
- Check logs: `sudo journalctl -u marketing-display -n 50`
- Test manually: `python3 /home/pi/marketing-display/app.py`

## License

[Your License]

## Contributors

[Your Team]
