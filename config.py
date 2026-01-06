"""
Configuration settings for Marketing Display Application
"""
import os
import platform
from pathlib import Path
from dotenv import load_dotenv


def load_environment(mode: str = None):
    """
    Load environment variables from .env file based on mode
    
    Args:
        mode: 'development', 'staging', or 'production'
              If None, reads from ENVIRONMENT variable or defaults to 'development'
    """
    # Determine mode
    if mode is None:
        mode = os.getenv('ENVIRONMENT', 'development')
    
    # Load appropriate .env file
    base_dir = Path(__file__).parent
    env_file = base_dir / f'.env.{mode}'
    
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✓ Loaded environment: {mode} from {env_file}")
    else:
        print(f"⚠ Environment file not found: {env_file}")
        print(f"  Using default/system environment variables")
    
    # Set environment mode
    os.environ['ENVIRONMENT'] = mode


def is_raspberry_pi():
    """Detect if running on Raspberry Pi"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False


class Config:
    """Application configuration"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    IS_RASPBERRY_PI = is_raspberry_pi()
    IS_DEVELOPMENT = ENVIRONMENT == 'development' or os.getenv('IS_DEVELOPMENT', 'false').lower() == 'true'
    
    # Device Configuration
    DEVICE_TYPE = int(os.getenv('DEVICE_TYPE', '11'))
    DEVICE_NAME = os.getenv('DEVICE_NAME', 'Marketing Display')
    
    # Backend API Configuration
    BACKEND_API_URL = os.getenv('BASE_URL', 'http://localhost:5000')
    BACKEND_POS_URL = os.getenv('BASE_URL_POS', 'http://localhost:5002')
    BACKEND_INVENTORY_URL = os.getenv('BASE_URL_INVENTORY', 'http://localhost:5001')
    BACKEND_SIGNALR_URL = os.getenv('BASE_URL_SIGNALR', BACKEND_INVENTORY_URL)
    
    PLAYLIST_ENDPOINT = f"{BACKEND_API_URL}/api/playlist"
    SIGNALR_HUB_URL = f"{BACKEND_SIGNALR_URL}/hubs/marketing"
    
    # Registration & Polling
    REGISTRATION_POLL_INTERVAL = int(os.getenv('REGISTRATION_POLL_INTERVAL', '10'))
    HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '30'))
    
    # Media Cache Configuration
    CACHE_DIR = os.path.expanduser('~/media-cache')
    
    MAX_CACHE_SIZE_GB = 50  # Maximum cache size in GB
    CACHE_CLEANUP_THRESHOLD = 0.9  # Clean when 90% full
    
    # Display Configuration
    FULLSCREEN = True  # Always fullscreen (kiosk mode)
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080
    
    # Video Configuration
    USE_HARDWARE_ACCEL = IS_RASPBERRY_PI
    DEFAULT_VIDEO_OPTIONS = []
    
    if USE_HARDWARE_ACCEL:
        # Raspberry Pi hardware acceleration
        DEFAULT_VIDEO_OPTIONS = [
            '--vout=mmal_vout',
            '--codec=mmal',
        ]
    
    # Image Configuration
    DEFAULT_IMAGE_DURATION = 10  # seconds
    IMAGE_TRANSITION_DURATION = 500  # milliseconds
    
    # Download Configuration
    DOWNLOAD_TIMEOUT = 300  # seconds (5 minutes)
    MAX_DOWNLOAD_RETRIES = 3
    DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    MAX_CONCURRENT_DOWNLOADS = 3
    
    # SignalR Configuration
    SIGNALR_RECONNECT_INTERVAL = 5  # seconds
    SIGNALR_MAX_RECONNECT_ATTEMPTS = 10
    
    # Network Check Configuration
    INTERNET_CHECK_INTERVAL = 5  # seconds
    INTERNET_CHECK_HOST = '8.8.8.8'
    INTERNET_CHECK_TIMEOUT = 2  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.path.join(os.path.dirname(CACHE_DIR), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'marketing-display.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Application Configuration
    APP_NAME = "Marketing Display"
    APP_VERSION = "1.0.0"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
    
    @classmethod
    def get_cache_size_gb(cls):
        """Get current cache size in GB"""
        total_size = 0
        if os.path.exists(cls.CACHE_DIR):
            for dirpath, dirnames, filenames in os.walk(cls.CACHE_DIR):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        return total_size / (1024 ** 3)  # Convert to GB
    
    @classmethod
    def print_config(cls):
        """Print configuration for debugging"""
        print(f"\n{'='*60}")
        print(f"{cls.APP_NAME} v{cls.APP_VERSION}")
        print(f"{'='*60}")
        print(f"Platform: {'Raspberry Pi' if cls.IS_RASPBERRY_PI else 'Development'}")
        print(f"Development Mode: {cls.IS_DEVELOPMENT}")
        print(f"Backend API: {cls.BACKEND_API_URL}")
        print(f"Cache Directory: {cls.CACHE_DIR}")
        print(f"Cache Size: {cls.get_cache_size_gb():.2f} GB / {cls.MAX_CACHE_SIZE_GB} GB")
        print(f"Fullscreen: {cls.FULLSCREEN}")
        print(f"Hardware Acceleration: {cls.USE_HARDWARE_ACCEL}")
        print(f"{'='*60}\n")


# Initialize directories on import
Config.ensure_directories()
