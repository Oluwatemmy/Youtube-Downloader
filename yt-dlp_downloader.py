import yt_dlp
import os
import time

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(f"❌ {msg}")

def download_video(url, retries=3):
    """
    Attempts to download a video with retries on failure.
    """
    attempt = 1
    while attempt <= retries:
        try:
            # Getting video info first to display file size
            video_info = get_video_info(url)
            if video_info:
                print(f"\nStarting download for: {video_info['title']}")
                print(f"Estimated file size: {format_size(video_info['filesize'])}")

            # Setting up download options
            download_path = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(download_path, exist_ok=True)

            ydl_opts = {
                'logger': MyLogger(),  # Suppress internal logs
                'quiet': True,  # Suppress extra information from yt-dlp
                'no_warnings': True, # Suppress warnings
                'format': 'best',
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            print(f"✅ Download complete: {video_info['title']}")
            print(f"📂  Saved to: {download_path}")
            return  # Exit the function if download is successful
        
        except yt_dlp.utils.DownloadError as e:
            print(f"❌ Download error: {e}")
            attempt += 1
            if attempt <= retries:
                print(f"Retrying... ({attempt}/{retries})")
            time.sleep(2)  # Retry after 2 seconds
        except yt_dlp.utils.ExtractorError as e:
            print(f"❌ Extractor error: {e}")
            attempt += 1
            if attempt <= retries:
                print(f"Retrying... ({attempt}/{retries})")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            attempt += 1
            if attempt <= retries:
                print(f"Retrying... ({attempt}/{retries})")
            time.sleep(2)  # Retry after 2 seconds
    
    print(f"❌ Download failed after {retries} attempts.")

def get_video_info(url):
    """
    Fetches video information (title, size) before downloading.
    """
    try:
        with yt_dlp.YoutubeDL() as ydl:
            result = ydl.extract_info(url, download=False)
            return {
                'title': result.get('title'),
                'filesize': result.get('filesize')
            }
    except Exception as e:
        print(f"❌ Error retrieving video info: {e}")
        return None

def format_size(size):
    """
    Converts bytes to a more readable format (KB, MB, GB).
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def progress_hook(d):
    """
    Updates the progress during the download.
    """
    if d['status'] == 'downloading':
        print(f"⬇️ Downloading: {d['_percent_str']} at {d['_speed_str']} ETA {d['_eta_str']}", end='\r')

def main():
    """
    Main function to initiate video download.
    """
    video_url = input("Enter the YouTube video URL: ").strip()
    download_video(video_url)

if __name__ == "__main__":
    main()
