# This script is designed to download videos from YouTube using yt-dlp.
# It includes progress display, and duplicate checks.
# The script is modular, with functions for creating download paths, formatting sizes, and handling errors.
# The script is intended for educational purposes and should be used in compliance with YouTube's terms of service.
# Always ensure you have permission to download content from YouTube before doing so.

import yt_dlp
import os
import time

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(f"❌ {msg}")

def create_download_path():
    """
    Creates and returns the download path.
    """
    download_path = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(download_path, exist_ok=True)
    return download_path

def format_size(size):
    """
    Convert bytes to a human-readable format.
    """
    if size is None:
        return "Unknown size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def sanitize_filename(name):
    """
    Clean file names from forbidden characters.
    """
    return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).strip()

def progress_hook(d):
    """
    Show progress of download.
    """
    if d['status'] == 'downloading':
        print(f"⬇️  Downloading: {d['_percent_str']} at {d['_speed_str']} ETA {d['_eta_str']}", end='\r')

def handle_errors(e, attempt, retries):
    """
    Handle and log errors based on type.
    """
    msg = str(e)
    if "ffmpeg" in msg.lower():
        print("❌ Missing dependency: ffmpeg is required to merge video and audio formats.")
        print("➡️  Please install ffmpeg from: https://ffmpeg.org/download.html")
        return False
    if "getaddrinfo failed" in msg:
        print("❌ Network error: Could not resolve YouTube. Please check your internet or DNS settings.")
    elif "HTTP Error 403" in msg:
        print("❌ Access denied: This video may be age-restricted or region-blocked.")
    elif "HTTP Error 404" in msg:
        print("❌ Not found: This video might have been removed.")
    elif "Failed to extract" in msg:
        print("❌ Extraction error: YouTube might have changed something. Try running `yt-dlp -U` to update.")
    else:
        print(f"❌ Download error: {msg}")
    
    attempt += 1
    if attempt <= retries:
        print(f"Retrying... ({attempt}/{retries})")
        time.sleep(2)  # Wait before retrying
        return True
    return False

def download_video(url, retries=3):
    """
    Downloads a single video or an entire playlist with retries and duplicate check.
    """
    attempt = 1
    download_path = create_download_path()

    while attempt <= retries:
        try:
            video_info = get_video_info(url)
            if not video_info:
                return

            entries = video_info.get('entries', [video_info])

            for entry in entries:
                title = sanitize_filename(entry.get('title', 'video'))
                filesize = entry.get('filesize')
                print(f"\nStarting download for: {title}")
                if filesize:
                    print(f"Estimated file size: {format_size(filesize)}")

                # Expected file (check common extensions)
                file_exists = any(
                    os.path.exists(os.path.join(download_path, f"{title}.{ext}"))
                    for ext in ['mp4', 'mkv', 'webm']
                )

                if file_exists:
                    print(f"⚠️  Skipping already downloaded video: {title}")
                    continue

                ydl_opts = {
                    'logger': MyLogger(),
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                    'progress_hooks': [progress_hook],
                    'noplaylist': False,
                    'merge_output_format': 'mp4',  # ensure merged file format
                    'ignoreerrors': True,  # Skip bad videos
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([entry['webpage_url']])

                print(f"✅ Download complete: {title}")
                print(f"📂  Saved to: {download_path}")

            return

        except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
            if not handle_errors(e, attempt, retries):
                break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if not handle_errors(e, attempt, retries):
                break

    print(f"❌ Download failed after {retries} attempts.")

def get_video_info(url):
    """
    Fetch video or playlist info without downloading.
    """
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'skip_download': True}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"❌ Error retrieving video info: {e}")
    return None

def main():
    """
    Main entry point for script.
    """
    video_url = input("Enter the YouTube video or playlist URL: ").strip()
    download_video(video_url)

if __name__ == "__main__":
    main()
