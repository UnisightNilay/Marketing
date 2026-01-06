"""
VLC-based Media Player Engine for Marketing Display Application
Handles video and photo playback using VLC for better compatibility
"""
import os
import sys
import logging
import vlc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QMainWindow, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QPixmap, QCursor, QImage
from PIL import Image

from config import Config
from utils import is_video_file, is_image_file

logger = logging.getLogger(__name__)


class MediaPlayerWidget(QWidget):
    """Widget for displaying photos and videos using VLC"""
    
    # Signals
    media_finished = pyqtSignal()  # Emitted when current media finishes
    media_error = pyqtSignal(str)  # Emitted on playback error
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_media_path = None
        self.current_media_type = None
        self.vlc_instance = None
        self.vlc_player = None
        self.init_ui()
        self.init_vlc()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setStyleSheet("background-color: black;")
        
        # Hide mouse cursor
        self.setCursor(Qt.BlankCursor)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Use stacked layout for seamless transitions
        from PyQt5.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: black;")
        
        # Video frame for VLC
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setCursor(Qt.BlankCursor)
        self.video_frame.setMouseTracking(True)
        self.stacked_widget.addWidget(self.video_frame)
        
        # Double buffer for images - two image labels to eliminate black flash
        self.image_label_1 = QLabel()
        self.image_label_1.setAlignment(Qt.AlignCenter)
        self.image_label_1.setScaledContents(False)
        self.image_label_1.setStyleSheet("background-color: black;")
        self.image_label_1.setCursor(Qt.BlankCursor)
        self.stacked_widget.addWidget(self.image_label_1)
        
        self.image_label_2 = QLabel()
        self.image_label_2.setAlignment(Qt.AlignCenter)
        self.image_label_2.setScaledContents(False)
        self.image_label_2.setStyleSheet("background-color: black;")
        self.image_label_2.setCursor(Qt.BlankCursor)
        self.stacked_widget.addWidget(self.image_label_2)
        
        # Track which image label is currently active
        self.current_image_label = self.image_label_1
        self.next_image_label = self.image_label_2
        
        layout.addWidget(self.stacked_widget)
        
        # Timer for image duration
        self.image_timer = QTimer()
        self.image_timer.setSingleShot(True)
        self.image_timer.timeout.connect(self.on_image_timeout)
        
        # Timer to check video playback status
        self.video_check_timer = QTimer()
        self.video_check_timer.timeout.connect(self.check_video_status)
        
        self.setLayout(layout)
    
    def init_vlc(self):
        """Initialize VLC player"""
        try:
            # Create VLC instance with hardware acceleration enabled
            vlc_args = [
                '--no-xlib',  # Don't use Xlib
                '--quiet',  # Suppress console output
                '--no-video-title-show',  # Don't show video title on screen
                '--mouse-hide-timeout=0',  # Hide mouse immediately
                '--no-osd',  # Disable on-screen display
                '--no-snapshot-preview',  # No snapshot preview
                '--no-stats',  # No stats
                '--no-sub-autodetect-file',  # No subtitle detection
                '--avcodec-hw=any',  # Enable hardware decoding
                '--vout=gl',  # Use OpenGL video output
                '--codec=avcodec,all',  # Use avcodec for decoding
            ]
            
            self.vlc_instance = vlc.Instance(' '.join(vlc_args))
            self.vlc_player = self.vlc_instance.media_player_new()
            
            logger.info("VLC player initialized successfully with hardware acceleration")
        except Exception as e:
            logger.error(f"Failed to initialize VLC: {e}")
            self.media_error.emit(f"VLC initialization failed: {e}")
    
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
        """Play video file using VLC"""
        self.current_media_type = 'video'
        
        # Stop timers only, keep previous content visible
        self.image_timer.stop()
        
        # Switch to video frame (index 0)
        self.stacked_widget.setCurrentIndex(0)
        
        try:
            # Create media
            media = self.vlc_instance.media_new(filepath)
            self.vlc_player.set_media(media)
            
            # Set video output to our frame (only set once if not already set)
            if sys.platform.startswith('linux'):
                self.vlc_player.set_xwindow(int(self.video_frame.winId()))
            elif sys.platform == "win32":
                self.vlc_player.set_hwnd(int(self.video_frame.winId()))
            elif sys.platform == "darwin":
                self.vlc_player.set_nsobject(int(self.video_frame.winId()))
            
            # Start playback - VLC will handle transition internally
            self.vlc_player.play()
            
            # Start checking video status
            self.video_check_timer.start(500)  # Check every 500ms
            
            logger.info(f"Started video playback: {os.path.basename(filepath)}")
        except Exception as e:
            error_msg = f"Failed to play video: {e}"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
    
    def play_image(self, filepath: str, duration: int):
        """
        Play image file for specified duration
        
        Args:
            filepath: Path to image file
            duration: Display duration in seconds
        """
        self.current_media_type = 'image'
        
        # Stop timers only, keep previous content visible
        self.video_check_timer.stop()
        
        # Preload the image first
        pixmap = QPixmap()
        
        try:
            # Try loading with PIL first (supports WebP and more formats)
            pil_image = Image.open(filepath)
            
            # Convert PIL image to QPixmap
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to bytes
            import io
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Load into QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            
        except Exception as e:
            # Fallback to QPixmap direct load (for standard formats)
            logger.warning(f"PIL load failed, trying QPixmap: {e}")
            pixmap = QPixmap(filepath)
        
        if pixmap.isNull():
            error_msg = f"Failed to load image: {filepath}"
            logger.error(error_msg)
            self.media_error.emit(error_msg)
            return
        
        # Get the parent window size (or screen size if no parent)
        if self.window():
            target_size = self.window().size()
        else:
            target_size = QApplication.instance().primaryScreen().size()
        
        # Scale image to fill entire screen (will crop to fit, no black bars)
        scaled_pixmap = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,  # Fill screen completely
            Qt.SmoothTransformation
        )
        
        # Crop to exact screen size if needed
        if scaled_pixmap.size() != target_size:
            # Center crop
            x = (scaled_pixmap.width() - target_size.width()) // 2
            y = (scaled_pixmap.height() - target_size.height()) // 2
            scaled_pixmap = scaled_pixmap.copy(x, y, target_size.width(), target_size.height())
        
        # Swap buffers: load into next buffer, then switch to it
        self.next_image_label.setPixmap(scaled_pixmap)
        
        # Switch to the newly loaded image (instant switch, no black)
        widget_index = self.stacked_widget.indexOf(self.next_image_label)
        self.stacked_widget.setCurrentIndex(widget_index)
        
        # Swap current and next for next transition
        self.current_image_label, self.next_image_label = self.next_image_label, self.current_image_label
        self.stacked_widget.setCurrentIndex(1)
        
        # Start timer for image duration
        self.image_timer.start(duration * 1000)  # Convert to milliseconds
        
        logger.info(f"Displaying image for {duration} seconds: {os.path.basename(filepath)}")
    
    def check_video_status(self):
        """Check if video has finished playing"""
        if self.vlc_player and self.current_media_type == 'video':
            state = self.vlc_player.get_state()
            
            # Log CPU usage for debugging
            if hasattr(self, '_last_state_log'):
                if state != self._last_state_log:
                    logger.debug(f"Video state changed: {state}")
                    self._last_state_log = state
            else:
                logger.debug(f"Video state: {state}")
                self._last_state_log = state
            
            # VLC states: NothingSpecial=0, Opening=1, Buffering=2, Playing=3, Paused=4, Stopped=5, Ended=6, Error=7
            if state == vlc.State.Ended:
                logger.info("Video playback finished")
                self.video_check_timer.stop()
                self.media_finished.emit()
            elif state == vlc.State.Error:
                logger.error("Video playback error")
                self.video_check_timer.stop()
                self.media_error.emit("Video playback error")
            elif state == vlc.State.Stopped and self.vlc_player.get_time() > 0:
                # Video stopped unexpectedly
                logger.warning("Video stopped unexpectedly")
                self.video_check_timer.stop()
                self.media_error.emit("Video stopped unexpectedly")
    
    def on_image_timeout(self):
        """Called when image display duration expires"""
        logger.info("Image display finished")
        self.media_finished.emit()
    
    def stop(self):
        """Stop current playback"""
        # Stop VLC player
        if self.vlc_player:
            self.vlc_player.stop()
        
        # Stop timers
        self.image_timer.stop()
        self.video_check_timer.stop()
        
        # Clear both image labels
        self.image_label_1.clear()
        self.image_label_2.clear()
    
    def pause(self):
        """Pause current playback"""
        if self.vlc_player and self.current_media_type == 'video':
            self.vlc_player.pause()
    
    def resume(self):
        """Resume paused playback"""
        if self.vlc_player and self.current_media_type == 'video':
            self.vlc_player.play()
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        if self.vlc_player:
            self.vlc_player.release()
        if self.vlc_instance:
            self.vlc_instance.release()


class MediaPlayerApp(QMainWindow):
    """Main application window for media playback"""
    
    def __init__(self, playlist: list = None):
        super().__init__()
        self.playlist = playlist or []
        self.current_index = 0
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("Marketing Display")
        self.setStyleSheet("background-color: black;")
        
        # Hide mouse cursor globally for the entire app
        self.setCursor(Qt.BlankCursor)
        self.setMouseTracking(True)  # Track mouse to keep cursor hidden
        QApplication.instance().setOverrideCursor(QCursor(Qt.BlankCursor))
        
        # Create media player widget
        self.player_widget = MediaPlayerWidget(self)
        self.player_widget.media_finished.connect(self.on_media_finished)
        self.player_widget.media_error.connect(self.on_media_error)
        
        self.setCentralWidget(self.player_widget)
        
        # Set window properties - frameless and fullscreen
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Force window to cover entire screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            self.setGeometry(screen_geometry)
            logger.info(f"Setting window geometry to screen size: {screen_geometry.width()}x{screen_geometry.height()}")
        
        # Install event filter to keep cursor hidden
        self.installEventFilter(self)
        
        # Delay start to ensure window is fully initialized
        if self.playlist:
            QTimer.singleShot(100, self.play_current)
    
    def eventFilter(self, obj, event):
        """Filter events to keep mouse cursor hidden"""
        if event.type() == QEvent.HoverMove or event.type() == QEvent.MouseMove:
            # Keep cursor hidden even when mouse moves
            QApplication.instance().setOverrideCursor(QCursor(Qt.BlankCursor))
        return super().eventFilter(obj, event)
    
    def set_playlist(self, playlist: list):
        """Set new playlist and start playing"""
        self.playlist = playlist
        self.current_index = 0
        if self.playlist:
            self.play_current()
    
    def play_current(self):
        """Play current media item"""
        if not self.playlist or self.current_index >= len(self.playlist):
            logger.warning("No media to play")
            return
        
        item = self.playlist[self.current_index]
        filepath = item.get('path')
        duration = item.get('duration')
        
        logger.info(f"▶️  Playing [{self.current_index + 1}/{len(self.playlist)}]: {os.path.basename(filepath)}")
        
        if filepath:
            self.player_widget.play_media(filepath, duration)
        else:
            logger.error(f"Invalid playlist item: {item}")
            self.next_media()
    
    def next_media(self):
        """Play next media in playlist"""
        self.current_index = (self.current_index + 1) % len(self.playlist)
        if self.current_index == 0:
            logger.info("🔄 Playlist loop completed, restarting from beginning")
        self.play_current()
    
    def previous_media(self):
        """Play previous media in playlist"""
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_current()
    
    def on_media_finished(self):
        """Called when current media finishes"""
        logger.info("Media finished, playing next")
        self.next_media()
    
    def on_media_error(self, error_msg: str):
        """Called when media error occurs"""
        logger.error(f"Media error: {error_msg}")
        # Try next media
        self.next_media()
    
    def keyPressEvent(self, event: QEvent):
        """Handle keyboard events"""
        key = event.key()
        
        if key == Qt.Key_Escape or key == Qt.Key_Q:
            logger.info("Exit key pressed")
            self.close()
        elif key == Qt.Key_Space or key == Qt.Key_Right:
            logger.info("Next media requested")
            self.next_media()
        elif key == Qt.Key_Left:
            logger.info("Previous media requested")
            self.previous_media()
        elif key == Qt.Key_P:
            logger.info("Pause/Resume requested")
            # Toggle pause (not implemented yet)
        elif key == Qt.Key_F or key == Qt.Key_F11:
            # Toggle fullscreen
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
    
    def closeEvent(self, event):
        """Handle window close event"""
        logger.info("Closing media player")
        self.player_widget.cleanup()
        event.accept()
