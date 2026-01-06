"""
Main Application Entry Point for Marketing Display
Integrates device registration, WiFi setup, media player, SignalR, and content management
"""
import sys
import os
import asyncio
import logging
from PyQt5.QtWidgets import QApplication, QStackedWidget
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt

from config import Config, load_environment
from utils import check_internet_connection, setup_logging
from wifi_setup import WiFiSetupUI
from media_player_vlc import MediaPlayerApp
from playlist_manager import PlaylistManager
from media_downloader import MediaDownloader
from signalr_client import SignalRClient
from device_registration import DeviceRegistrationManager, RegistrationUI, RegistrationState

logger = logging.getLogger(__name__)


class ContentUpdateThread(QThread):
    """Thread for handling playlist updates and downloads"""
    
    playlist_ready = pyqtSignal(list)  # Emits playlist when ready
    
    def __init__(self, action='refresh', message=None):
        super().__init__()
        self.action = action
        self.message = message
    
    def run(self):
        """Run content update in background thread"""
        try:
            logger.info(f"Processing content update: {self.action}")
            
            # Fetch latest playlist
            playlist_manager = PlaylistManager()
            items = playlist_manager.fetch_playlist()
            
            if items:
                # Download media files
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def download_all():
                    async with MediaDownloader() as downloader:
                        return await downloader.download_playlist(items)
                
                downloaded_items = loop.run_until_complete(download_all())
                loop.close()
                
                if downloaded_items:
                    self.playlist_ready.emit(downloaded_items)
                    logger.info(f"Content update completed: {len(downloaded_items)} items ready")
                else:
                    logger.warning("No items downloaded")
            else:
                logger.error("Failed to fetch playlist")
                
        except Exception as e:
            logger.error(f"Error in content update thread: {e}")


class MarketingDisplayApp:
    """Main application controller"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        # Main window stack (registration -> wifi -> media player)
        self.main_window = QStackedWidget()
        self.main_window.setWindowTitle(f"{Config.DEVICE_NAME} - {Config.ENVIRONMENT}")
        
        # Windows
        self.registration_window = None
        self.wifi_window = None
        self.player_window = None
        
        # Managers
        self.registration_manager = DeviceRegistrationManager()
        self.signalr_client = None
        self.playlist_manager = PlaylistManager()
        self.update_thread = None
        
        # Timer for periodic internet checks
        self.internet_check_timer = QTimer()
        self.internet_check_timer.timeout.connect(self.check_connectivity)
        
        # Hide cursor globally
        self.app.setOverrideCursor(QCursor(Qt.BlankCursor))
        
        logger.info(f"Starting {Config.DEVICE_NAME} in {Config.ENVIRONMENT} mode")
    
    async def check_registration(self):
        """Check if device is registered, start registration if needed"""
        # Try to load existing registration
        existing = await self.registration_manager.load_registration()
        
        if existing and existing.is_activated():
            logger.info(f"✅ Device already registered: {existing.branch}")
            return existing
        else:
            logger.info("❌ Device not registered, starting registration process")
            return None
    
    def start(self):
        """Start the application"""
        logger.info("Application starting...")
        
        # Run async initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        registration_state = loop.run_until_complete(self.check_registration())
        
        if not registration_state:
            # Need to register device
            self.show_registration()
        elif not check_internet_connection():
            # Registered but no internet - show WiFi setup
            logger.warning("No internet connection - showing WiFi setup")
            self.show_wifi_setup()
        else:
            # Registered and has internet - start main app
            logger.info("Device registered and connected - starting main app")
            self.start_main_app(registration_state)
        
        # Start application event loop
        return self.app.exec_()
    
    def show_registration(self):
        """Show device registration UI"""
        logger.info("Showing device registration screen")
        
        self.registration_window = RegistrationUI()
        self.registration_window.registration_complete.connect(self.on_registration_complete)
        
        # Show window first (fullscreen kiosk mode)
        self.registration_window.showFullScreen()
        
        # Start registration process after window is shown
        QTimer.singleShot(100, self._start_registration_async)
    
    def _start_registration_async(self):
        """Start registration process asynchronously"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.registration_window.start_registration_process())
    
    def on_registration_complete(self, state: RegistrationState):
        """Called when device registration is complete"""
        logger.info(f"🎉 Registration complete! Branch: {state.branch}")
        
        # Close registration window
        if self.registration_window:
            self.registration_window.close()
            self.registration_window = None
        
        # Check internet and proceed
        if check_internet_connection():
            self.start_main_app(state)
        else:
            self.show_wifi_setup()
    
    def show_wifi_setup(self):
        """Show WiFi configuration UI"""
        self.wifi_window = WiFiSetupUI(on_success_callback=self.on_wifi_connected)
        
        # Always show fullscreen (kiosk mode)
        self.wifi_window.showFullScreen()
    
    def on_wifi_connected(self):
        """Called when WiFi connection is successful"""
        logger.info("WiFi connected, starting main application")
        
        # Close WiFi window
        if self.wifi_window:
            self.wifi_window.close()
            self.wifi_window = None
        
        # Start main app
        QTimer.singleShot(1000, self.start_main_app)
    
    def start_main_app(self, registration_state: RegistrationState = None):
        """Start main media display application"""
        logger.info("Starting main application")
        
        # Create media player window
        self.player_window = MediaPlayerApp()
        
        # Always show fullscreen (kiosk mode)
        self.player_window.showFullScreen()
        
        # Load initial content
        logger.info("Main application window displayed")
        
        # TODO: Uncomment when backend is ready
        # if registration_state:
        #     self.load_content(registration_state.api_key)
        #     self.start_signalr(registration_state.api_key)
        
    def load_content(self, api_key: str):
        """Load initial content from backend"""
        logger.info("Loading initial content")
        
        # Try to load cached playlist first
        cache_file = os.path.join(Config.CACHE_DIR, 'playlist_cache.json')
        
        if os.path.exists(cache_file):
            if self.playlist_manager.load_playlist_cache(cache_file):
                logger.info("Loaded cached playlist")
                
                # Use cached items that are already downloaded
                cached_items = []
                for item in self.playlist_manager.get_current_playlist():
                    if item.get('path') and os.path.exists(item['path']):
                        cached_items.append(item)
                
                if cached_items and self.player_window:
                    self.player_window.set_playlist(cached_items)
                    logger.info(f"Playing {len(cached_items)} cached items")
        
        # Fetch fresh content in background
        # TODO: Uncomment when backend is ready
        # self.refresh_content()ndow.set_playlist(cached_items)
        
        # Fetch fresh content in background
        self.refresh_content()
    
    def refresh_content(self, action='refresh', message=None):
        """Refresh content from backend"""
        logger.info("Refreshing content from backend")
        
        # Start update thread
        self.update_thread = ContentUpdateThread(action, message)
        self.update_thread.playlist_ready.connect(self.on_playlist_ready)
        self.update_thread.start()
    
    def on_playlist_ready(self, playlist):
        """Called when playlist is downloaded and ready"""
        logger.info(f"Playlist ready with {len(playlist)} items")
        
        # Update player
        if self.player_window:
            self.player_window.set_playlist(playlist)
        
        # Save to cache
        cache_file = os.path.join(Config.CACHE_DIR, 'playlist_cache.json')
        self.playlist_manager.save_playlist_cache(cache_file)
    
    def start_signalr(self):
        """Start SignalR client for real-time updates"""
        try:
            self.signalr_client = SignalRClient(on_playlist_updated=self.on_signalr_update)
            self.signalr_client.start()
            logger.info("SignalR client started")
        except Exception as e:
            logger.error(f"Failed to start SignalR client: {e}")
            logger.info("Will continue without real-time updates")
    
    def on_signalr_update(self, action, message):
        """Handle SignalR playlist update messages"""
        logger.info(f"SignalR update received: {action}")
        
        if action == 'refresh':
            self.refresh_content(action, message)
        elif action == 'add':
            # Handle add action
            pass
        elif action == 'remove':
            # Handle remove action
            pass
        elif action == 'update':
            # Handle update action
            pass
    
    def check_connectivity(self):
        """Periodic internet connectivity check"""
        if not check_internet_connection():
            logger.warning("Internet connection lost")
            # Could show reconnection UI here
            # For now, just log it
    
    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("Shutting down application")
        
        # Stop SignalR
        if self.signalr_client:
            self.signalr_client.stop()
        
        # Stop timers
        self.internet_check_timer.stop()
        
        # Close windows
        if self.player_window:
            self.player_window.close()
        if self.wifi_window:
            self.wifi_window.close()


def main():
    """Main entry point"""
    # Load environment first
    environment = os.getenv('ENVIRONMENT', 'development')
    load_environment(environment)
    
    # Setup logging
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    logger.info("="*60)
    logger.info(f"Marketing Display - {Config.ENVIRONMENT.upper()} MODE")
    logger.info("="*60)
    logger.info(f"Device: {Config.DEVICE_NAME}")
    logger.info(f"Backend: {Config.BACKEND_API_URL}")
    logger.info(f"Platform: {'Raspberry Pi' if Config.IS_RASPBERRY_PI else 'Development'}")
    logger.info("="*60)
    
    try:
        # Create and start application
        app = MarketingDisplayApp()
        exit_code = app.start()
        
        # Cleanup
        app.shutdown()
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
