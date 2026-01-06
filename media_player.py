"""
Media Player Engine for Marketing Display Application
Handles video and photo playback
"""
import os
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl

from config import Config
from utils import is_video_file, is_image_file

logger = logging.getLogger(__name__)


class MediaPlayerWidget(QWidget):
    """Widget for displaying photos and videos"""
    
    # Signals
    media_finished = pyqtSignal()  # Emitted when current media finishes
    media_error = pyqtSignal(str)  # Emitted on playback error
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_media_path = None
        self.current_media_type = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setStyleSheet("background-color: black;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.hide()
        layout.addWidget(self.video_widget)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.hide()
        layout.addWidget(self.image_label)
        
        # Media player
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.stateChanged.connect(self.on_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.error.connect(self.on_player_error)
        
        # Timer for image duration
        self.image_timer = QTimer()
        self.image_timer.setSingleShot(True)
        self.image_timer.timeout.connect(self.on_image_timeout)
        
        self.setLayout(layout)
    
    def play_media(self, filepath: str, duration: int = None):
        """
        Play media file (video or image)
        
        Args:
            filepath: Path to media file
            duration: Duration in seconds (for images only)
        """
        if not os.path.exists(filepath):
            error_msg = f"Media file not found: {filepath}"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
            return
        
        logger.info(f"Playing media: {os.path.basename(filepath)}")
        
        self.current_media_path = filepath
        
        # Determine media type
        if is_video_file(filepath):
            self.play_video(filepath)
        elif is_image_file(filepath):
            self.play_image(filepath, duration or Config.DEFAULT_IMAGE_DURATION)
        else:
            error_msg = f"Unsupported media type: {filepath}"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
    
    def play_video(self, filepath: str):
        """Play video file"""
        self.current_media_type = 'video'
        
        # Stop any current playback
        self.stop()
        
        # Hide image, show video
        self.image_label.hide()
        self.video_widget.show()
        
        # Load and play video
        media_content = QMediaContent(QUrl.fromLocalFile(filepath))
        self.media_player.setMedia(media_content)
        self.media_player.play()
        
        logger.info(f"Started video playback: {os.path.basename(filepath)}")
    
    def play_image(self, filepath: str, duration: int):
        """
        Play image file for specified duration
        
        Args:
            filepath: Path to image file
            duration: Display duration in seconds
        """
        self.current_media_type = 'image'
        
        # Stop any current playback
        self.stop()
        
        # Hide video, show image
        self.video_widget.hide()
        self.image_label.show()
        
        # Load and display image
        pixmap = QPixmap(filepath)
        
        if pixmap.isNull():
            error_msg = f"Failed to load image: {filepath}"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
            return
        
        # Scale image to fit screen while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
        
        # Start timer for image duration
        self.image_timer.start(duration * 1000)  # Convert to milliseconds
        
        logger.info(f"Displaying image for {duration}s: {os.path.basename(filepath)}")
    
    def stop(self):
        """Stop current playback"""
        # Stop video
        if self.media_player.state() != QMediaPlayer.StoppedState:
            self.media_player.stop()
        
        # Stop image timer
        if self.image_timer.isActive():
            self.image_timer.stop()
    
    def pause(self):
        """Pause current playback"""
        if self.current_media_type == 'video':
            self.media_player.pause()
        elif self.current_media_type == 'image':
            self.image_timer.stop()
    
    def resume(self):
        """Resume paused playback"""
        if self.current_media_type == 'video':
            self.media_player.play()
        elif self.current_media_type == 'image':
            # Can't truly resume image, would need to track remaining time
            pass
    
    def on_state_changed(self, state):
        """Handle media player state changes"""
        if state == QMediaPlayer.StoppedState:
            logger.debug("Video playback stopped")
    
    def on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.EndOfMedia:
            logger.info("Video playback completed")
            self.media_finished.emit()
        elif status == QMediaPlayer.InvalidMedia:
            error_msg = "Invalid media format"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
    
    def on_player_error(self, error):
        """Handle media player errors"""
        error_msg = f"Player error: {self.media_player.errorString()}"
        logger.error(error_msg)
        self.media_error.emit(error_msg)
    
    def on_image_timeout(self):
        """Called when image display duration expires"""
        logger.info("Image display duration completed")
        self.media_finished.emit()
    
    def resizeEvent(self, event):
        """Handle window resize - rescale image if displaying"""
        super().resizeEvent(event)
        
        if self.current_media_type == 'image' and not self.image_label.pixmap().isNull():
            # Reload and rescale current image
            pixmap = QPixmap(self.current_media_path)
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)


class MediaPlayerApp(QWidget):
    """Main application window with media player"""
    
    def __init__(self, playlist=None):
        super().__init__()
        self.playlist = playlist or []
        self.current_index = 0
        self.init_ui()
    
    def init_ui(self):
        """Initialize the application window"""
        self.setWindowTitle(Config.APP_NAME)
        self.setStyleSheet("background-color: black;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Media player widget
        self.player = MediaPlayerWidget()
        self.player.media_finished.connect(self.play_next)
        self.player.media_error.connect(self.handle_media_error)
        layout.addWidget(self.player)
        
        self.setLayout(layout)
        
        # Set window size
        if Config.FULLSCREEN:
            self.showFullScreen()
        else:
            self.resize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
    
    def set_playlist(self, playlist: list):
        """
        Set new playlist
        
        Args:
            playlist: List of media items with 'path' and 'duration' keys
        """
        logger.info(f"Loading playlist with {len(playlist)} items")
        self.playlist = playlist
        self.current_index = 0
        
        if self.playlist:
            self.play_current()
    
    def play_current(self):
        """Play current media item"""
        if not self.playlist:
            logger.warning("Playlist is empty")
            self.show_no_content_message()
            return
        
        if self.current_index >= len(self.playlist):
            self.current_index = 0
        
        item = self.playlist[self.current_index]
        filepath = item.get('path')
        duration = item.get('duration')
        
        if filepath:
            self.player.play_media(filepath, duration)
        else:
            logger.error(f"Invalid playlist item: {item}")
            self.play_next()
    
    def play_next(self):
        """Play next media item in playlist"""
        if not self.playlist:
            return
        
        self.current_index = (self.current_index + 1) % len(self.playlist)
        logger.debug(f"Playing item {self.current_index + 1}/{len(self.playlist)}")
        self.play_current()
    
    def play_previous(self):
        """Play previous media item in playlist"""
        if not self.playlist:
            return
        
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_current()
    
    def handle_media_error(self, error_msg: str):
        """Handle media playback errors"""
        logger.error(f"Media error: {error_msg}")
        # Skip to next item on error
        QTimer.singleShot(2000, self.play_next)
    
    def show_no_content_message(self):
        """Show message when no content is available"""
        logger.warning("No content available to display")
        # Could show a "No Content" screen here
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        key = event.key()
        
        if key == Qt.Key_Escape:
            # Exit fullscreen or quit
            if self.isFullScreen():
                self.showNormal()
            else:
                self.close()
        elif key == Qt.Key_Right or key == Qt.Key_Space:
            # Next media
            self.play_next()
        elif key == Qt.Key_Left:
            # Previous media
            self.play_previous()
        elif key == Qt.Key_F:
            # Toggle fullscreen
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()


if __name__ == '__main__':
    # Test media player with sample media
    import sys
    from PyQt5.QtWidgets import QApplication
    from utils import setup_logging
    
    setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)
    
    # Create sample playlist (use your own media files)
    test_playlist = [
        {'path': '/path/to/image1.jpg', 'duration': 5},
        {'path': '/path/to/video1.mp4', 'duration': None},
        {'path': '/path/to/image2.png', 'duration': 7},
    ]
    
    app = QApplication(sys.argv)
    player_app = MediaPlayerApp(test_playlist)
    player_app.show()
    
    sys.exit(app.exec_())
