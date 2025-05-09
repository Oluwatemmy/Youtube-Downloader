# This script is designed to download videos from YouTube using yt-dlp.
# It includes progress display, and duplicate checks.
# The script is modular, with functions for creating download paths, formatting sizes, and handling errors.
# The script is intended for educational purposes and should be used in compliance with YouTube's terms of service.
# Always ensure you have permission to download content from YouTube before doing so.

import yt_dlp
import os
import time

# Target resolutions
TARGET_RESOLUTIONS = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]

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
    
    if attempt <= retries:
        print(f"Retrying... ({attempt}/{retries})")
        time.sleep(2)  # Wait before retrying
        return True
    return False

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

def download_video(url, retries=3):
    """
    Downloads a single video or an entire playlist with retries, resolution selection, and duplicate check.
    """
    attempt = 1
    download_path = create_download_path()

    while attempt <= retries:
        try:
            video_info = get_video_info(url)
            if not video_info:
                return
            
            # return video title
            title = video_info.get('title', 'video')
            print(f"\n🎬 Title: {title}\n")

            formats = video_info.get('formats', [])
            if not formats:
                print("❌ No downloadable formats found for this video.")
                return
            
            # Include all video formats (even video-only), and ignore audio-only
            filtered_formats = []
            for f in formats:
                resolution = f.get('format_note') or f.get('height')
                if f.get('vcodec') != 'none' and resolution in TARGET_RESOLUTIONS:
                    if isinstance(resolution, int):
                        resolution = f"{resolution}p"
                    ext = f.get('ext')
                    filesize = f.get('filesize') or f.get('filesize_approx')

                    filtered_formats.append({
                        'format_id': f['format_id'],
                        'resolution': resolution or 'Unknown',
                        'filesize': filesize,
                        'ext': ext,
                    })
            
            # # Filter formats: only mp4 + common resolutions
            # filtered_formats = []
            # for f in formats:
            #     resolution = f.get('format_note') or f.get('height')
            #     ext = f.get('ext')
            #     filesize = f.get('filesize') or f.get('filesize_approx')

            #     if isinstance(resolution, int):
            #         resolution = f"{resolution}p"

            #     if ext == 'mp4' and resolution in TARGET_RESOLUTIONS and f.get("vcodec") != 'none' and f.get("acodec") != 'none':
            #         filtered_formats.append({
            #             'format_id': f['format_id'],
            #             'resolution': resolution,
            #             'filesize': filesize,
            #         })

            if not filtered_formats:
                print("❌ No suitable formats found for the specified resolutions.")
                return
            
            # Sort formats by resolution (best effort)
            filtered_formats.sort(key=lambda x: int(x['resolution'].replace('p', '')) if x['resolution'].endswith('p') else 0)


            # Display available formats and file sizes
            print("\nAvailable video formats:")
            for i, fmt in enumerate(filtered_formats):
                filesize = fmt.get('filesize')
                print(f"{i + 1}. {fmt['resolution']} - {format_size(filesize)} ({fmt['ext']})")

            # Ask user to select format
            try:
                choice = int(input(f"\nChoose the format number (1-{len(filtered_formats)}): ").strip())
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
                return
            if choice < 1 or choice > len(filtered_formats):
                print("❌ Invalid choice.")
                return

            selected_format = filtered_formats[choice - 1]
            resolution = selected_format.get('resolution')
            filesize = selected_format.get('filesize')
            print(f"\nSelected resolution: {resolution} - {format_size(filesize)}")

            # Check if file already exists
            title = sanitize_filename(video_info.get('title', 'video'))
            file_exists = any(
                os.path.exists(os.path.join(download_path, f"{title}.{ext}"))
                for ext in ['mp4', 'mkv', 'webm']
            )

            if file_exists:
                print(f"⚠️  Skipping! Video already exists at directory: {title}")
                return

            # Set download options for the selected format
            ydl_opts = {
                'logger': MyLogger(),
                'quiet': True,
                'no_warnings': True,
                'format': f"{selected_format['format_id']}+bestaudio/best" if '+bestaudio' not in selected_format['format_id'] else selected_format['format_id'],
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'merge_output_format': 'mp4',  # Ensure merged file format
                'ignoreerrors': True,  # Skip bad videos
            }

            # Download the video with the selected format
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.download([url])

            if result == 0:
                print(f"✅ Download complete: {title}")
                print(f"📂  Saved to: {download_path}")
                return
            else:
                print("❌ Download failed.")

        except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
            if not handle_errors(e, attempt, retries):
                break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if not handle_errors(e, attempt, retries):
                break
        attempt += 1
    print(f"❌ Download failed after {retries} attempts.")

def main():
    """
    Main entry point for script.
    """
    video_url = input("Enter the YouTube video or playlist URL: ").strip()
    download_video(video_url)

if __name__ == "__main__":
    main()

# End of script. Enjoy downloading your videos! 🎥