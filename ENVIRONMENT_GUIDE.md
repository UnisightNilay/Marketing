# Marketing Display Application - Environment Configuration

## Overview
The application supports three environments:
- **Development**: Local development with mock data
- **Staging**: Testing environment
- **Production**: Live deployment

## Configuration Files
- `.env.development` - Development settings
- `.env.staging` - Staging settings  
- `.env.production` - Production settings

## Running the Application

### Interactive Mode
```bash
./run.sh
```
Select environment from menu (1=dev, 2=staging, 3=production)

### Direct Mode
```bash
# Development
ENVIRONMENT=development python3 app.py

# Staging  
ENVIRONMENT=staging python3 app.py

# Production
ENVIRONMENT=production python3 app.py
```

## Environment Variables

### Backend URLs
- `BASE_URL` - Main API endpoint
- `BASE_URL_INVENTORY` - Inventory API endpoint
- `BASE_URL_SIGNALR` - SignalR/WebSocket hub URL

### Device Configuration
- `DEVICE_TYPE` - Device type ID (11 = Marketing Display)
- `DEVICE_NAME` - Display name for this device

### Polling & Timing
- `REGISTRATION_POLL_INTERVAL` - Seconds between registration status checks (default: 10)
- `HEARTBEAT_INTERVAL` - Seconds between heartbeat pings (default: 30)

### Logging
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR, CRITICAL

## Device Registration Flow

1. **App Starts** → Loads environment config
2. **Check Registration** → Looks for `/Config/registration.json`
3. **If Not Registered**:
   - Request QR code from backend
   - Display QR on screen
   - Poll every 10s for activation
   - Save credentials when activated
4. **Check Internet** → WiFi setup if needed
5. **Start Media Player** → Load playlist and begin playback

## File Structure
```
/home/unisight/Documents/Marketing/
├── .env.development          # Dev environment config
├── .env.staging              # Staging environment config
├── .env.production           # Production environment config
├── Config/
│   ├── registration.json     # Device credentials (auto-created)
│   └── branchInfo.json       # Branch details (auto-created)
├── app.py                    # Main application
├── device_registration.py    # Registration manager
└── run.sh                    # Environment selector script
```

## Deployment to Raspberry Pi

1. **Copy .env files** to Pi:
```bash
scp .env.* pi@raspberrypi:~/marketing-display/
```

2. **Set environment on Pi** (edit ~/.bashrc):
```bash
export ENVIRONMENT=production
```

3. **Run on boot** (systemd service will use ENVIRONMENT variable)

## Testing Registration

### Development Mode
Update `.env.development` with your local backend URL:
```
BASE_URL=http://localhost:5000
```

### Staging Mode
Update `.env.staging` with staging URLs:
```
BASE_URL=https://staging-api.example.com
```

## Troubleshooting

### Check Current Environment
```bash
echo $ENVIRONMENT
```

### View Logs
```bash
tail -f ~/logs/marketing-display.log
```

### Reset Registration
```bash
rm ~/Documents/Marketing/Config/registration.json
rm ~/Documents/Marketing/Config/branchInfo.json
```

### Test API Connection
```bash
curl -H "version: v1" http://your-backend-url/device-registration/qr-registration
```
