#!/bin/bash
# Deployment script - sync files from development machine to Raspberry Pi

# Configuration
PI_HOST="${PI_HOST:-10.0.120.163}"
PI_USER="${PI_USER:-unisight}"
PROJECT_DIR="Marketing"
EXCLUDE_DIRS="--exclude=.git --exclude=__pycache__ --exclude=*.pyc --exclude=media-cache --exclude=logs --exclude=.venv"

echo "=========================================="
echo "Deploying to Raspberry Pi"
echo "=========================================="
echo "Host: $PI_USER@$PI_HOST"
echo "Project: $PROJECT_DIR"
echo ""

# Check if Pi is reachable
if ! ping -c 1 -W 2 "$PI_HOST" > /dev/null 2>&1; then
    echo "Error: Cannot reach $PI_HOST"
    echo "Make sure the Raspberry Pi is powered on and connected to the network"
    exit 1
fi

# Sync files
echo "Syncing files..."
rsync -avz --progress $EXCLUDE_DIRS \
    ./ ${PI_USER}@${PI_HOST}:~/${PROJECT_DIR}/

if [ $? -eq 0 ]; then
    echo ""
    echo "Files synced successfully!"
    echo ""
    
    # Ask if should restart service
    read -p "Restart marketing-display service? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Restarting service..."
        ssh ${PI_USER}@${PI_HOST} "sudo systemctl restart marketing-display"
        echo "Service restarted"
        echo ""
        echo "Check status with:"
        echo "  ssh ${PI_USER}@${PI_HOST} 'sudo systemctl status marketing-display'"
    fi
    
    echo ""
    echo "Deployment complete!"
else
    echo ""
    echo "Error: Deployment failed"
    exit 1
fi
