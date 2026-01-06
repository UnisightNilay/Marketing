# Quick Start Guide

## Development Machine Setup

### 1. Install Dependencies

```bash
cd ~/Documents/Marketing

# Install Python dependencies
pip3 install -r requirements.txt

# Or install system-wide (may require sudo)
sudo apt install python3-pyqt5 python3-pyqt5.qtmultimedia
```

### 2. Configure Backend API

```bash
# Set environment variable
export BACKEND_API_URL="http://your-backend-api.com"

# Or edit config.py directly
```

### 3. Run in Development Mode

```bash
# Run the application
./run_dev.sh

# Or directly
python3 app.py
```

### 4. Test WiFi Setup UI (Standalone)

```bash
python3 wifi_setup.py
```

### 5. Test Media Player (Standalone)

Edit `media_player.py` to update test_playlist with your media files, then:

```bash
python3 media_player.py
```

## Keyboard Shortcuts (Development Mode)

- **ESC** - Exit fullscreen or quit
- **F** - Toggle fullscreen
- **Right Arrow / Space** - Next media
- **Left Arrow** - Previous media

## Testing Without Backend

The application includes mock data for development:

1. **WiFi Setup** - Shows mock networks if nmcli is not available
2. **Playlist** - Can use local JSON file (see `tests/sample_playlist.json`)
3. **SignalR** - Gracefully handles connection failures

## Project Structure

```
marketing-display/
├── app.py                 # Main application
├── config.py              # Configuration
├── utils.py               # Utility functions
├── wifi_setup.py          # WiFi configuration UI
├── media_player.py        # Media playback engine
├── signalr_client.py      # Real-time updates
├── media_downloader.py    # Download manager
├── playlist_manager.py    # Playlist management
├── run_dev.sh             # Development run script
├── install.sh             # Raspberry Pi installation
├── deploy.sh              # Deployment script
└── requirements.txt       # Python dependencies
```

## Next Steps

1. **Install dependencies**: `pip3 install -r requirements.txt`
2. **Test WiFi UI**: `python3 wifi_setup.py`
3. **Create test media**: Add some images/videos
4. **Run full app**: `./run_dev.sh`

## Deploy to Raspberry Pi

```bash
# Set your Pi's hostname or IP
export PI_HOST="raspberrypi.local"

# Deploy
./deploy.sh

# Or manually copy
scp -r . pi@raspberrypi.local:~/marketing-display/

# SSH and install
ssh pi@raspberrypi.local
cd ~/marketing-display
./install.sh
```

## Troubleshooting

### PyQt5 Not Found

```bash
# Try pip install
pip3 install PyQt5

# Or system package
sudo apt install python3-pyqt5 python3-pyqt5.qtmultimedia
```

### VLC Not Found

```bash
sudo apt install vlc libvlc-dev python3-vlc
pip3 install python-vlc
```

### NetworkManager Not Found

```bash
sudo apt install network-manager
sudo systemctl start NetworkManager
sudo systemctl enable NetworkManager
```

### Display Issues

```bash
# Make sure X11 is running
export DISPLAY=:0

# Or start X11
startx
```

## Configuration

Edit `config.py` to customize:

- Backend API URL
- Cache directory and size limits
- Video/image settings
- Logging configuration
- SignalR settings

## Logs

```bash
# View application logs
tail -f ~/logs/marketing-display.log

# Or if running as service
sudo journalctl -u marketing-display -f
```
