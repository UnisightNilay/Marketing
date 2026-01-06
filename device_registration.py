"""
Device Registration Manager
Handles QR code registration, polling, and device activation
"""
import os
import json
import logging
import asyncio
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import aiohttp
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

from config import Config

logger = logging.getLogger(__name__)


class RegistrationState:
    """Device registration state"""
    def __init__(self, data: Dict[str, Any] = None):
        data = data or {}
        self.assigned_guid = data.get('AssignedGuid', '')
        self.access_token = data.get('AccessToken', '')
        self.device_status = data.get('DeviceStatus', 'Pending')
        self.api_key = data.get('ApiKey', '')
        self.branch_id = data.get('BranchId')
        self.branch = data.get('Branch', '')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'AssignedGuid': self.assigned_guid,
            'AccessToken': self.access_token,
            'DeviceStatus': self.device_status,
            'ApiKey': self.api_key,
            'BranchId': self.branch_id,
            'Branch': self.branch
        }
    
    def is_activated(self) -> bool:
        """Check if device is fully activated"""
        return bool(self.api_key and self.api_key.strip())


class DeviceRegistrationManager:
    """Manages device registration process"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), 'Config')
        self.registration_file = os.path.join(self.config_dir, 'registration.json')
        self.branch_info_file = os.path.join(self.config_dir, 'branchInfo.json')
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.registration_state: Optional[RegistrationState] = None
        self.branch_info: Optional[Dict[str, Any]] = None
    
    async def load_registration(self) -> Optional[RegistrationState]:
        """Load existing registration from file"""
        try:
            if os.path.exists(self.registration_file):
                with open(self.registration_file, 'r') as f:
                    data = json.load(f)
                    self.registration_state = RegistrationState(data)
                    logger.info(f"Loaded registration: Status={self.registration_state.device_status}")
                    return self.registration_state
        except Exception as e:
            logger.error(f"Failed to load registration: {e}")
        return None
    
    async def save_registration(self, state: RegistrationState):
        """Save registration state to file"""
        try:
            with open(self.registration_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.info(f"Saved registration: Status={state.device_status}")
        except Exception as e:
            logger.error(f"Failed to save registration: {e}")
    
    async def save_branch_info(self, branch_data: Dict[str, Any]):
        """Save branch information to file"""
        try:
            with open(self.branch_info_file, 'w') as f:
                json.dump(branch_data, f, indent=2)
            self.branch_info = branch_data
            logger.info(f"Saved branch info: {branch_data.get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to save branch info: {e}")
    
    async def request_qr_registration(self) -> Dict[str, Any]:
        """Request QR code registration from backend"""
        device_type = int(os.getenv('DEVICE_TYPE', '11'))
        base_url = os.getenv('BASE_URL')
        
        if not base_url:
            raise ValueError("BASE_URL not configured in environment")
        
        endpoint = f"{base_url}/device-registration/qr-registration"
        
        headers = {
            'version': 'v1',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = {
            'DeviceType': device_type
        }
        
        logger.info(f"Requesting QR registration from {endpoint}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers=headers) as response:
                if response.status not in [200, 201]:
                    text = await response.text()
                    raise Exception(f"Registration failed: {response.status} - {text}")
                
                data = await response.json()
                logger.info(f"QR registration response: {data}")
                logger.info(f"QR registration successful: GUID={data.get('assignedGuid')}")
                return data
    
    async def check_device_status(self, guid: str, access_token: str) -> Dict[str, Any]:
        """Poll device status from backend"""
        base_url = os.getenv('BASE_URL')
        endpoint = f"{base_url}/device-registration/device-status/{guid}"
        
        headers = {
            'version': 'v1',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Status check failed: {response.status} - {text}")
                
                data = await response.json()
                return data
    
    async def fetch_branch_info(self, api_key: str) -> Dict[str, Any]:
        """Fetch branch information from inventory API"""
        base_url = os.getenv('BASE_URL_INVENTORY')
        endpoint = f"{base_url}/api/v1/branches/current"
        
        headers = {
            'version': 'v1',
            'Accept': 'application/json',
            'X-Api-Key': api_key
        }
        
        logger.info(f"Fetching branch info from {endpoint}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Branch fetch failed: {response.status} - {text}")
                
                data = await response.json()
                # Extract the 'success' object if present
                branch_data = data.get('success', data)
                return branch_data
    
    async def start_registration(self) -> RegistrationState:
        """Start the registration process"""
        # Request QR code
        qr_response = await self.request_qr_registration()
        
        logger.info(f"QR Response keys: {qr_response.keys()}")
        
        # Create initial registration state
        # Handle both camelCase and PascalCase response formats
        state = RegistrationState({
            'AssignedGuid': qr_response.get('assignedGuid') or qr_response.get('AssignedGuid'),
            'AccessToken': qr_response.get('accessToken') or qr_response.get('AccessToken'),
            'DeviceStatus': 'QR issued'
        })
        
        # Save initial state
        await self.save_registration(state)
        
        # Store QR code image for display (handle different response formats)
        state.qr_image = (qr_response.get('qrCodeImage') or 
                         qr_response.get('QrCodeImage') or
                         qr_response.get('qrCode'))
        state.qr_url = qr_response.get('url') or qr_response.get('Url')
        
        logger.info(f"QR Image present: {state.qr_image is not None}")
        logger.info(f"QR URL: {state.qr_url}")
        
        return state
    
    async def poll_until_activated(self, state: RegistrationState, 
                                   callback=None) -> RegistrationState:
        """Poll device status until activated"""
        poll_interval = int(os.getenv('REGISTRATION_POLL_INTERVAL', '10'))
        
        logger.info(f"Starting polling every {poll_interval} seconds")
        
        while not state.is_activated():
            await asyncio.sleep(poll_interval)
            
            try:
                # Check status
                status_data = await self.check_device_status(
                    state.assigned_guid, 
                    state.access_token
                )
                
                # Update state
                state.device_status = status_data.get('deviceStatus', 'Unknown')
                state.api_key = status_data.get('apiKey', '')
                state.branch_id = status_data.get('branchId')
                state.branch = status_data.get('branch', '')
                
                # Save updated state
                await self.save_registration(state)
                
                logger.info(f"Device status: {state.device_status}")
                
                # Notify callback
                if callback:
                    callback(state)
                
                # Check if activated
                if state.is_activated():
                    logger.info("✅ Device activated!")
                    
                    # Fetch branch info
                    branch_data = await self.fetch_branch_info(state.api_key)
                    await self.save_branch_info(branch_data)
                    
                    return state
                    
            except Exception as e:
                logger.error(f"Polling error: {e}")
                # Continue polling on error
        
        return state
    
    def is_registered(self) -> bool:
        """Check if device is already registered"""
        if self.registration_state and self.registration_state.is_activated():
            return True
        return False


class RegistrationUI(QWidget):
    """UI for displaying QR code during registration"""
    
    registration_complete = pyqtSignal(RegistrationState)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = DeviceRegistrationManager()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel("Device Registration")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #333; margin: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Status message
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 18px; color: #666; margin: 10px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # QR code image
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(400, 400)
        layout.addWidget(self.qr_label)
        
        # Activation code (last 8 digits of URL)
        self.activation_code_label = QLabel()
        self.activation_code_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin: 10px; font-family: monospace;")
        self.activation_code_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.activation_code_label)
        
        # Instructions
        instructions = QLabel("Scan the QR code with your mobile app\nto register and activate this device")
        instructions.setStyleSheet("font-size: 16px; color: #888; margin: 20px;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Set the layout to the widget
        self.setLayout(layout)
    
    def show_qr_code(self, qr_base64: str):
        """Display QR code from base64 string"""
        try:
            if not qr_base64:
                logger.error("No QR code image data provided")
                self.status_label.setText("❌ No QR code received from server")
                return
            
            # Remove data:image/png;base64, prefix if present
            if ',' in qr_base64:
                qr_base64 = qr_base64.split(',', 1)[1]
            
            # Decode base64
            qr_data = base64.b64decode(qr_base64)
            
            # Create pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(qr_data)
            
            if pixmap.isNull():
                logger.error("Failed to create pixmap from QR data")
                self.status_label.setText("❌ Invalid QR code image data")
                return
            
            # Scale to fit
            scaled = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(scaled)
            logger.info("✓ QR code displayed successfully")
            
        except Exception as e:
            logger.error(f"Failed to display QR code: {e}")
            self.status_label.setText(f"❌ Error displaying QR code: {e}")
    
    def update_status(self, state: RegistrationState):
        """Update status message"""
        status_messages = {
            'QR issued': '📱 Scan the QR code to register',
            'Pending': '⏳ Waiting for registration...',
            'Claimed': '✓ Device claimed! Waiting for activation...',
            'Activated': '🎉 Device activated successfully!'
        }
        
        message = status_messages.get(state.device_status, f"Status: {state.device_status}")
        
        if state.branch:
            message += f"\n\n📍 Branch: {state.branch}"
        
        self.status_label.setText(message)
    
    async def start_registration_process(self):
        """Start the full registration flow"""
        try:
            # Check if already registered
            existing = await self.manager.load_registration()
            if existing and existing.is_activated():
                logger.info("Device already registered")
                self.registration_complete.emit(existing)
                return
            
            # Start new registration
            self.status_label.setText("🔄 Requesting QR code...")
            state = await self.manager.start_registration()
            
            # Display QR code
            self.show_qr_code(state.qr_image)
            
            # Extract and display last 8 characters from URL
            if state.qr_url:
                activation_code = state.qr_url.split('/')[-1]  # Get last part of URL
                self.activation_code_label.setText(f"Code: {activation_code}")
            
            self.update_status(state)
            
            # Start polling in background
            asyncio.create_task(self._poll_for_activation(state))
            
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            self.status_label.setText(f"❌ Registration failed: {e}")
    
    async def _poll_for_activation(self, state: RegistrationState):
        """Background polling task"""
        try:
            activated_state = await self.manager.poll_until_activated(
                state, 
                callback=self.update_status
            )
            
            # Show success
            self.update_status(activated_state)
            
            # Emit completion signal
            QTimer.singleShot(2000, lambda: self.registration_complete.emit(activated_state))
            
        except Exception as e:
            logger.error(f"Polling failed: {e}")
            self.status_label.setText(f"❌ Activation failed: {e}")
