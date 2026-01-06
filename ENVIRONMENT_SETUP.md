# Environment Setup Guide

## Quick Start

This application requires environment configuration files for different deployment environments.

### 1. Create Environment Files

Create the following files in the project root:

#### `.env.development` (for local development)
```bash
# Development Environment Configuration
ENVIRONMENT=development
IS_DEVELOPMENT=true

# Device Configuration
DEVICE_TYPE=11
DEVICE_NAME=Marketing Display Dev

# Backend API URLs (Local Development)
BASE_URL=http://localhost:5000
BASE_URL_POS=http://localhost:5002
BASE_URL_INVENTORY=http://localhost:5001
BASE_URL_SIGNALR=http://localhost:5001

# Polling & Timing
REGISTRATION_POLL_INTERVAL=10
HEARTBEAT_INTERVAL=30

# Logging
LOG_LEVEL=DEBUG
```

#### `.env.staging` (for staging environment)
```bash
# Staging Environment Configuration
ENVIRONMENT=staging
IS_DEVELOPMENT=false

# Device Configuration
DEVICE_TYPE=11
DEVICE_NAME=Marketing Display Staging

# Backend API URLs (Staging Environment)
# TODO: Update these URLs to your staging backend
BASE_URL=https://staging-api.example.com
BASE_URL_POS=https://staging-pos.example.com
BASE_URL_INVENTORY=https://staging-inventory.example.com
BASE_URL_SIGNALR=https://staging-inventory.example.com

# Polling & Timing
REGISTRATION_POLL_INTERVAL=10
HEARTBEAT_INTERVAL=30

# Logging
LOG_LEVEL=INFO
```

#### `.env.production` (for production deployment)
```bash
# Production Environment Configuration
ENVIRONMENT=production
IS_DEVELOPMENT=false

# Device Configuration
DEVICE_TYPE=11
DEVICE_NAME=Marketing Display

# Backend API URLs (Production Environment)
# TODO: Update these URLs to your production backend
BASE_URL=https://api.example.com
BASE_URL_POS=https://pos.example.com
BASE_URL_INVENTORY=https://inventory.example.com
BASE_URL_SIGNALR=https://inventory.example.com

# Polling & Timing
REGISTRATION_POLL_INTERVAL=10
HEARTBEAT_INTERVAL=30

# Logging
LOG_LEVEL=INFO
```

### 2. Create the Files

**On macOS/Linux:**
```bash
# Navigate to project directory
cd "/Users/nilay/Desktop/Unisight Dev/Marketing"

# Create development environment file
cat > .env.development << 'EOF'
ENVIRONMENT=development
IS_DEVELOPMENT=true
DEVICE_TYPE=11
DEVICE_NAME=Marketing Display Dev
BASE_URL=http://localhost:5000
BASE_URL_POS=http://localhost:5002
BASE_URL_INVENTORY=http://localhost:5001
BASE_URL_SIGNALR=http://localhost:5001
REGISTRATION_POLL_INTERVAL=10
HEARTBEAT_INTERVAL=30
LOG_LEVEL=DEBUG
EOF

# Create staging and production files similarly
cp .env.development .env.staging
cp .env.development .env.production

# Edit staging and production files with appropriate URLs
```

### 3. Update Backend URLs

Edit each `.env.*` file and update the `BASE_URL` variables to point to your actual backend services.

### 4. Verify Setup

Run the following to check if environment is loaded correctly:

```bash
ENVIRONMENT=development python3 -c "from config import Config; Config.print_config()"
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment mode (development/staging/production) | development | Yes |
| `IS_DEVELOPMENT` | Development mode flag | false | No |
| `DEVICE_TYPE` | Device type ID (11 = Marketing Display) | 11 | Yes |
| `DEVICE_NAME` | Display name for device | Marketing Display | Yes |
| `BASE_URL` | Main backend API URL | - | Yes |
| `BASE_URL_POS` | POS API URL | - | No |
| `BASE_URL_INVENTORY` | Inventory API URL | - | Yes |
| `BASE_URL_SIGNALR` | SignalR hub URL | Same as INVENTORY | No |
| `REGISTRATION_POLL_INTERVAL` | Seconds between registration checks | 10 | No |
| `HEARTBEAT_INTERVAL` | Seconds between heartbeat pings | 30 | No |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO | No |

## Notes

- **DO commit** `.env.development`, `.env.staging`, and `.env.production` to version control (they don't contain secrets)
- **DO NOT commit** `Config/registration.json` or `Config/branchInfo.json` (these contain API keys and device credentials)
- For local testing, you can override values by creating `.env.local` (which is gitignored)

