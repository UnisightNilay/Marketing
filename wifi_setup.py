"""
WiFi Setup UI for Marketing Display Application
Displays when no internet connection is available
"""
import sys
import os
import subprocess
import logging
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLineEdit, QPushButton, QLabel, 
    QMessageBox, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap

from config import Config
from utils import check_internet_connection

logger = logging.getLogger(__name__)


class WiFiSetupUI(QWidget):
    """WiFi configuration UI"""
    
    def __init__(self, on_success_callback=None):
        super().__init__()
        self.on_success_callback = on_success_callback
        self.selected_ssid = None
        self.init_ui()
        self.scan_networks()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('WiFi Setup - Marketing Display')
        self.setStyleSheet('background-color: #f5f5f5;')
        
        # Main layout - full screen
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Center container - mobile style
        center_container = QFrame()
        center_container.setStyleSheet(
            'background-color: white; '
            'border-radius: 20px; '
            'border: 1px solid #e0e0e0;'
        )
        center_container.setMaximumWidth(500)
        center_container.setMinimumWidth(400)
        
        # Container layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo at the top
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'Assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            scaled_logo = logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
        else:
            # Fallback if logo not found
            logo_label.setText('📶')
            logo_label.setStyleSheet('font-size: 64px;')
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Title
        title = QLabel('WiFi Network Setup')
        title.setStyleSheet(
            'font-size: 24px; font-weight: bold; '
            'color: #2c3e50; padding: 10px 0;'
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instruction label
        instruction = QLabel('Select a network and enter the password')
        instruction.setStyleSheet('font-size: 14px; color: #7f8c8d; padding-bottom: 10px;')
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        
        # Network list
        list_label = QLabel('Available Networks:')
        list_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #2c3e50; padding-top: 10px;')
        layout.addWidget(list_label)
        
        self.network_list = QListWidget()
        self.network_list.setStyleSheet(
            'font-size: 16px; padding: 8px; border: 1px solid #e0e0e0; '
            'border-radius: 8px; background-color: #fafafa;'
        )
        self.network_list.setMaximumHeight(250)
        self.network_list.setMinimumHeight(200)
        self.network_list.itemClicked.connect(self.on_network_selected)
        layout.addWidget(self.network_list)
        
        # Refresh button
        self.refresh_btn = QPushButton('🔄 Refresh Networks')
        self.refresh_btn.setStyleSheet(
            'font-size: 16px; padding: 10px; background-color: #3498db; '
            'color: white; border: none; border-radius: 8px; font-weight: bold;'
        )
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.scan_networks)
        layout.addWidget(self.refresh_btn)
        
        # Password section
        password_label = QLabel('Password:')
        password_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #2c3e50; padding-top: 10px;')
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(
            'font-size: 16px; padding: 10px; border: 1px solid #e0e0e0; '
            'border-radius: 8px; background-color: white;'
        )
        self.password_input.setPlaceholderText('Enter WiFi password')
        layout.addWidget(self.password_input)
        
        # Show/Hide password toggle
        self.show_password_btn = QPushButton('👁 Show Password')
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.setStyleSheet(
            'font-size: 14px; padding: 8px; background-color: #95a5a6; '
            'color: white; border: none; border-radius: 6px;'
        )
        self.show_password_btn.setCursor(Qt.PointingHandCursor)
        self.show_password_btn.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password_btn)
        
        # Connect button
        self.connect_btn = QPushButton('✓ Connect to Network')
        self.connect_btn.setStyleSheet(
            'font-size: 18px; padding: 12px; background-color: #27ae60; '
            'color: white; border: none; border-radius: 8px; font-weight: bold;'
        )
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.connect_to_wifi)
        self.connect_btn.setEnabled(False)
        layout.addWidget(self.connect_btn)
        
        # Status label
        self.status_label = QLabel('')
        self.status_label.setStyleSheet(
            'font-size: 14px; padding: 12px; color: #7f8c8d; '
            'background-color: #f8f9fa; border-radius: 8px;'
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Add stretch at bottom to push content up
        layout.addStretch()
        
        # Set layout to container
        center_container.setLayout(layout)
        
        # Add container to main layout (centered)
        main_layout.addStretch()
        main_layout.addWidget(center_container, 0, Qt.AlignCenter)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def scan_networks(self):
        """Scan for available WiFi networks"""
        logger.info("Scanning for WiFi networks...")
        self.status_label.setText('🔍 Scanning for networks...')
        self.status_label.setStyleSheet(
            'font-size: 18px; padding: 15px; color: #2c3e50; '
            'background-color: #3498db; border-radius: 8px;'
        )
        self.network_list.clear()
        self.refresh_btn.setEnabled(False)
        
        try:
            # Use nmcli to scan for WiFi networks
            result = subprocess.run(
                ['nmcli', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                networks = self.parse_networks(result.stdout)
                
                if networks:
                    for network in networks:
                        ssid = network['ssid']
                        signal = network['signal']
                        security = network['security']
                        
                        # Format display
                        lock_icon = '🔒' if security != '--' else '🔓'
                        signal_bars = self.get_signal_bars(int(signal))
                        display_text = f"{signal_bars} {ssid}  ({signal}%)  {lock_icon}"
                        
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, ssid)  # Store actual SSID
                        self.network_list.addItem(item)
                    
                    self.status_label.setText(f'✓ Found {len(networks)} network(s)')
                    self.status_label.setStyleSheet(
                        'font-size: 14px; padding: 12px; color: white; '
                        'background-color: #27ae60; border-radius: 8px;'
                    )
                    logger.info(f"Found {len(networks)} WiFi networks")
                else:
                    self.status_label.setText('⚠ No networks found. Click Refresh to try again.')
                    self.status_label.setStyleSheet(
                        'font-size: 14px; padding: 12px; color: white; '
                        'background-color: #e67e22; border-radius: 8px;'
                    )
                    logger.warning("No WiFi networks found")
            else:
                self.status_label.setText('❌ Error scanning networks. Make sure WiFi is enabled.')
                self.status_label.setStyleSheet(
                    'font-size: 14px; padding: 12px; color: white; '
                    'background-color: #e74c3c; border-radius: 8px;'
                )
                logger.error(f"Network scan failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            self.status_label.setText('❌ Network scan timed out. Click Refresh to try again.')
            self.status_label.setStyleSheet(
                'font-size: 14px; padding: 12px; color: white; '
                'background-color: #e74c3c; border-radius: 8px;'
            )
            logger.error("Network scan timed out")
        except FileNotFoundError:
            # nmcli not available - development mode
            self.load_mock_networks()
        except Exception as e:
            self.status_label.setText(f'❌ Scan error: {str(e)}')
            self.status_label.setStyleSheet(
                'font-size: 14px; padding: 12px; color: white; '
                'background-color: #e74c3c; border-radius: 8px;'
            )
            logger.error(f"Network scan error: {e}")
        
        self.refresh_btn.setEnabled(True)
    
    def parse_networks(self, output: str) -> list:
        """Parse nmcli output to extract network information"""
        networks = []
        lines = output.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                ssid = parts[0]
                if ssid and ssid != '--' and ssid != '':
                    signal = parts[1] if len(parts) > 1 else '0'
                    security = ' '.join(parts[2:]) if len(parts) > 2 else '--'
                    
                    try:
                        signal_int = int(signal)
                        networks.append({
                            'ssid': ssid,
                            'signal': signal,
                            'security': security
                        })
                    except ValueError:
                        pass
        
        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: int(x['signal']), reverse=True)
        return networks
    
    def load_mock_networks(self):
        """Load mock networks for development/testing"""
        logger.info("Loading mock WiFi networks (development mode)")
        mock_networks = [
            {'ssid': 'Office-WiFi-5G', 'signal': '85', 'security': 'WPA2'},
            {'ssid': 'Guest-Network', 'signal': '72', 'security': 'WPA2'},
            {'ssid': 'Store-Display', 'signal': '68', 'security': 'WPA2'},
            {'ssid': 'Public-WiFi', 'signal': '45', 'security': '--'},
        ]
        
        for network in mock_networks:
            ssid = network['ssid']
            signal = network['signal']
            security = network['security']
            
            lock_icon = '🔒' if security != '--' else '🔓'
            signal_bars = self.get_signal_bars(int(signal))
            display_text = f"{signal_bars} {ssid}  ({signal}%)  {lock_icon}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, ssid)
            self.network_list.addItem(item)
        self.status_label.setText('✓ Found 4 network(s) [MOCK DATA - Development Mode]')
        self.status_label.setStyleSheet(
            'font-size: 14px; padding: 12px; color: white; '
            'background-color: #f39c12; border-radius: 8px;'
        )
    
    def get_signal_bars(self, signal_strength: int) -> str:
        """Convert signal strength to visual bars"""
        if signal_strength >= 75:
            return '📶'
        elif signal_strength >= 50:
            return '📶'
        elif signal_strength >= 25:
            return '📶'
        else:
            return '📶'
    
    def on_network_selected(self, item):
        """Handle network selection from list"""
        self.selected_ssid = item.data(Qt.UserRole)
        self.connect_btn.setEnabled(True)
        self.status_label.setText(f'Selected: {self.selected_ssid}')
        self.status_label.setStyleSheet(
            'font-size: 14px; padding: 12px; color: #2c3e50; '
            'background-color: #f8f9fa; border-radius: 8px;'
        )
        logger.info(f"Network selected: {self.selected_ssid}")
    
    def toggle_password_visibility(self, checked):
        """Toggle password field visibility"""
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText('🙈 Hide Password')
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText('👁 Show Password')
    
    def connect_to_wifi(self):
        """Attempt to connect to selected WiFi network"""
        if not self.selected_ssid:
            QMessageBox.warning(self, 'Error', 'Please select a network first')
            return
        
        password = self.password_input.text().strip()
        
        # Confirm connection to open network
        if not password:
            reply = QMessageBox.question(
                self, 'Confirm Connection',
                f'Connect to "{self.selected_ssid}" without password (open network)?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        logger.info(f"Attempting to connect to: {self.selected_ssid}")
        self.status_label.setText(f'🔄 Connecting to {self.selected_ssid}...')
        self.status_label.setStyleSheet(
            'font-size: 14px; padding: 12px; color: white; '
            'background-color: #3498db; border-radius: 8px;'
        )
        self.connect_btn.setEnabled(False)
        QApplication.processEvents()  # Update UI
        
        try:
            # Connect using nmcli
            if password:
                cmd = [
                    'nmcli', 'device', 'wifi', 'connect',
                    self.selected_ssid, 'password', password
                ]
            else:
                cmd = ['nmcli', 'device', 'wifi', 'connect', self.selected_ssid]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to {self.selected_ssid}")
                self.status_label.setText(f'✅ Connected to {self.selected_ssid}!')
                self.status_label.setStyleSheet(
                    'font-size: 14px; padding: 12px; color: white; '
                    'background-color: #27ae60; border-radius: 8px; font-weight: bold;'
                )
                
                # Wait 2 seconds then close
                QTimer.singleShot(2000, self.on_connection_success)
            else:
                error_msg = result.stderr.strip() if result.stderr else 'Connection failed'
                logger.error(f"WiFi connection failed: {error_msg}")
                self.status_label.setText(f'❌ Connection failed: {error_msg}')
                self.status_label.setStyleSheet(
                    'font-size: 14px; padding: 12px; color: white; '
                    'background-color: #e74c3c; border-radius: 8px;'
                )
                self.connect_btn.setEnabled(True)
                
        except subprocess.TimeoutExpired:
            logger.error("WiFi connection timed out")
            self.status_label.setText('❌ Connection timed out. Please try again.')
            self.status_label.setStyleSheet(
                'font-size: 14px; padding: 12px; color: white; '
                'background-color: #e74c3c; border-radius: 8px;'
            )
            self.connect_btn.setEnabled(True)
        except FileNotFoundError:
            # Development mode - simulate success
            logger.info("Development mode - simulating WiFi connection")
            self.status_label.setText('✅ Connected! [SIMULATED - Development Mode]')
            self.status_label.setStyleSheet(
                'font-size: 14px; padding: 12px; color: white; '
                'background-color: #f39c12; border-radius: 8px; font-weight: bold;'
            )
            QTimer.singleShot(2000, self.on_connection_success)
        except Exception as e:
            logger.error(f"WiFi connection error: {e}")
            self.status_label.setText(f'❌ Error: {str(e)}')
            self.status_label.setStyleSheet(
                'font-size: 14px; padding: 12px; color: white; '
                'background-color: #e74c3c; border-radius: 8px;'
            )
            self.connect_btn.setEnabled(True)
    
    def on_connection_success(self):
        """Called when WiFi connection is successful"""
        logger.info("WiFi setup completed successfully")
        if self.on_success_callback:
            self.on_success_callback()
        self.close()


if __name__ == '__main__':
    # Test WiFi setup UI
    from utils import setup_logging
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    app = QApplication(sys.argv)
    wifi_ui = WiFiSetupUI()
    
    # Always show fullscreen (kiosk mode)
    wifi_ui.showFullScreen()
    
    sys.exit(app.exec_())
