"""
SignalR Client for Marketing Display Application
Handles real-time communication with backend
"""
import logging
import time
from typing import Callable, Optional
from signalrcore.hub_connection_builder import HubConnectionBuilder

from config import Config

logger = logging.getLogger(__name__)


class SignalRClient:
    """SignalR client for real-time playlist updates"""
    
    def __init__(self, on_playlist_updated: Optional[Callable] = None):
        self.hub_connection = None
        self.on_playlist_updated = on_playlist_updated
        self.is_connected = False
        self.reconnect_attempts = 0
    
    def start(self):
        """Start SignalR connection"""
        try:
            logger.info(f"Connecting to SignalR hub: {Config.SIGNALR_HUB_URL}")
            
            # Build hub connection
            self.hub_connection = HubConnectionBuilder() \
                .with_url(Config.SIGNALR_HUB_URL) \
                .with_automatic_reconnect({
                    "type": "interval",
                    "intervals": [0, 2, 5, 10, 30, 60]
                }) \
                .build()
            
            # Register event handlers
            self.hub_connection.on_open(self.on_open)
            self.hub_connection.on_close(self.on_close)
            self.hub_connection.on_error(self.on_error)
            
            # Register message handlers
            self.hub_connection.on("PlaylistUpdated", self.handle_playlist_updated)
            self.hub_connection.on("ContentChanged", self.handle_content_changed)
            
            # Start connection
            self.hub_connection.start()
            
            logger.info("SignalR connection started")
            
        except Exception as e:
            logger.error(f"Failed to start SignalR connection: {e}")
    
    def stop(self):
        """Stop SignalR connection"""
        if self.hub_connection:
            try:
                self.hub_connection.stop()
                logger.info("SignalR connection stopped")
            except Exception as e:
                logger.error(f"Error stopping SignalR connection: {e}")
    
    def on_open(self):
        """Called when connection opens"""
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info("SignalR connection established")
    
    def on_close(self):
        """Called when connection closes"""
        self.is_connected = False
        logger.warning("SignalR connection closed")
        
        # Attempt reconnection
        if self.reconnect_attempts < Config.SIGNALR_MAX_RECONNECT_ATTEMPTS:
            self.reconnect_attempts += 1
            logger.info(f"Reconnecting... (attempt {self.reconnect_attempts})")
            time.sleep(Config.SIGNALR_RECONNECT_INTERVAL)
            self.start()
    
    def on_error(self, error):
        """Called on connection error"""
        logger.error(f"SignalR error: {error}")
    
    def handle_playlist_updated(self, message):
        """
        Handle PlaylistUpdated message from backend
        
        Args:
            message: Message data from SignalR
        """
        try:
            logger.info(f"Received PlaylistUpdated message: {message}")
            
            playlist_id = message.get('playlistId')
            action = message.get('action', 'refresh')
            
            # Call callback if registered
            if self.on_playlist_updated:
                self.on_playlist_updated(action, message)
            
        except Exception as e:
            logger.error(f"Error handling PlaylistUpdated message: {e}")
    
    def handle_content_changed(self, message):
        """
        Handle ContentChanged message from backend
        
        Args:
            message: Message data from SignalR
        """
        try:
            logger.info(f"Received ContentChanged message: {message}")
            
            # Treat as playlist update
            if self.on_playlist_updated:
                self.on_playlist_updated('refresh', message)
            
        except Exception as e:
            logger.error(f"Error handling ContentChanged message: {e}")
    
    def send_message(self, method: str, *args):
        """
        Send message to SignalR hub
        
        Args:
            method: Hub method name
            *args: Method arguments
        """
        if self.hub_connection and self.is_connected:
            try:
                self.hub_connection.send(method, args)
                logger.debug(f"Sent message: {method}")
            except Exception as e:
                logger.error(f"Error sending message: {e}")
        else:
            logger.warning("Cannot send message: not connected")


if __name__ == '__main__':
    # Test SignalR client
    from utils import setup_logging
    
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    def on_update(action, message):
        print(f"Update received: {action} - {message}")
    
    client = SignalRClient(on_playlist_updated=on_update)
    
    try:
        client.start()
        print("SignalR client running... Press Ctrl+C to stop")
        
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()
