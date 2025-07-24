# This script is designed to download videos from YouTube using yt-dlp with threading support.
# It includes progress display, duplicate checks, and concurrent downloads.
# The script is modular, with functions for creating download paths, formatting sizes, and handling errors.
# The script is intended for educational purposes and should be used in compliance with YouTube's terms of service.
# Always ensure you have permission to download content from YouTube before doing so.

import yt_dlp
import os, time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Target resolutions
TARGET_RESOLUTIONS = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]

# Thread-safe print function
print_lock = threading.Lock()

# Simple progress tracking for each thread
thread_progress = {}
progress_initialized = False


def thread_safe_print(*args, **kwargs):
    """Thread-safe print function to prevent garbled output."""
    with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()


def initialize_progress_display(max_workers):
    """Initialize progress display with placeholders for each thread."""
    global progress_initialized
    if not progress_initialized:
        print("\n" + "=" * 50)
        print("📊 DOWNLOAD PROGRESS")
        print("=" * 50)
        for i in range(1, max_workers + 1):
            thread_id = f"T{i}"
            print(f"⬇️  [{thread_id}] Waiting to start...")
            thread_progress[thread_id] = i - 1  # Store line position
        progress_initialized = True


def update_progress_line(thread_id, message):
    """Update progress for a specific thread on its dedicated line."""
    with print_lock:
        if thread_id in thread_progress:
            line_position = thread_progress[thread_id]
            # Move cursor up to the thread's line
            lines_up = len(thread_progress) - line_position
            if lines_up > 0:
                print(f"\033[{lines_up}A", end="")

            # Clear line and print new message
            print(f"\r{message:<90}", end="")

            # Move cursor back down
            if lines_up > 0:
                print(f"\033[{lines_up}B", end="")

            sys.stdout.flush()


def clear_progress_display():
    """Clear the progress display."""
    global progress_initialized, thread_progress
    with print_lock:
        if progress_initialized:
            # Simply move cursor to the end and add some newlines
            # This is safer than trying to clear specific lines
            print()  # Add a newline to separate from progress display

            thread_progress.clear()
            progress_initialized = False
            sys.stdout.flush()


class MyLogger:
    def __init__(self, thread_id=""):
        self.thread_id = thread_id

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        thread_safe_print(f"❌ [{self.thread_id}] {msg}")


def create_download_path(subfolder=None):
    """
    Creates and returns the download path with optional subfolder.
    """
    base_path = os.path.join(os.getcwd(), "downloads")

    if subfolder:
        download_path = os.path.join(base_path, sanitize_filename(subfolder))
    else:
        download_path = base_path

    os.makedirs(download_path, exist_ok=True)
    return download_path


def list_existing_folders():
    """
    List existing folders in the downloads directory.
    """
    downloads_path = os.path.join(os.getcwd(), "downloads")
    if not os.path.exists(downloads_path):
        return []

    folders = []
    for item in os.listdir(downloads_path):
        item_path = os.path.join(downloads_path, item)
        if os.path.isdir(item_path):
            folders.append(item)

    return sorted(folders)


def select_or_create_folder():
    """
    Allow user to select existing folder or create new one.
    """
    existing_folders = list_existing_folders()

    if existing_folders:
        print("\n📁 Existing folders in downloads:")
        for i, folder in enumerate(existing_folders, 1):
            print(f"  {i}. {folder}")
        print(f"  {len(existing_folders) + 1}. Create new folder")
        print(f"  {len(existing_folders) + 2}. Use main downloads folder")

        try:
            choice = int(
                input(f"\nChoose option (1-{len(existing_folders) + 2}): ").strip()
            )
            if 1 <= choice <= len(existing_folders):
                return existing_folders[choice - 1]
            elif choice == len(existing_folders) + 1:
                new_folder = input("Enter new folder name: ").strip()
                return new_folder if new_folder else None
            elif choice == len(existing_folders) + 2:
                return None
            else:
                print("❌ Invalid choice. Using main downloads folder.")
                return None
        except ValueError:
            print("❌ Invalid input. Using main downloads folder.")
            return None
    else:
        create_new = (
            input("No existing folders found. Create new folder? (y/n): ")
            .strip()
            .lower()
        )
        if create_new == "y":
            new_folder = input("Enter folder name: ").strip()
            return new_folder if new_folder else None
        return None


def save_video_description(video_info, download_path, filename_base):
    """
    Save video description to a text file.
    """
    try:
        description = video_info.get("description", "")
        if description:
            desc_filename = f"{filename_base}_description.txt"
            desc_path = os.path.join(download_path, desc_filename)

            with open(desc_path, "w", encoding="utf-8") as f:
                f.write(f"Title: {video_info.get('title', 'Unknown')}\n")
                f.write(f"URL: {video_info.get('webpage_url', 'Unknown')}\n")
                f.write(f"Uploader: {video_info.get('uploader', 'Unknown')}\n")
                f.write(f"Duration: {video_info.get('duration_string', 'Unknown')}\n")
                f.write(f"View Count: {video_info.get('view_count', 'Unknown')}\n")
                f.write(f"Upload Date: {video_info.get('upload_date', 'Unknown')}\n")
                f.write(f"Tags: {', '.join(video_info.get('tags', []))}\n")
                f.write("\n" + "=" * 60 + "\n")
                f.write("DESCRIPTION:\n")
                f.write("=" * 60 + "\n\n")
                f.write(description)

            return desc_path
    except Exception as e:
        thread_safe_print(f"⚠️  Could not save description: {e}")
    return None


def format_size(size):
    """
    Convert bytes to a human-readable format.
    """
    if size is None:
        return "Unknown size"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def sanitize_filename(name):
    """
    Clean file names from forbidden characters.
    """
    return "".join(c for c in name if c.isalnum() or c in (" ", ".", "_", "-")).strip()


def progress_hook_factory(thread_id):
    """
    Factory function to create thread-specific progress hooks.
    """

    def progress_hook(d):
        if d["status"] == "downloading":
            message = f"⬇️  [{thread_id}] Downloading: {d['_percent_str']} at {d['_speed_str']} ETA {d['_eta_str']}"
            update_progress_line(thread_id, message)

    return progress_hook


def handle_errors(e, attempt, retries, thread_id=""):
    """
    Handle and log errors based on type.
    """
    msg = str(e)
    if "ffmpeg" in msg.lower():
        update_progress_line(thread_id, f"❌ [{thread_id}] Missing ffmpeg dependency")
        return False
    if "getaddrinfo failed" in msg:
        update_progress_line(thread_id, f"❌ [{thread_id}] Network error")
    elif "HTTP Error 403" in msg:
        update_progress_line(thread_id, f"❌ [{thread_id}] Access denied")
    elif "HTTP Error 404" in msg:
        update_progress_line(thread_id, f"❌ [{thread_id}] Video not found")
    elif "Failed to extract" in msg:
        update_progress_line(thread_id, f"❌ [{thread_id}] Extraction error")
    else:
        update_progress_line(thread_id, f"❌ [{thread_id}] Download error")

    if attempt <= retries:
        update_progress_line(
            thread_id, f"🔄 [{thread_id}] Retrying... ({attempt}/{retries})"
        )
        time.sleep(2)  # Wait before retrying
        return True
    return False


def get_video_info(url, thread_id=""):
    """
    Fetch video or playlist info without downloading.
    """
    try:
        with yt_dlp.YoutubeDL(
            {"quiet": True, "no_warnings": True, "skip_download": True}
        ) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        thread_safe_print(f"❌ [{thread_id}] Error retrieving video info: {e}")
    return None


def download_video_threaded(
    url,
    format_choice=None,
    thread_id=None,
    retries=3,
    subfolder=None,
    save_description=False,
):
    """
    Downloads a single video with threading support.
    """
    if thread_id is None:
        thread_id = f"T{threading.current_thread().ident % 1000}"

    attempt = 1
    download_path = create_download_path(subfolder)

    # Update progress line to show we're starting
    update_progress_line(thread_id, f"⬇️  [{thread_id}] Getting video info...")

    while attempt <= retries:
        try:
            video_info = get_video_info(url, thread_id)
            if not video_info:
                update_progress_line(
                    thread_id, f"❌ [{thread_id}] Failed to get video info"
                )
                return False, f"Failed to get video info for {url}"

            title = video_info.get("title", "video")
            update_progress_line(
                thread_id, f"⬇️  [{thread_id}] Preparing: {title[:50]}..."
            )

            formats = video_info.get("formats", [])
            if not formats:
                update_progress_line(
                    thread_id, f"❌ [{thread_id}] No downloadable formats found"
                )
                return False, "No downloadable formats found"

            # Include all video formats (even video-only), and ignore audio-only
            filtered_formats = []
            for f in formats:
                resolution = f.get("format_note") or f.get("height")
                if f.get("vcodec") != "none" and resolution in TARGET_RESOLUTIONS:
                    if isinstance(resolution, int):
                        resolution = f"{resolution}p"
                    ext = f.get("ext")
                    filesize = f.get("filesize") or f.get("filesize_approx")

                    filtered_formats.append(
                        {
                            "format_id": f["format_id"],
                            "resolution": resolution or "Unknown",
                            "filesize": filesize,
                            "ext": ext,
                        }
                    )

            if not filtered_formats:
                update_progress_line(
                    thread_id, f"❌ [{thread_id}] No suitable formats found"
                )
                return False, "No suitable formats found"

            # Sort formats by resolution (best effort)
            filtered_formats.sort(
                key=lambda x: (
                    int(x["resolution"].replace("p", ""))
                    if x["resolution"].endswith("p")
                    else 0
                )
            )

            # Use provided format choice or default to highest quality
            if format_choice is None or format_choice >= len(filtered_formats):
                selected_format = filtered_formats[-1]  # Highest quality
            else:
                selected_format = filtered_formats[format_choice]

            resolution = selected_format.get("resolution")
            filesize = selected_format.get("filesize")

            # Check if file already exists
            title_clean = sanitize_filename(video_info.get("title", "video"))
            file_exists = any(
                os.path.exists(os.path.join(download_path, f"{title_clean}.{ext}"))
                for ext in ["mp4", "mkv", "webm"]
            )

            if file_exists:
                update_progress_line(
                    thread_id, f"⚠️  [{thread_id}] Already exists: {title[:50]}..."
                )
                return True, f"Video already exists: {title_clean}"

            # Save description if requested
            if save_description:
                save_video_description(video_info, download_path, title_clean)

            # Set download options for the selected format
            ydl_opts = {
                "logger": MyLogger(thread_id),
                "quiet": True,
                "no_warnings": True,
                "format": (
                    f"{selected_format['format_id']}+bestaudio/best"
                    if "+bestaudio" not in selected_format["format_id"]
                    else selected_format["format_id"]
                ),
                "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                "progress_hooks": [progress_hook_factory(thread_id)],
                "merge_output_format": "mp4",  # Ensure merged file format
                "ignoreerrors": True,  # Skip bad videos
            }

            # Download the video with the selected format
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.download([url])

            if result == 0:
                update_progress_line(
                    thread_id, f"✅ [{thread_id}] Complete: {title[:50]}..."
                )
                return True, f"Successfully downloaded: {title}"
            else:
                update_progress_line(thread_id, f"❌ [{thread_id}] Download failed")

        except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as e:
            update_progress_line(thread_id, f"❌ [{thread_id}] Error: {str(e)[:40]}...")
            if not handle_errors(e, attempt, retries, thread_id):
                break
        except Exception as e:
            update_progress_line(thread_id, f"❌ [{thread_id}] Unexpected error")
            if not handle_errors(e, attempt, retries, thread_id):
                break
        attempt += 1

    update_progress_line(thread_id, f"❌ [{thread_id}] Failed after {retries} attempts")
    return False, f"Download failed after {retries} attempts"


def download_video(url, retries=3, subfolder=None, save_description=False):
    """
    Downloads a single video (original function for backward compatibility).
    """
    attempt = 1
    download_path = create_download_path(subfolder)

    while attempt <= retries:
        try:
            video_info = get_video_info(url)
            if not video_info:
                return

            title = video_info.get("title", "video")
            print(f"\n🎬 Title: {title}\n")

            formats = video_info.get("formats", [])
            if not formats:
                print("❌ No downloadable formats found for this video.")
                return

            # Include all video formats (even video-only), and ignore audio-only
            filtered_formats = []
            for f in formats:
                resolution = f.get("format_note") or f.get("height")
                if f.get("vcodec") != "none" and resolution in TARGET_RESOLUTIONS:
                    if isinstance(resolution, int):
                        resolution = f"{resolution}p"
                    ext = f.get("ext")
                    filesize = f.get("filesize") or f.get("filesize_approx")

                    filtered_formats.append(
                        {
                            "format_id": f["format_id"],
                            "resolution": resolution or "Unknown",
                            "filesize": filesize,
                            "ext": ext,
                        }
                    )

            if not filtered_formats:
                print("❌ No suitable formats found for the specified resolutions.")
                return

            # Sort formats by resolution (best effort)
            filtered_formats.sort(
                key=lambda x: (
                    int(x["resolution"].replace("p", ""))
                    if x["resolution"].endswith("p")
                    else 0
                )
            )

            # Display available formats and file sizes
            print("\nAvailable video formats:")
            for i, fmt in enumerate(filtered_formats):
                filesize = fmt.get("filesize")
                print(
                    f"{i + 1}. {fmt['resolution']} - {format_size(filesize)} ({fmt['ext']})"
                )

            # Ask user to select format
            try:
                choice = int(
                    input(
                        f"\nChoose the format number (1-{len(filtered_formats)}): "
                    ).strip()
                )
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
                return
            if choice < 1 or choice > len(filtered_formats):
                print("❌ Invalid choice.")
                return

            selected_format = filtered_formats[choice - 1]
            resolution = selected_format.get("resolution")
            filesize = selected_format.get("filesize")
            print(f"\nSelected resolution: {resolution} - {format_size(filesize)}")

            # Check if file already exists
            title_clean = sanitize_filename(video_info.get("title", "video"))
            file_exists = any(
                os.path.exists(os.path.join(download_path, f"{title_clean}.{ext}"))
                for ext in ["mp4", "mkv", "webm"]
            )

            if file_exists:
                print(f"⚠️  Skipping! Video already exists at directory: {title_clean}")
                return

            # Save description if requested
            desc_path = None
            if save_description:
                desc_path = save_video_description(
                    video_info, download_path, title_clean
                )
                if desc_path:
                    print(f"📝 Description saved: {os.path.basename(desc_path)}")

            # Set download options for the selected format
            ydl_opts = {
                "logger": MyLogger(),
                "quiet": True,
                "no_warnings": True,
                "format": (
                    f"{selected_format['format_id']}+bestaudio/best"
                    if "+bestaudio" not in selected_format["format_id"]
                    else selected_format["format_id"]
                ),
                "outtmpl": os.path.join(download_path, "%(title)s.%(ext)s"),
                "progress_hooks": [progress_hook_factory("MAIN")],
                "merge_output_format": "mp4",  # Ensure merged file format
                "ignoreerrors": True,  # Skip bad videos
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


def download_multiple_videos(
    urls, max_workers=3, format_choice=None, subfolder=None, save_description=False
):
    """
    Download multiple videos concurrently using threading.

    Args:
        urls: List of YouTube URLs to download
        max_workers: Maximum number of concurrent downloads (default: 3)
        format_choice: Format index to use for all videos (None for auto-select highest quality)
        subfolder: Subfolder name within downloads directory
        save_description: Whether to save video descriptions as text files
    """
    if not urls:
        print("❌ No URLs provided.")
        return

    folder_info = f" in folder '{subfolder}'" if subfolder else ""
    print(
        f"🚀 Starting concurrent downloads with {max_workers} workers{folder_info}..."
    )
    print(f"📥 Total videos to download: {len(urls)}")
    if save_description:
        print("📝 Video descriptions will be saved as text files")

    # Initialize progress display
    initialize_progress_display(max_workers)

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        # For sequential processing (max_workers=1), we need to handle thread IDs differently
        if max_workers == 1:
            # Process videos one by one, reusing the same thread ID
            future_to_url = {}
            for i, url in enumerate(urls):
                future = executor.submit(
                    download_video_threaded,
                    url,
                    format_choice,
                    "T1",  # Always use T1 for sequential processing
                    3,
                    subfolder,
                    save_description,
                )
                future_to_url[future] = url
        else:
            # For concurrent processing, assign different thread IDs
            future_to_url = {
                executor.submit(
                    download_video_threaded,
                    url,
                    format_choice,
                    f"T{(i % max_workers) + 1}",  # Cycle through available thread IDs
                    3,
                    subfolder,
                    save_description,
                ): url
                for i, url in enumerate(urls)
            }

        # Process completed downloads
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                success, message = future.result()
                results.append((url, success, message))
            except Exception as exc:
                results.append((url, False, str(exc)))

    # Clear progress display after all downloads complete
    clear_progress_display()

    # Print summary
    successful = sum(1 for _, success, _ in results if success)
    failed = len(results) - successful

    print("\n" + "=" * 60)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(results)}")
    if subfolder:
        print(f"📁 Folder: {subfolder}")

    if failed > 0:
        print("\n❌ Failed downloads:")
        for url, success, message in results:
            if not success:
                print(f"  • {url}: {message}")


def main():
    """
    Main entry point for script with multi-threading options.
    """
    print("🎥 YouTube Video Downloader with Threading Support")
    print("=" * 50)

    mode = input(
        "Choose mode:\n1. Single video download\n2. Multiple videos download\nEnter choice (1 or 2): "
    ).strip()

    if mode == "1":
        video_url = input("Enter the YouTube video URL: ").strip()

        # Folder selection
        folder = select_or_create_folder()

        # Description option
        save_desc = (
            input("Save video description? (y/n, default n): ").strip().lower() == "y"
        )

        download_video(video_url, subfolder=folder, save_description=save_desc)

    elif mode == "2":
        print("\nEnter YouTube URLs (one per line, press Enter twice when done):")
        urls = []
        while True:
            url = input().strip()
            if not url:
                break
            urls.append(url)

        if not urls:
            print("❌ No URLs entered.")
            return

        # Folder selection
        folder = select_or_create_folder()

        try:
            max_workers = int(
                input(f"Enter max concurrent downloads (1-10, default 3): ").strip()
                or "3"
            )
            max_workers = max(1, min(10, max_workers))  # Clamp between 1-10
        except ValueError:
            max_workers = 3

        # Ask for format preference
        format_pref = (
            input("Use highest quality for all videos? (y/n, default y): ")
            .strip()
            .lower()
        )
        format_choice = (
            None if format_pref != "n" else 0
        )  # Use highest quality by default

        # Description option
        save_desc = (
            input("Save video descriptions? (y/n, default n): ").strip().lower() == "y"
        )

        download_multiple_videos(urls, max_workers, format_choice, folder, save_desc)

    else:
        print("❌ Invalid choice. Please run the script again.")


if __name__ == "__main__":
    main()
