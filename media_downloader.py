"""
Media Downloader for Marketing Display Application
Handles downloading and caching media files from Azure Blob Storage
"""
import os
import asyncio
import aiohttp
import logging
from typing import Optional, Callable
from urllib.parse import urlparse

from config import Config
from utils import get_url_filename, get_file_hash, format_bytes, sanitize_filename

logger = logging.getLogger(__name__)


class MediaDownloader:
    """Handles media file downloads with caching"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.download_progress_callback: Optional[Callable] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_cached_path(self, url: str) -> str:
        """
        Get local cache path for URL
        
        Args:
            url: Media URL
            
        Returns:
            Local cache path
        """
        filename = get_url_filename(url)
        filename = sanitize_filename(filename)
        return os.path.join(Config.CACHE_DIR, filename)
    
    def is_cached(self, url: str) -> bool:
        """
        Check if media is already cached
        
        Args:
            url: Media URL
            
        Returns:
            True if cached, False otherwise
        """
        cache_path = self.get_cached_path(url)
        return os.path.exists(cache_path) and os.path.getsize(cache_path) > 0
    
    async def download_media(self, url: str, force_download: bool = False) -> Optional[str]:
        """
        Download media file from URL
        
        Args:
            url: Media URL to download
            force_download: Force re-download even if cached
            
        Returns:
            Local path to downloaded file or None if failed
        """
        cache_path = self.get_cached_path(url)
        
        # Return cached file if exists and not forcing download
        if self.is_cached(url) and not force_download:
            logger.info(f"Using cached file: {os.path.basename(cache_path)}")
            return cache_path
        
        # Ensure session exists
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        logger.info(f"Downloading: {url}")
        
        # Try download with retries
        for attempt in range(Config.MAX_DOWNLOAD_RETRIES):
            try:
                async with self.session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=Config.DOWNLOAD_TIMEOUT)
                ) as response:
                    
                    if response.status == 200:
                        # Get total file size
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded_size = 0
                        
                        logger.info(f"Downloading {format_bytes(total_size)}...")
                        
                        # Download in chunks
                        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                        
                        with open(cache_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(Config.DOWNLOAD_CHUNK_SIZE):
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # Progress callback
                                if self.download_progress_callback and total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    self.download_progress_callback(url, progress)
                        
                        logger.info(f"Downloaded successfully: {os.path.basename(cache_path)}")
                        return cache_path
                    
                    else:
                        logger.error(f"Download failed with status {response.status}: {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Download timeout (attempt {attempt + 1}/{Config.MAX_DOWNLOAD_RETRIES}): {url}")
            except Exception as e:
                logger.error(f"Download error (attempt {attempt + 1}/{Config.MAX_DOWNLOAD_RETRIES}): {e}")
            
            # Wait before retry
            if attempt < Config.MAX_DOWNLOAD_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to download after {Config.MAX_DOWNLOAD_RETRIES} attempts: {url}")
        return None
    
    async def download_playlist(self, items: list) -> list:
        """
        Download all media from playlist
        
        Args:
            items: List of playlist items with 'url' key
            
        Returns:
            List of items with added 'path' key (local cache path)
        """
        logger.info(f"Downloading playlist with {len(items)} items")
        
        # Ensure session exists
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Download items with concurrency limit
        semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_DOWNLOADS)
        
        async def download_item(item):
            async with semaphore:
                url = item.get('url')
                if url:
                    path = await self.download_media(url)
                    if path:
                        item['path'] = path
                        return item
                return None
        
        # Download all items
        tasks = [download_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful downloads
        downloaded_items = []
        for result in results:
            if isinstance(result, dict) and result.get('path'):
                downloaded_items.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Download task failed: {result}")
        
        logger.info(f"Successfully downloaded {len(downloaded_items)}/{len(items)} items")
        return downloaded_items
    
    def cleanup_cache(self, keep_files: list = None):
        """
        Clean up cache directory
        
        Args:
            keep_files: List of filenames to keep (others will be deleted)
        """
        if not os.path.exists(Config.CACHE_DIR):
            return
        
        keep_files = keep_files or []
        keep_basenames = [os.path.basename(f) for f in keep_files]
        
        removed_count = 0
        freed_space = 0
        
        try:
            for filename in os.listdir(Config.CACHE_DIR):
                if filename not in keep_basenames:
                    filepath = os.path.join(Config.CACHE_DIR, filename)
                    if os.path.isfile(filepath):
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        removed_count += 1
                        freed_space += file_size
                        logger.info(f"Removed cached file: {filename}")
            
            if removed_count > 0:
                logger.info(f"Cache cleanup: removed {removed_count} files, freed {format_bytes(freed_space)}")
        
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def check_cache_size(self) -> bool:
        """
        Check if cache size is within limits
        
        Returns:
            True if cache is under threshold, False if cleanup needed
        """
        current_size = Config.get_cache_size_gb()
        max_size = Config.MAX_CACHE_SIZE_GB
        threshold = Config.CACHE_CLEANUP_THRESHOLD
        
        if current_size >= (max_size * threshold):
            logger.warning(f"Cache size ({current_size:.2f} GB) exceeds threshold ({max_size * threshold:.2f} GB)")
            return False
        
        return True


# Convenience function for synchronous usage
def download_media_sync(url: str) -> Optional[str]:
    """
    Synchronous wrapper for downloading media
    
    Args:
        url: Media URL
        
    Returns:
        Local cache path or None if failed
    """
    async def _download():
        async with MediaDownloader() as downloader:
            return await downloader.download_media(url)
    
    return asyncio.run(_download())


if __name__ == '__main__':
    # Test downloader
    import sys
    from utils import setup_logging
    
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    test_url = "https://example.com/test-image.jpg"
    
    async def test():
        async with MediaDownloader() as downloader:
            # Test single download
            path = await downloader.download_media(test_url)
            if path:
                print(f"Downloaded to: {path}")
            
            # Test playlist download
            test_playlist = [
                {'url': 'https://example.com/image1.jpg', 'duration': 5},
                {'url': 'https://example.com/video1.mp4'},
            ]
            
            results = await downloader.download_playlist(test_playlist)
            print(f"Downloaded {len(results)} items")
    
    asyncio.run(test())
