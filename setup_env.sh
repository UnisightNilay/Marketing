#!/bin/bash
# Setup environment configuration files for Marketing Display Application

echo "========================================"
echo "Marketing Display - Environment Setup"
echo "========================================"
echo ""

# Check if .env.development already exists
if [ -f ".env.development" ]; then
    read -p ".env.development already exists. Overwrite? (y/N): " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo "Skipping .env.development"
    else
        rm .env.development
    fi
fi

# Create .env.development
if [ ! -f ".env.development" ]; then
    echo "Creating .env.development..."
    cat > .env.development << 'EOF'
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
EOF
    echo "✓ Created .env.development"
fi

# Create .env.staging
if [ ! -f ".env.staging" ]; then
    echo "Creating .env.staging..."
    cat > .env.staging << 'EOF'
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
EOF
    echo "✓ Created .env.staging"
fi

# Create .env.production
if [ ! -f ".env.production" ]; then
    echo "Creating .env.production..."
    cat > .env.production << 'EOF'
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
EOF
    echo "✓ Created .env.production"
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Update .env.staging with your staging backend URLs"
echo "2. Update .env.production with your production backend URLs"
echo "3. Run the application: ./run.sh"
echo ""

