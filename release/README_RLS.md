# 🎥 YouTube Downloader Pro

A high-performance YouTube video downloader with multiple interfaces (Desktop GUI, Web Browser, CLI) and advanced features.

[![Release](https://img.shields.io/github/v/release/your-username/Youtube-Downloader?style=for-the-badge)](https://github.com/your-username/Youtube-Downloader/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/your-username/Youtube-Downloader/total?style=for-the-badge)](https://github.com/your-username/Youtube-Downloader/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## 🚀 Quick Download

### 🏆 Windows Installer (Recommended)
[![Download Installer](https://img.shields.io/badge/Download-Installer%20ZIP-blue?style=for-the-badge&logo=windows)](https://github.com/your-username/Youtube-Downloader/releases/latest/download/YouTubeDownloader-Installer.zip)

**Best for most users** - Only 25 KB, works on any Windows system with Python
1. Download and extract ZIP
2. Run `YouTube Downloader.bat`  
3. Dependencies install automatically
4. Enjoy!

### ⚡ Portable Executable
[![Download Portable](https://img.shields.io/badge/Download-Portable%20EXE-green?style=for-the-badge&logo=windows)](https://github.com/your-username/Youtube-Downloader/releases/latest/download/YouTubeDownloader-Portable.zip)

**No Python required** - Self-contained executable (~20 MB)
1. Download and extract ZIP
2. Run `YouTubeDownloader.exe`
3. Web interface launches if GUI unavailable

### 📱 All Releases
[![View All Releases](https://img.shields.io/badge/View-All%20Releases-purple?style=for-the-badge&logo=github)](https://github.com/your-username/Youtube-Downloader/releases)

---

**⚠️ Educational Use Only**: Always comply with YouTube's Terms of Service and only download videos you have permission to download.

## 🛠️ Features

### 🖥️ Multiple Interfaces
* **Desktop GUI** - Native Windows interface with drag & drop
* **Web Browser** - Modern interface accessible at http://127.0.0.1:5000  
* **Enhanced CLI** - Terminal interface with async downloads
* **Auto-detection** - Automatically selects best available interface

### ⚡ High Performance
* **5-10x faster** downloads via async architecture
* **50+ concurrent downloads** supported
* **Resume capability** for interrupted downloads
* **Smart caching** and duplicate detection
* **Connection pooling** reduces network overhead

### 📊 Advanced Features
* **Multiple video qualities** - 360p to 4K support
* **Batch downloads** - Handle multiple videos efficiently
* **Playlist support** - Download entire YouTube playlists
* **Real-time progress** - Speed, ETA, and progress tracking
* **Queue management** - Add, remove, prioritize downloads
* **Settings persistence** - Remembers your preferences

## 📦 Installation Options

### 🏆 Option 1: Windows Installer (Recommended)
**Easiest method - works on any Windows system with Python**

1. **Download installer**: `YouTubeDownloader-Installer.zip` 
2. **Extract** to any folder (e.g., Desktop)
3. **Run** `YouTube Downloader.bat`
4. **First time**: Dependencies install automatically
5. **Launch**: Application starts with best available interface

### 🔧 Option 2: Build Windows Executable
**For creating standalone .exe file**

```bash
# Clone repository
git clone https://github.com/your-repo/Youtube-Downloader.git
cd Youtube-Downloader

# Run build script
build_windows.bat

# Find executable in dist/YouTubeDownloader.exe
```

### 💻 Option 3: Run from Source

1.  **Clone the repository**

    ```bash
    git clone https://github.com/Oluwatemmy/Youtube-Downloader.git
    cd Youtube-Downloader
    ```

2.  **Create a virtual environment (recommended)**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

## 🔧 Installing ffmpeg

This script requires `ffmpeg` to merge audio and video streams. Follow the instructions below for your operating system:

**Windows:**

1.  Download the latest stable build from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html).
2.  Extract the ZIP file to a location on your computer (e.g., `C:\ffmpeg`).
3.  Add the `bin\` folder inside the extracted directory to your system's `PATH` environment variable.
4.  Verify the installation by opening a new command prompt and running:

    ```bash
    ffmpeg -version
    ```

**macOS (with Homebrew):**

1.  If you don't have Homebrew installed, you can install it from [https://brew.sh/](https://brew.sh/).
2.  Open your terminal and run:

    ```bash
    brew install ffmpeg
    ```

**Ubuntu/Linux:**

1.  Open your terminal and run:

    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```

## 🚀 Usage

### Quick Start
After installation, the application automatically detects the best interface:

1. **Desktop GUI** (if tkinter available) - Full-featured native interface
2. **Web Browser** (fallback) - Opens at http://127.0.0.1:5000  
3. **Enhanced CLI** (fallback) - Terminal-based with all features

### Interface Options
```bash
# Auto-detect best interface
python youtube_downloader_safe.py

# Force specific interface  
python youtube_downloader_gui.py    # Desktop GUI
python youtube_downloader_web.py    # Web interface
python yt_dlp_enhanced.py          # Enhanced CLI
```

Downloaded files are saved to `downloads/` folder (configurable in settings).

## 🔨 Creating Windows Installer

### For Developers - Create Installer Package
```bash
# Create the installer ZIP for distribution
python create_installer.py

# This creates: YouTubeDownloader-Installer.zip
# Share this file with end users
```

### For Developers - Build Executable  
```bash
# Create standalone .exe file
build_windows.bat

# This creates: dist/YouTubeDownloader.exe
# Note: May have tkinter issues, installer method is more reliable
```

## 🧠 How It Works
1. **User Input:** The script prompts the user for a YouTube video or playlist URL and a desired resolution.
2. **Video Information:** It uses `yt-dlp` to fetch video information, including available formats and the best resolution without downloading the actual content initially.
3. **List available Resolutions:** The script lists available resolutions and allows the user to select one.
5. **Resolution Selection:** The user selects their preferred resolution from the provided list.
6. **Duplicate Check:** The script checks if the video has already been downloaded by comparing the video ID with existing files in the `downloads/` directory.
7. **Download:** If the video hasn't been downloaded, it uses `yt-dlp` to download the video in the selected resolution and save it in the `downloads/` directory.
8. **Progress Display:** The script displays the download progress, including speed and estimated time of arrival (ETA).
9. **Error Handling:** If an error occurs during the download, the script retries the download up to 3 times before giving up.
10. **Completion Message:** Once the download is complete, the script informs the user and provides the path to the downloaded file.
11. **Exit:** The script exits after the download is complete.

## Output
Downloads are saved to:
```bash
<your-project-root>/downloads/
```
The filenames are cleaned to remove invalid characters, ensuring they are readable and compatible with most operating systems.

## ❗ Troubleshooting
### ffmpeg not found?
Make sure:
* `ffmpeg` is installed correctly to your system.
* The `bin` directory of `ffmpeg` is added to your system's `PATH` environment variable(for Windows).
* Restart your terminal or command prompt after making changes to the `PATH` variable.
* If you still encounter issues, try running `ffmpeg -version` in your terminal to verify the installation.
### yt-dlp not found?
Make sure:
* `yt-dlp` is installed correctly in your Python environment.
* You can check if `yt-dlp` is installed by running `yt-dlp --version` in your terminal.
* If you see an error, try reinstalling `yt-dlp` using `pip install -U yt-dlp`.
### Error during download?
The script includes basic error handling and will attempt retries automatically in some cases. 
Common issues include:
* `Network connectivity problems:` Check your internet connection and try again.
* `Invalid URL:` Ensure the URL you provided is correct and accessible.
* `Video unavailable:` The video may have been removed or set to private. Try a different URL.
* `Age-restricted content:` Some videos may be age-restricted. You may need to log in to your YouTube account to access them. You can do this by providing your cookies file using the `--cookies` option in `yt-dlp`.
*`Outdated yt-dlp version:` Ensure you have the latest version of `yt-dlp` installed. You can update it using:
```bash
pip install -U yt-dlp
```
If you encounter persistent errors, please check the yt-dlp documentation or issue tracker for potential solutions.

## 🤝 Contributing
Contributions are welcome! If you find a bug or have a feature request, please open an issue or submit a pull request.
Please ensure your code adheres to the existing style and includes appropriate tests.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.

## 🛡️ Disclaimer
This tool is intended for educational purposes only. Downloading copyrighted material without permission is illegal and violates YouTube's Terms of Service. Please use this script responsibly and only download videos that you have the right to access and save. The developers are not responsible for any misuse of this tool.

## 👤 Author

**Oluwaseyi Ajayi** - [GitHub](https://github.com/Oluwatemmy) | [Twitter](https://twitter.com/Oluwatemmy15) | [LinkedIn](https://www.linkedin.com/in/aotem11/) | [Portfolio](https://oluwatemmy.netlify.app/)
