#!/bin/bash
# Installation script for Raspberry Pi

echo "=========================================="
echo "Marketing Display - Raspberry Pi Setup"
echo "=========================================="

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo ""
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo ""
echo "Step 2: Installing system dependencies..."
sudo apt install -y \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    unclutter \
    network-manager \
    python3-pyqt5 \
    python3-pyqt5.qtmultimedia \
    python3-requests \
    python3-pil \
    python3-aiohttp \
    vlc \
    libvlc-dev \
    python3-vlc \
    python3-pip \
    python3-venv

# Create Python virtual environment with system packages
echo ""
echo "Step 3: Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv --system-site-packages .venv
    echo "Virtual environment created with system site packages"
fi

# Activate virtual environment and install packages
echo ""
echo "Step 4: Installing Python packages in virtual environment..."
source .venv/bin/activate
pip install --upgrade pip
pip install signalrcore websocket-client python-dotenv aiohttp Pillow

# Create necessary directories
echo ""
echo "Step 5: Creating directories..."
mkdir -p ~/media-cache
mkdir -p ~/logs

echo ""
echo "Configuration will be loaded from .env files"
echo "No manual API URL entry needed"

# Enable NetworkManager
echo ""
echo "Step 6: Enabling NetworkManager..."
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager

# Disable screen blanking in X11
echo ""
echo "Step 7: Disabling screen blanking and power saving..."
mkdir -p ~/.config

# Disable screen blanking via raspi-config
sudo raspi-config nonint do_blanking 1

# Add xset commands to disable power management
if ! grep -q "xset s off" ~/.bash_profile 2>/dev/null; then
    echo "xset s off" >> ~/.bash_profile
    echo "xset -dpms" >> ~/.bash_profile
    echo "xset s noblank" >> ~/.bash_profile
    echo "Screen blanking disabled in bash profile"
fi

# Create xinitrc with screen blanking disabled
cat > ~/.xinitrc <<'XINITRC'
#!/bin/bash
xset -dpms      # Disable DPMS (Energy Star) features
xset s off      # Disable screen saver
xset s noblank  # Don't blank the video device

# Start the marketing display app
cd ~/Marketing
python3 app.py
XINITRC
chmod +x ~/.xinitrc

# Update boot config to prevent HDMI blanking
if ! grep -q "hdmi_blanking" /boot/firmware/config.txt 2>/dev/null; then
    echo "# Disable HDMI blanking" | sudo tee -a /boot/firmware/config.txt
    echo "hdmi_blanking=1" | sudo tee -a /boot/firmware/config.txt
    echo "HDMI blanking disabled in boot config"
fi

# Configure X server to allow systemd services to start X
echo ""
echo "Step 8: Configuring X server permissions..."
if [ ! -f /etc/X11/Xwrapper.config ]; then
    echo "allowed_users=anybody" | sudo tee /etc/X11/Xwrapper.config
else
    if ! grep -q "allowed_users=anybody" /etc/X11/Xwrapper.config; then
        sudo sed -i 's/allowed_users=.*/allowed_users=anybody/' /etc/X11/Xwrapper.config
        if ! grep -q "allowed_users" /etc/X11/Xwrapper.config; then
            echo "allowed_users=anybody" | sudo tee -a /etc/X11/Xwrapper.config
        fi
    fi
fi
echo "X server permissions configured"

# Configure X server for Raspberry Pi GPU
echo ""
echo "Step 9: Configuring X server for Raspberry Pi..."
sudo mkdir -p /etc/X11/xorg.conf.d
sudo tee /etc/X11/xorg.conf.d/99-vc4.conf > /dev/null <<'XORGCONF'
Section "Device"
    Identifier "vc4"
    Driver "modesetting"
    Option "kmsdev" "/dev/dri/card1"
EndSection
XORGCONF
echo "X server GPU configuration created"

# Setup systemd service (optional)
echo ""
read -p "Install as system service (auto-start on boot)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating systemd service..."
    
    # Get the real user (not root when using sudo)
    if [ -n "$SUDO_USER" ]; then
        ACTUAL_USER="$SUDO_USER"
        ACTUAL_HOME=$(eval echo ~$SUDO_USER)
    else
        ACTUAL_USER=$(whoami)
        ACTUAL_HOME="$HOME"
    fi
    
    echo "Creating service for user: $ACTUAL_USER"
    echo "Home directory: $ACTUAL_HOME"
    
    SERVICE_FILE="/etc/systemd/system/marketing-display.service"
    
    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Marketing Display
After=multi-user.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$ACTUAL_HOME/Marketing
Environment=DISPLAY=:0
Environment=QT_QPA_PLATFORM=xcb
Environment=QT_X11_NO_MITSHM=1
# NOTE: For production, change test_media_player.py to app.py
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/xinit $ACTUAL_HOME/Marketing/.venv/bin/python $ACTUAL_HOME/Marketing/test_media_player.py -- :0 vt7
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable marketing-display.service
    
    echo ""
    echo "✓ Service installed successfully"
    echo ""
    echo "IMPORTANT: Currently configured for TEST MODE"
    echo "  Running: test_media_player.py via xinit"
    echo ""
    echo "For PRODUCTION deployment, edit the service file:"
    echo "  sudo nano /etc/systemd/system/marketing-display.service"
    echo ""
    echo "Change the ExecStart line to run app.py instead:"
    echo "  ExecStart=/usr/bin/xinit $ACTUAL_HOME/Marketing/.venv/bin/python $ACTUAL_HOME/Marketing/app.py -- :0 vt7"
    echo ""
    echo "Then run:"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl restart marketing-display"
    echo ""
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
if sudo systemctl is-enabled marketing-display &>/dev/null; then
    echo "✓ Service installed - will start automatically on boot"
    echo ""
    echo "REBOOT NOW to start the service:"
    echo "  sudo reboot"
    echo ""
    echo "After reboot, the test media player will start automatically on the monitor."
    echo ""
    echo "To manage the service:"
    echo "  sudo systemctl status marketing-display"
    echo "  sudo systemctl stop marketing-display"
    echo "  sudo journalctl -u marketing-display -f"
else
    echo "To run manually:"
    echo "  cd ~/Marketing"
    echo "  source .venv/bin/activate"
    echo "  xinit python test_media_player.py -- :0 vt7"
fi
echo ""
echo "=========================================="
echo "REBOOT recommended to start the service"
echo "  sudo reboot"
echo "=========================================="
echo ""
