# YouTube Downloader Pro - Enhanced Edition

**Modern YouTube downloader with enhanced GUI, analytics, and playlist support**

## ✨ Features

### 🚀 **Enhanced Performance**
- **Async download architecture** for optimal speeds
- **Smart format fallback chain** for maximum compatibility
- **Resume capability** for interrupted downloads
- **Concurrent download support** with configurable limits
- **Progress tracking** with real-time speed and ETA

### 🖥️ **Modern GUI Interface**
- **Streamlined single-tab design** - All features in one place
- **Integrated playlist support** - Load entire playlists directly to queue
- **Real-time progress visualization** with progress bars and status updates
- **Advanced queue management** - Filter, sort, and control downloads
- **Persistent settings** with user preferences saved automatically
- **Analytics dashboard** - Track download statistics and history

### 🎯 **Smart Features**
- **Automatic URL validation** with visual feedback
- **Playlist expansion** - Automatically adds all videos from playlists
- **Quality selection** (360p to 4K, best, worst)
- **Description saving** and metadata extraction
- **Duplicate detection** prevents re-downloading
- **Context menu** for queue management (remove, retry, open location)
- **Session tracking** with persistent analytics storage

## 📦 Installation

### From Source
```bash
# Clone repository
git clone https://github.com/Oluwatemmy/Youtube-Downloader.git
cd Youtube-Downloader

# Install dependencies
pip install -r requirements.txt

# Run the GUI application
python youtube_downloader_gui.py
```

### Quick Launch
```bash
# Use the launcher script (Windows)
run_youtube_downloader.bat

# Or launch directly
python laucher.py
```

## 🚀 Usage

### Quick Start
1. **Launch** the application: `python youtube_downloader_gui.py`
2. **Enter URLs**:
   - Single video URL in the Quick Add field
   - Multiple URLs in the Batch Add section
   - Playlist URLs automatically expand to include all videos
3. **Configure settings** in the Settings tab (quality, download location, etc.)
4. **Start downloading** - Monitor progress in real-time
5. **View analytics** - Track your download history and statistics

### Main Interface Features

#### 🔗 **URL Input Section**
- **Quick Add**: Single URL input with real-time validation
- **Batch Add**: Multi-line text area for multiple URLs
- **Playlist Support**: Direct playlist URL input with automatic expansion
- **Auto-load**: Automatically loads video information when enabled

#### 📋 **Download Queue & Progress**
- **Integrated queue and progress** - Everything in one view
- **Real-time progress bars** for overall and current download
- **Queue filtering** - View all, pending, or completed downloads
- **Status tracking** - Visual status indicators for each video
- **Queue management** - Start, pause, stop, clear operations

#### ⚙️ **Settings Tab**
- **Download folder** selection with browse button
- **Video quality** options (best to worst, specific resolutions)
- **Concurrent downloads** configuration (1-10 simultaneous)
- **Behavior settings** - Auto-load info, save descriptions
- **Advanced options** - Retry attempts, timeout settings

#### 📊 **Analytics Tab**
- **Download statistics** - Total, successful, failed downloads
- **Data tracking** - Monitor total data downloaded
- **Session analytics** - Current session statistics
- **Recent activity** - Real-time activity log
- **Export/import** - Save analytics data
- **History management** - Clear or export download history

## 🔧 Advanced Features

### Queue Management
- **Context menu**: Right-click queue items for options
- **Remove selected**: Remove unwanted downloads
- **Retry failed**: Retry failed downloads
- **Open location**: Navigate to downloaded files
- **Copy URL**: Copy original video URL
- **Filter by status**: Show specific types of downloads

### Playlist Features
- **Automatic detection**: Recognizes playlist URLs
- **Bulk adding**: Adds all playlist videos to queue
- **Smart duplicate handling**: Prevents re-adding existing videos
- **Metadata preservation**: Maintains uploader, duration, and view count info

### Analytics & Tracking
- **Persistent storage**: Analytics saved between sessions
- **Export capability**: Save analytics as JSON
- **Session tracking**: Monitor current session performance
- **Activity logging**: Timestamped activity feed
- **Data visualization**: Progress tracking and statistics

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.8 or later
- **RAM**: 4GB (8GB recommended for large batches)
- **Storage**: 100MB for application + space for downloads
- **Network**: Internet connection

### Dependencies
- Python 3.8+
- tkinter (usually included with Python)
- yt-dlp (latest version)
- Standard library modules (threading, queue, json, pathlib, etc.)

Install dependencies: `pip install -r requirements.txt`

## 🛠️ Development & Building

### Project Structure
```
Youtube-Downloader/
├── Core Application
│   ├── youtube_downloader_gui.py      # Main GUI application
│   ├── yt_dlp_enhanced.py            # Enhanced download backend
│   ├── yt-dlp_downloader.py          # Basic CLI version
│   └── laucher.py                    # Application launcher
├── Build & Distribution
│   ├── create_installer.py           # Creates installer package
│   ├── build_windows.bat            # Builds Windows executable
│   ├── run_youtube_downloader.bat   # Windows launcher script
│   ├── test_build.py                # Build validation tests
│   └── version.py                   # Version management
├── Resources
│   ├── templates/
│   │   └── index.html              # Web UI template (legacy)
│   └── create_icon.py             # Icon generation utility
├── Documentation
│   ├── README.md                   # This file
│   ├── LICENSE                     # MIT license
│   └── requirements.txt           # Python dependencies
└── Downloads
    ├── downloads/                 # Default download directory
    └── test_downloads/           # Test download directory
```

### Building Windows Executable
```bash
# Build standalone executable
build_windows.bat
# Creates: dist/YouTubeDownloader.exe (if PyInstaller available)
```

### Creating Installer Package
```bash
# Create installer package
python create_installer.py
# Creates: YouTubeDownloader-Installer.zip
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/Oluwatemmy/Youtube-Downloader.git
cd Youtube-Downloader

# Install dependencies
pip install -r requirements.txt

# Run the main application
python youtube_downloader_gui.py

# Or use the launcher
python laucher.py
```

## 🆘 Troubleshooting

### Installation Issues

#### "Python not found"
- **Windows**: Install from [python.org](https://python.org)
- **Linux**: `sudo apt install python3 python3-pip`
- **macOS**: `brew install python3`

#### "tkinter not available"
- **Linux**: `sudo apt install python3-tk`
- **Most systems**: tkinter comes with Python by default

#### "ModuleNotFoundError"
- Install dependencies: `pip install -r requirements.txt`
- Ensure Python 3.8+ is installed: `python --version`

### Runtime Issues

#### Downloads fail
- Check internet connection
- Verify YouTube URL is accessible in browser
- Try reducing concurrent downloads in Settings
- Check available disk space
- Update yt-dlp: `pip install --upgrade yt-dlp`

#### GUI doesn't start
- Check Python version: `python --version` (need 3.8+)
- Verify tkinter: `python -c "import tkinter"`
- Try running with: `python -u youtube_downloader_gui.py`

#### Slow performance
- Increase concurrent downloads in Settings tab
- Use SSD for download directory
- Check internet connection speed
- Close bandwidth-heavy applications

#### Progress not updating
- Check if downloads folder has write permissions
- Verify sufficient disk space available
- Check Windows Defender/antivirus isn't blocking

### Getting Help
1. **Check error messages** in the application status bar
2. **View recent activity** in the Analytics tab
3. **Verify system requirements** are met
4. **Run validation**: `python test_build.py`
5. **Report issues** on GitHub with error details and system info

## 🔒 Legal Notice

⚠️ **Important**: This tool is for educational and personal use only.

- Always respect YouTube's Terms of Service
- Only download videos you have permission to download
- Respect copyright laws in your jurisdiction
- Do not distribute copyrighted content without permission
- The developers are not responsible for misuse of this software

## 🏆 Why Choose This Downloader?

### ✅ **Modern Interface**
- Clean, intuitive GUI design
- Real-time progress visualization
- Integrated playlist support
- Comprehensive analytics dashboard

### ✅ **Reliability**
- Robust error handling and recovery
- Resume interrupted downloads
- Multiple format fallback options
- Comprehensive logging and debugging

### ✅ **Performance**
- Async download architecture
- Configurable concurrent downloads
- Smart format selection
- Efficient progress tracking

### ✅ **User Experience**
- Single-tab streamlined design
- Persistent settings and preferences
- Context menus and keyboard shortcuts
- Comprehensive help and documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with clear description

### Development Guidelines
- Follow existing code style and structure
- Test on multiple platforms when possible
- Update documentation for new features
- Ensure backward compatibility
- Add appropriate error handling

### Code Structure
- **youtube_downloader_gui.py**: Main GUI application with all interface logic
- **yt_dlp_enhanced.py**: Download backend with async support
- **VideoInfo class**: Data structure for video metadata
- **Analytics system**: Persistent tracking and reporting

## 📞 Support

For support and questions:
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check troubleshooting section first
- **Testing**: Run `python test_build.py` to validate setup
- **Community**: Share experiences and solutions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🚀 Enhanced YouTube downloading with modern GUI, analytics, and streamlined workflow!**

Made with ❤️ for content creators and media enthusiasts