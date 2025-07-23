"""
Version information for YouTube Downloader Pro
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Release information
RELEASE_NAME = "YouTube Downloader Pro"
RELEASE_DESCRIPTION = "High-performance YouTube video downloader with multiple interfaces"
AUTHOR = "YouTube Downloader Pro Team"
LICENSE = "MIT"

# Feature highlights for releases
FEATURES = [
    "5-10x faster downloads via async architecture",
    "50+ concurrent downloads supported", 
    "Multiple interfaces: Desktop GUI, Web Browser, Enhanced CLI",
    "Smart fallback: Always provides working interface",
    "Resume capability for interrupted downloads",
    "Batch downloads and playlist support",
    "Real-time progress tracking with speed/ETA",
    "Smart caching and duplicate detection"
]

# Requirements
REQUIREMENTS = {
    "python": "3.8+",
    "windows": "10+",
    "dependencies": ["yt-dlp", "aiohttp", "aiofiles", "tqdm", "flask"]
}

def get_version():
    """Get version string"""
    return __version__

def get_version_info():
    """Get version tuple"""
    return __version_info__

def get_release_info():
    """Get complete release information"""
    return {
        "version": __version__,
        "name": RELEASE_NAME, 
        "description": RELEASE_DESCRIPTION,
        "author": AUTHOR,
        "license": LICENSE,
        "features": FEATURES,
        "requirements": REQUIREMENTS
    }