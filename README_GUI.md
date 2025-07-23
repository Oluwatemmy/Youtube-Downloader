# YouTube Downloader Pro - GUI Version

A cross-platform desktop application for downloading YouTube videos with a modern graphical user interface.

## Features

### 🖥️ Cross-Platform GUI
- **Windows**: Native executable (.exe)
- **macOS**: App bundle (.app) 
- **Linux**: Executable with optional AppImage

### ⚡ Performance Optimizations
- Concurrent downloads (up to 10 simultaneous)
- Async architecture for maximum efficiency
- Smart caching system
- Resume capability for interrupted downloads
- Connection pooling for reduced overhead

### 🎯 User-Friendly Interface
- Drag & drop URL input
- Download queue management
- Real-time progress tracking
- Settings persistence
- Batch download support
- Playlist download support

### 📊 Advanced Features
- Multiple video quality options (360p to 4K)
- Video description saving
- Smart duplicate detection
- Detailed download statistics
- Error handling and retry logic

## Installation

### Option 1: Run from Source
```bash
# Clone repository
git clone https://github.com/your-repo/Youtube-Downloader.git
cd Youtube-Downloader

# Install dependencies
pip install -r requirements.txt

# Run GUI
python youtube_downloader_gui.py
```

### Option 2: Download Standalone Executable
Download the latest release for your platform:
- **Windows**: `YouTubeDownloader.exe`
- **macOS**: `YouTubeDownloader.app`
- **Linux**: `YouTubeDownloader` or `YouTubeDownloader.AppImage`

## Building Standalone Executables

### Windows
```bash
# Run the build script
build_windows.bat

# Or manually with PyInstaller
pip install pyinstaller
pyinstaller youtube_downloader.spec
```

### macOS
```bash
# Make script executable and run
chmod +x build_macos.sh
./build_macos.sh

# Creates YouTubeDownloader.app in dist/
```

### Linux
```bash
# Make script executable and run
chmod +x build_linux.sh
./build_linux.sh

# Creates executable in dist/
```

## Usage

### Basic Usage
1. **Launch** the application
2. **Enter URLs** in the text area (one per line)
3. **Configure settings** (download directory, quality, concurrent downloads)
4. **Click "Add to Queue"** to add videos
5. **Click "Start Download"** to begin downloading

### Advanced Features

#### Batch Downloads
- Enter multiple URLs (one per line)
- Supports YouTube playlists
- Queue management with progress tracking

#### Settings
- **Download Directory**: Choose where to save videos
- **Video Quality**: Select from 360p to 4K (or "best")
- **Concurrent Downloads**: Adjust simultaneous downloads (1-10)
- **Save Descriptions**: Option to save video descriptions as text files

#### Queue Management
- **Start/Stop**: Control download process
- **Clear Completed**: Remove finished downloads from queue
- **Clear All**: Empty the entire queue
- **Progress Tracking**: Real-time status and progress bars

## System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM**: 4GB (8GB recommended for large batches)
- **Storage**: 100MB for application + space for downloads
- **Network**: Internet connection

### Dependencies (for source)
- Python 3.8+
- tkinter (usually included with Python)
- yt-dlp
- aiohttp
- aiofiles
- tqdm

### External Dependencies
- **FFmpeg**: Required for video processing (auto-installed by yt-dlp)

## Performance Tips

### For Best Performance
1. **Use SSD storage** for download directory
2. **Increase concurrent downloads** (3-5 for fast internet)
3. **Use wired connection** when possible
4. **Close other bandwidth-heavy applications**

### Troubleshooting

#### Common Issues
1. **"FFmpeg not found"**
   - Solution: yt-dlp will auto-install FFmpeg on first use

2. **Downloads fail with network errors**
   - Solution: Reduce concurrent downloads, check internet connection

3. **GUI doesn't start**
   - Solution: Ensure all dependencies are installed, try running from command line

4. **Slow downloads**
   - Solution: Check internet speed, reduce concurrent downloads, try different quality

#### Error Reporting
If you encounter issues:
1. Check error messages in the status bar
2. Try downloading a single video first
3. Verify the YouTube URL is valid and accessible

## Legal Notice

⚠️ **Important**: This tool is for educational purposes only. 

- Always respect YouTube's Terms of Service
- Only download videos you have permission to download
- Respect copyright laws in your jurisdiction
- Do not distribute copyrighted content without permission

## Development

### Project Structure
```
Youtube-Downloader/
├── youtube_downloader_gui.py    # Main GUI application
├── yt_dlp_enhanced.py          # Enhanced backend downloader
├── yt-dlp_downloader.py        # Original CLI version
├── youtube_downloader.spec     # PyInstaller spec file
├── build_windows.bat           # Windows build script
├── build_macos.sh             # macOS build script
├── build_linux.sh             # Linux build script
├── create_icon.py             # Icon creation utility
└── requirements.txt           # Python dependencies
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on multiple platforms
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 1.0.0
- Initial GUI release
- Cross-platform support
- Async download engine
- Queue management
- Settings persistence
- Standalone executables

## Support

For support and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Verify you're using the latest version

---

**Made with ❤️ for the open source community**