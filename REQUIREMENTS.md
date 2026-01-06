# Marketing Display Application - Requirements Document

## Project Overview

A digital signage application for Raspberry Pi 5 that displays marketing content (photos and videos) fetched from a backend API, with real-time updates via SignalR.

---

## Functional Requirements

### FR1: Media Display
**FR1.1** - System shall display photos in fullscreen mode
**FR1.2** - System shall display videos in fullscreen mode without controls
**FR1.3** - Photos shall be displayed for a configurable duration (from JSON)
**FR1.4** - Videos shall play in their entirety
**FR1.5** - System shall automatically transition between media items
**FR1.6** - System shall loop through the playlist continuously

### FR2: Content Management
**FR2.1** - System shall fetch playlist from backend API (JSON format)
**FR2.2** - JSON shall contain media type, URL, duration (for photos), and order
**FR2.3** - System shall download media from Azure Blob Storage URLs
**FR2.4** - System shall cache downloaded media locally
**FR2.5** - System shall use cached media to avoid redundant downloads
**FR2.6** - System shall manage cache size (maximum 50GB of 64GB storage)

### FR3: Real-Time Updates
**FR3.1** - System shall connect to backend via SignalR/WebSocket
**FR3.2** - System shall listen for playlist update messages
**FR3.3** - On receiving update message, system shall fetch new playlist
**FR3.4** - System shall handle different update types:
  - `refresh` - Reload entire playlist
  - `add` - Add new media item
  - `remove` - Remove media item
  - `update` - Update existing item
**FR3.5** - System shall gracefully handle updates during playback
**FR3.6** - System shall automatically reconnect if SignalR connection drops

### FR4: Network Management
**FR4.1** - System shall check internet connectivity on startup
**FR4.2** - If no internet, system shall display WiFi setup UI
**FR4.3** - WiFi UI shall scan and list available networks
**FR4.4** - WiFi UI shall show signal strength for each network
**FR4.5** - WiFi UI shall indicate secured vs open networks
**FR4.6** - WiFi UI shall provide password input for secured networks
**FR4.7** - WiFi UI shall provide "Show Password" toggle
**FR4.8** - WiFi UI shall connect to selected network
**FR4.9** - WiFi UI shall display connection status (connecting, success, failure)
**FR4.10** - After successful connection, system shall start main application

### FR5: Error Handling
**FR5.1** - System shall retry failed downloads (max 3 attempts)
**FR5.2** - System shall skip corrupted media files
**FR5.3** - System shall log all errors
**FR5.4** - System shall continue operation if single media item fails
**FR5.5** - System shall display error screen if playlist is empty
**FR5.6** - System shall reconnect to backend if connection lost

### FR6: Auto-Start
**FR6.1** - System shall start automatically on Pi boot
**FR6.2** - System shall run as systemd service
**FR6.3** - System shall restart on crash
**FR6.4** - System shall handle graceful shutdown

---

## Non-Functional Requirements

### NFR1: Performance
**NFR1.1** - Application memory usage shall not exceed 500MB
**NFR1.2** - Video playback shall be smooth (30fps minimum)
**NFR1.3** - Transition between media shall be under 500ms
**NFR1.4** - Startup time shall be under 10 seconds
**NFR1.5** - Network requests shall timeout after 30 seconds

### NFR2: Reliability
**NFR2.1** - Application uptime shall be 99.9%
**NFR2.2** - Application shall recover from crashes automatically
**NFR2.3** - Application shall handle network interruptions gracefully
**NFR2.4** - Application shall validate all downloaded media

### NFR3: Usability
**NFR3.1** - WiFi setup UI shall be touch-friendly (large buttons)
**NFR3.2** - WiFi setup UI text shall be readable from 2 meters
**NFR3.3** - WiFi setup UI shall provide clear status messages
**NFR3.4** - System shall require no manual intervention during normal operation

### NFR4: Compatibility
**NFR4.1** - Application shall run on Raspberry Pi 5 (2GB RAM)
**NFR4.2** - Application shall support Raspberry Pi OS Lite (64-bit)
**NFR4.3** - Application shall be developed on Linux x86_64 machines
**NFR4.4** - Application shall support common video formats (MP4, AVI, MKV)
**NFR4.5** - Application shall support common image formats (JPG, PNG, WebP)

### NFR5: Security
**NFR5.1** - WiFi passwords shall not be logged
**NFR5.2** - API credentials shall be stored securely
**NFR5.3** - Downloaded media shall be validated before display
**NFR5.4** - HTTPS shall be used for all network requests

---

## Technical Specifications

### Hardware
- **Device:** Raspberry Pi 5
- **RAM:** 2GB
- **Storage:** 64GB (50GB max for media cache)
- **Display:** HDMI output (any resolution)
- **Network:** WiFi (802.11ac recommended)

### Software Stack
- **OS:** Raspberry Pi OS Lite (64-bit) with X11
- **Language:** Python 3.9+
- **UI Framework:** PyQt5
- **Video Player:** python-vlc or QMediaPlayer
- **HTTP Client:** aiohttp
- **SignalR Client:** signalrcore
- **Network Manager:** NetworkManager (nmcli)

### Dependencies
```
PyQt5>=5.15.0
python-vlc>=3.0.0
aiohttp>=3.8.0
signalrcore>=0.9.5
requests>=2.28.0
Pillow>=9.0.0
```

### API Endpoints
- **Playlist:** `GET {backend_url}/api/playlist`
- **SignalR Hub:** `{backend_url}/marketingHub`

### Media Support
- **Video:** H.264, H.265, VP9 (MP4, MKV containers)
- **Images:** JPEG, PNG, WebP
- **Max File Size:** 500MB per video, 10MB per image

---

## User Stories

### US1: First-Time Setup
**As a** technician  
**I want to** configure WiFi on first boot  
**So that** the device can connect to the internet

**Acceptance Criteria:**
- Device shows WiFi selection screen when no internet
- I can see all available networks with signal strength
- I can enter WiFi password
- Device connects and starts displaying content

### US2: Content Display
**As a** store manager  
**I want to** display marketing photos and videos  
**So that** customers see promotional content

**Acceptance Criteria:**
- Photos display for specified duration
- Videos play completely without controls
- Content transitions smoothly
- Display loops continuously

### US3: Content Updates
**As a** marketing manager  
**I want to** update content remotely  
**So that** I don't need physical access to devices

**Acceptance Criteria:**
- Backend sends update notification
- Device fetches new content automatically
- New content displays without restart
- Update happens seamlessly during playback

### US4: Network Recovery
**As a** system administrator  
**I want to** reconnect to WiFi if connection drops  
**So that** content updates continue working

**Acceptance Criteria:**
- Device detects connection loss
- Device attempts automatic reconnection
- If reconnection fails, WiFi setup appears
- Cached content continues playing during outage

---

## Testing Requirements

### Unit Tests
- Media player component
- Download manager
- Playlist parser
- WiFi scanner
- Cache manager

### Integration Tests
- End-to-end playlist fetch and display
- SignalR connection and message handling
- WiFi connection flow
- Error recovery scenarios

### Performance Tests
- Memory usage under load
- Video playback performance
- Download speed optimization
- Cache management efficiency

### User Acceptance Tests
- Complete installation on fresh Pi
- WiFi configuration workflow
- Content display quality
- Real-time update scenarios

---

## Deployment Requirements

### Pre-Installation
- Raspberry Pi OS Lite flashed to SD card
- Display connected via HDMI
- Power supply connected

### Installation Steps
1. Boot Raspberry Pi
2. Run installation script
3. Configure backend API URL
4. Enable systemd service
5. Reboot

### Post-Installation Verification
- Service starts automatically
- WiFi configuration works
- Content displays correctly
- Updates are received

---

## Maintenance Requirements

### Monitoring
- Application logs via journalctl
- Memory usage monitoring
- Storage usage monitoring
- Network connectivity status

### Updates
- Application updates via git pull + restart
- System updates via apt
- Configuration updates without reinstall

### Backup
- Configuration files backed up
- Cache can be cleared and rebuilt
- Service can be reinstalled without data loss

---

## Future Enhancements (Out of Scope for v1.0)

- Touch screen interaction
- Multiple display zones
- Scheduled content (time-based playlists)
- Analytics (content view tracking)
- Remote device management dashboard
- Multi-device synchronization
- Audio support
- Interactive content
- QR code display
- Weather/time widgets
