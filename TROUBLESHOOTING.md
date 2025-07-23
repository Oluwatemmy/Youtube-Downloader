# YouTube Downloader - Troubleshooting Guide

## 🔧 Common Issues and Solutions

### Issue: "No module named 'tkinter'" when running executable

**Problem**: The PyInstaller executable can't find tkinter/GUI components.

**Solutions**:

#### Option 1: Use Web Interface (Recommended)
The web interface doesn't require tkinter and works on all systems:
```bash
# If you have the source code
python youtube_downloader_web.py

# Or run the safe launcher and select web interface
python youtube_downloader_safe.py
```

#### Option 2: Fix tkinter in Executable
1. **Rebuild with correct Python installation**:
   ```bash
   # Ensure Python was installed with tkinter support
   python -c "import tkinter; print('tkinter OK')"
   
   # If that fails, reinstall Python with tkinter
   # Download from python.org and ensure "tcl/tk and IDLE" is checked
   ```

2. **Use the safe launcher**:
   ```bash
   # Build with the safe launcher that has fallbacks
   build_windows.bat
   
   # The executable will automatically fall back to web interface
   # if GUI is not available
   ```

#### Option 3: Web-Only Build
```bash
# Build web-only version (no tkinter dependency)
build_windows_web.bat
```

### Issue: Unicode/Encoding Errors on Windows Console

**Problem**: Emoji characters cause crashes on Windows console.

**Solution**: Use the safe launcher (`youtube_downloader_safe.py`) which removes all Unicode characters.

### Issue: "Can't find a usable init.tcl"

**Problem**: tkinter/Tcl installation is incomplete or corrupted.

**Solutions**:
1. **Reinstall Python**: Download from python.org and ensure "tcl/tk and IDLE" is selected
2. **Use alternative interface**: The web interface doesn't require tkinter
3. **Manual Tcl/Tk installation**:
   - Download Tcl/Tk from activestate.com
   - Set TCL_LIBRARY and TK_LIBRARY environment variables

### Issue: Flask/Web Interface Not Working

**Problem**: Missing Flask dependency or network issues.

**Solutions**:
1. **Install Flask**:
   ```bash
   pip install flask
   ```

2. **Check port availability**:
   - Default port is 5000
   - If occupied, the launcher will show an error
   - Try closing other applications using port 5000

3. **Firewall issues**:
   - Allow Python through Windows Firewall
   - The web interface only listens on localhost (127.0.0.1)

### Issue: "yt-dlp" Related Errors

**Problem**: YouTube downloader backend issues.

**Solutions**:
1. **Update yt-dlp**:
   ```bash
   pip install -U yt-dlp
   ```

2. **Network connectivity**:
   - Check internet connection
   - Try with different videos
   - Some videos may be region-blocked

3. **FFmpeg missing**:
   - yt-dlp will auto-install FFmpeg on first use
   - For manual installation: https://ffmpeg.org/download.html

### Issue: Slow Downloads or Timeouts

**Problem**: Network or performance issues.

**Solutions**:
1. **Reduce concurrent downloads**:
   - Lower the concurrent download setting to 2-3
   - This reduces network load

2. **Check internet speed**:
   - Use speed test to verify connection
   - Adjust quality settings for slower connections

3. **Try different servers**:
   - YouTube has multiple CDN servers
   - Restart the application to potentially get different servers

### Issue: Downloads Fail with "HTTP Error 403"

**Problem**: YouTube access restrictions.

**Solutions**:
1. **Update yt-dlp**: YouTube frequently changes their API
   ```bash
   pip install -U yt-dlp
   ```

2. **Check video availability**:
   - Video might be private or region-blocked
   - Try with different videos

3. **Rate limiting**:
   - Reduce concurrent downloads
   - Add delays between downloads

### Issue: Executable Won't Start

**Problem**: Missing dependencies or system compatibility.

**Solutions**:
1. **Check system requirements**:
   - Windows 10+ (for .exe)
   - 64-bit system recommended

2. **Run from command line**:
   ```cmd
   # Navigate to exe location and run
   YouTubeDownloader.exe
   
   # This will show any error messages
   ```

3. **Try portable version**:
   - Use the Python source instead of executable
   - Install Python and run: `python youtube_downloader_safe.py`

### Issue: Videos Download with Wrong Quality

**Problem**: Quality selection not working correctly.

**Solutions**:
1. **Check available formats**:
   - Some videos don't have all quality options
   - "Best" quality is automatically selected

2. **Update format selection**:
   - Use specific quality settings (720p, 1080p)
   - Check if video actually supports the selected quality

3. **Network limitations**:
   - Lower quality for slower connections
   - Higher quality requires more bandwidth

## 🚀 Quick Fix Commands

### Complete Reinstall
```bash
# Remove old installation
rm -rf Youtube-Downloader/

# Clone fresh copy
git clone https://github.com/your-repo/Youtube-Downloader.git
cd Youtube-Downloader

# Install dependencies
pip install -r requirements.txt

# Test web interface (most compatible)
python youtube_downloader_web.py
```

### Minimal Working Setup
```bash
# Just the essentials
pip install yt-dlp flask

# Run basic web interface
python youtube_downloader_web.py
```

### Debug Mode
```bash
# Run with full error output
python youtube_downloader_safe.py

# Or check individual components
python -c "import tkinter; print('GUI: OK')"
python -c "import flask; print('Web: OK')"
python -c "import yt_dlp; print('Downloader: OK')"
```

## 📞 Getting Help

### Before Reporting Issues
1. Try the web interface first (`youtube_downloader_web.py`)
2. Update all dependencies: `pip install -U -r requirements.txt`
3. Test with a simple YouTube video
4. Check this troubleshooting guide

### Information to Include
When reporting issues, please include:
- Operating system and version
- Python version: `python --version`
- Error messages (full traceback)
- Steps to reproduce the issue
- YouTube URL that's failing (if applicable)

### Alternative Solutions
If nothing works:
1. **Use yt-dlp directly**: `pip install yt-dlp` then `yt-dlp [URL]`
2. **Try online converters**: Various web-based alternatives exist
3. **Use other GUI tools**: Many YouTube downloaders are available

## 🎯 Recommended Workflow

For maximum compatibility:

1. **First time setup**:
   ```bash
   python youtube_downloader_safe.py
   ```
   
2. **If GUI works**: Great! Use the desktop interface

3. **If GUI fails**: Automatically falls back to web interface

4. **If web fails**: Falls back to enhanced CLI

5. **If all fails**: Basic CLI as last resort

This multi-tier approach ensures the application works on virtually any system with Python installed.

---

**Still having issues?** The web interface (`youtube_downloader_web.py`) is the most reliable option and works on all systems with Python and an internet browser.