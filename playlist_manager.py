"""
Playlist Manager for Marketing Display Application
Handles playlist fetching, parsing, and state management
"""
import json
import logging
import requests
from typing import Optional, List, Dict
from datetime import datetime

from config import Config

logger = logging.getLogger(__name__)


class PlaylistManager:
    """Manages playlist state and backend communication"""
    
    def __init__(self):
        self.current_playlist: List[Dict] = []
        self.playlist_id: Optional[str] = None
        self.playlist_version: Optional[str] = None
        self.last_updated: Optional[datetime] = None
    
    def fetch_playlist(self) -> Optional[List[Dict]]:
        """
        Fetch playlist from backend API
        
        Returns:
            List of playlist items or None if failed
        """
        try:
            logger.info(f"Fetching playlist from: {Config.PLAYLIST_ENDPOINT}")
            
            response = requests.get(
                Config.PLAYLIST_ENDPOINT,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_playlist(data)
            else:
                logger.error(f"Failed to fetch playlist: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Playlist fetch timeout")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Connection error while fetching playlist")
            return None
        except Exception as e:
            logger.error(f"Error fetching playlist: {e}")
            return None
    
    def parse_playlist(self, data: Dict) -> List[Dict]:
        """
        Parse playlist JSON data
        
        Args:
            data: JSON playlist data
            
        Returns:
            List of parsed playlist items
        """
        try:
            # Extract metadata
            self.playlist_id = data.get('playlistId')
            self.playlist_version = data.get('version')
            
            last_updated_str = data.get('lastUpdated')
            if last_updated_str:
                self.last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
            
            # Extract items
            items = data.get('items', [])
            
            # Sort by order
            items.sort(key=lambda x: x.get('order', 0))
            
            # Validate and clean items
            validated_items = []
            for item in items:
                if self.validate_item(item):
                    validated_items.append(item)
                else:
                    logger.warning(f"Invalid playlist item: {item.get('id')}")
            
            self.current_playlist = validated_items
            
            logger.info(
                f"Parsed playlist: ID={self.playlist_id}, "
                f"Version={self.playlist_version}, "
                f"Items={len(validated_items)}"
            )
            
            return validated_items
            
        except Exception as e:
            logger.error(f"Error parsing playlist: {e}")
            return []
    
    def validate_item(self, item: Dict) -> bool:
        """
        Validate playlist item
        
        Args:
            item: Playlist item dict
            
        Returns:
            True if valid, False otherwise
        """
        # Required fields
        if not item.get('id'):
            return False
        if not item.get('type'):
            return False
        if not item.get('url'):
            return False
        
        # Type validation
        if item['type'] not in ['photo', 'video', 'image']:
            logger.warning(f"Unknown media type: {item['type']}")
            return False
        
        # Duration required for photos
        if item['type'] in ['photo', 'image'] and not item.get('duration'):
            logger.warning(f"Photo missing duration: {item['id']}")
            item['duration'] = Config.DEFAULT_IMAGE_DURATION
        
        return True
    
    def get_current_playlist(self) -> List[Dict]:
        """Get current playlist"""
        return self.current_playlist
    
    def update_playlist(self, new_items: List[Dict]):
        """
        Update current playlist with new items
        
        Args:
            new_items: New playlist items
        """
        self.current_playlist = new_items
        logger.info(f"Playlist updated: {len(new_items)} items")
    
    def add_item(self, item: Dict):
        """
        Add item to playlist
        
        Args:
            item: Playlist item to add
        """
        if self.validate_item(item):
            self.current_playlist.append(item)
            # Re-sort by order
            self.current_playlist.sort(key=lambda x: x.get('order', 0))
            logger.info(f"Added item to playlist: {item['id']}")
        else:
            logger.warning(f"Cannot add invalid item: {item.get('id')}")
    
    def remove_item(self, item_id: str):
        """
        Remove item from playlist
        
        Args:
            item_id: ID of item to remove
        """
        original_length = len(self.current_playlist)
        self.current_playlist = [
            item for item in self.current_playlist
            if item.get('id') != item_id
        ]
        
        if len(self.current_playlist) < original_length:
            logger.info(f"Removed item from playlist: {item_id}")
        else:
            logger.warning(f"Item not found in playlist: {item_id}")
    
    def update_item(self, item_id: str, updated_data: Dict):
        """
        Update existing playlist item
        
        Args:
            item_id: ID of item to update
            updated_data: New data for item
        """
        for i, item in enumerate(self.current_playlist):
            if item.get('id') == item_id:
                # Merge updated data
                item.update(updated_data)
                if self.validate_item(item):
                    self.current_playlist[i] = item
                    logger.info(f"Updated playlist item: {item_id}")
                else:
                    logger.warning(f"Updated item validation failed: {item_id}")
                break
        else:
            logger.warning(f"Item not found for update: {item_id}")
    
    def save_playlist_cache(self, filepath: str):
        """
        Save playlist to local cache file
        
        Args:
            filepath: Path to cache file
        """
        try:
            cache_data = {
                'playlistId': self.playlist_id,
                'version': self.playlist_version,
                'lastUpdated': self.last_updated.isoformat() if self.last_updated else None,
                'items': self.current_playlist
            }
            
            with open(filepath, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Playlist cached to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving playlist cache: {e}")
    
    def load_playlist_cache(self, filepath: str) -> bool:
        """
        Load playlist from local cache file
        
        Args:
            filepath: Path to cache file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.parse_playlist(data)
            logger.info(f"Playlist loaded from cache: {filepath}")
            return True
            
        except FileNotFoundError:
            logger.warning(f"Cache file not found: {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error loading playlist cache: {e}")
            return False


if __name__ == '__main__':
    # Test playlist manager
    from utils import setup_logging
    
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    manager = PlaylistManager()
    
    # Test with sample data
    sample_data = {
        "playlistId": "test-123",
        "version": "1.0.0",
        "lastUpdated": "2026-01-02T10:30:00Z",
        "items": [
            {
                "id": "item-1",
                "type": "photo",
                "url": "https://example.com/photo1.jpg",
                "duration": 10,
                "order": 1
            },
            {
                "id": "item-2",
                "type": "video",
                "url": "https://example.com/video1.mp4",
                "order": 2
            }
        ]
    }
    
    items = manager.parse_playlist(sample_data)
    print(f"Parsed {len(items)} items")
    print(f"Playlist ID: {manager.playlist_id}")
