"""
Utility functions for Marketing Display Application
"""
import os
import subprocess
import hashlib
import logging
from typing import Optional, List, Dict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def check_internet_connection(host: str = "8.8.8.8", timeout: int = 2) -> bool:
    """
    Check if internet connection is available
    
    Args:
        host: Host to ping (default: Google DNS)
        timeout: Timeout in seconds
        
    Returns:
        True if internet is available, False otherwise
    """
    try:
        subprocess.check_call(
            ["ping", "-c", "1", "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        logger.error(f"Error checking internet connection: {e}")
        return False


def get_file_hash(filepath: str) -> Optional[str]:
    """
    Calculate SHA256 hash of a file
    
    Args:
        filepath: Path to file
        
    Returns:
        Hex digest of file hash or None if error
    """
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return None


def get_url_filename(url: str) -> str:
    """
    Extract filename from URL
    
    Args:
        url: URL string
        
    Returns:
        Filename from URL
    """
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    return filename if filename else "download"


def get_file_size_mb(filepath: str) -> float:
    """
    Get file size in MB
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    except:
        return 0.0


def is_video_file(filename: str) -> bool:
    """
    Check if file is a video based on extension
    
    Args:
        filename: Filename or path
        
    Returns:
        True if video file, False otherwise
    """
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    ext = os.path.splitext(filename)[1].lower()
    return ext in video_extensions


def is_image_file(filename: str) -> bool:
    """
    Check if file is an image based on extension
    
    Args:
        filename: Filename or path
        
    Returns:
        True if image file, False otherwise
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    ext = os.path.splitext(filename)[1].lower()
    return ext in image_extensions


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes to human readable string
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def get_media_info(filepath: str) -> Dict[str, any]:
    """
    Get basic information about media file
    
    Args:
        filepath: Path to media file
        
    Returns:
        Dictionary with media info
    """
    info = {
        'path': filepath,
        'filename': os.path.basename(filepath),
        'exists': os.path.exists(filepath),
        'size_mb': 0.0,
        'is_video': False,
        'is_image': False,
    }
    
    if info['exists']:
        info['size_mb'] = get_file_size_mb(filepath)
        info['is_video'] = is_video_file(filepath)
        info['is_image'] = is_image_file(filepath)
    
    return info


def cleanup_old_files(directory: str, max_age_days: int = 30) -> int:
    """
    Remove files older than specified days
    
    Args:
        directory: Directory to clean
        max_age_days: Maximum age in days
        
    Returns:
        Number of files removed
    """
    import time
    
    removed_count = 0
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    removed_count += 1
                    logger.info(f"Removed old file: {filename}")
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")
    
    return removed_count


def setup_logging(log_file: str, log_level: str = 'INFO'):
    """
    Setup application logging
    
    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    from logging.handlers import RotatingFileHandler
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    
    # File handler
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized - Level: {log_level}")
