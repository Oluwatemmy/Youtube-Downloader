import asyncio
import aiohttp
import aiofiles
import yt_dlp
import os
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import pickle
from pathlib import Path
import sys

try:
    from tqdm.asyncio import tqdm
except ImportError:
    tqdm = None

@dataclass
class VideoInfo:
    url: str
    title: str
    video_id: str
    formats: List[Dict]
    duration: int
    filesize_approx: int
    resolution: Optional[str] = None
    format_id: Optional[str] = None
    
@dataclass
class DownloadStats:
    total_videos: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        if self.total_videos == 0:
            return 0
        return (self.completed / self.total_videos) * 100

class MetadataCache:
    """Fast metadata caching system"""
    def __init__(self, cache_dir: str = ".yt_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "metadata.pkl"
        self.memory_cache: Dict[str, VideoInfo] = {}
        self._load_cache()
    
    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.memory_cache = pickle.load(f)
            except Exception:
                self.memory_cache = {}
    
    def _save_cache(self):
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.memory_cache, f)
    
    def get(self, video_id: str) -> Optional[VideoInfo]:
        return self.memory_cache.get(video_id)
    
    def set(self, video_id: str, info: VideoInfo):
        self.memory_cache[video_id] = info
        self._save_cache()

class DuplicateChecker:
    """Efficient duplicate checking using bloom filter concept"""
    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.downloaded_ids = set()
        self._scan_existing()
    
    def _scan_existing(self):
        """Scan existing files once at startup"""
        if self.download_dir.exists():
            for file in self.download_dir.rglob("*"):
                if file.is_file() and file.suffix in ['.mp4', '.mkv', '.webm']:
                    # Extract video ID from filename if possible
                    self.downloaded_ids.add(file.stem)
    
    def is_downloaded(self, video_id: str, title: str) -> bool:
        """Check if video is already downloaded"""
        clean_title = self._sanitize_filename(title)
        return (video_id in self.downloaded_ids or 
                clean_title in self.downloaded_ids or
                any(Path(self.download_dir / f"{clean_title}.{ext}").exists() 
                    for ext in ['mp4', 'mkv', 'webm']))
    
    def mark_downloaded(self, video_id: str, title: str):
        """Mark video as downloaded"""
        self.downloaded_ids.add(video_id)
        self.downloaded_ids.add(self._sanitize_filename(title))
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).strip()

class AsyncYoutubeDownloader:
    def __init__(self, download_dir: str = "downloads", max_concurrent: int = 10):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Performance components
        self.metadata_cache = MetadataCache()
        self.duplicate_checker = DuplicateChecker(download_dir)
        self.stats = DownloadStats()
        
        # Shared yt-dlp instance with optimized settings
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'concurrent_fragment_downloads': 5,
            'buffersize': 1024 * 1024,  # 1MB buffer
            'http_chunk_size': 1024 * 1024,  # 1MB chunks
        }
        
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Progress tracking
        self.progress_bars: Dict[str, Any] = {}
    
    async def extract_info(self, url: str) -> Optional[VideoInfo]:
        """Extract video info with caching"""
        # Try to get video ID from URL for cache lookup
        video_id = self._extract_video_id(url)
        
        if video_id:
            cached = self.metadata_cache.get(video_id)
            if cached:
                return cached
        
        # Extract info in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL({**self.ydl_opts, 'skip_download': True}) as ydl:
                info = await loop.run_in_executor(
                    self.thread_pool, 
                    ydl.extract_info, 
                    url, 
                    False
                )
            
            if info:
                video_info = VideoInfo(
                    url=url,
                    title=info.get('title', 'Unknown'),
                    video_id=info.get('id', ''),
                    formats=info.get('formats', []),
                    duration=info.get('duration', 0),
                    filesize_approx=info.get('filesize_approx', 0)
                )
                
                # Cache the metadata
                if video_id:
                    self.metadata_cache.set(video_id, video_info)
                
                return video_info
        except Exception as e:
            print(f"❌ Error extracting info for {url}: {e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _select_best_format(self, formats: List[Dict], target_resolution: Optional[str] = None) -> Dict:
        """Intelligently select best format"""
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        
        if not video_formats:
            return formats[0] if formats else {}
        
        # Sort by quality metrics
        def quality_score(f):
            height = f.get('height', 0) or 0
            fps = f.get('fps', 30) or 30
            bitrate = f.get('tbr', 0) or 0
            return (height * fps) + (bitrate / 1000)
        
        video_formats.sort(key=quality_score, reverse=True)
        
        if target_resolution:
            # Find closest match to target
            for f in video_formats:
                if f.get('format_note') == target_resolution or f.get('height') == int(target_resolution.rstrip('p')):
                    return f
        
        # Return highest quality
        return video_formats[0]
    
    async def download_video(self, url: str, video_info: Optional[VideoInfo] = None) -> Tuple[bool, str]:
        """Download a single video with optimizations"""
        async with self.semaphore:
            try:
                # Get video info if not provided
                if not video_info:
                    video_info = await self.extract_info(url)
                    if not video_info:
                        return False, "Failed to extract video info"
                
                # Check for duplicates
                if self.duplicate_checker.is_downloaded(video_info.video_id, video_info.title):
                    self.stats.skipped += 1
                    return True, f"Already downloaded: {video_info.title}"
                
                # Select best format
                best_format = self._select_best_format(video_info.formats)
                if not best_format:
                    return False, "No suitable format found"
                
                # Prepare download options
                output_path = self.download_dir / f"{self.duplicate_checker._sanitize_filename(video_info.title)}.%(ext)s"
                
                download_opts = {
                    **self.ydl_opts,
                    'format': f"{best_format['format_id']}+bestaudio/best",
                    'outtmpl': str(output_path),
                    'progress_hooks': [self._create_progress_hook(video_info.video_id)],
                    'merge_output_format': 'mp4',
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }],
                    'concurrent_fragment_downloads': 5,
                    'throttledratelimit': 1000000,  # 1MB/s minimum speed
                }
                
                # Download in thread pool
                loop = asyncio.get_event_loop()
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    result = await loop.run_in_executor(
                        self.thread_pool,
                        ydl.download,
                        [url]
                    )
                
                if result == 0:
                    self.stats.completed += 1
                    self.stats.total_bytes += best_format.get('filesize', 0) or best_format.get('filesize_approx', 0) or 0
                    self.duplicate_checker.mark_downloaded(video_info.video_id, video_info.title)
                    return True, f"Successfully downloaded: {video_info.title}"
                else:
                    self.stats.failed += 1
                    return False, "Download failed"
                    
            except Exception as e:
                self.stats.failed += 1
                return False, f"Error: {str(e)}"
    
    def _create_progress_hook(self, video_id: str):
        """Create progress hook for video"""
        def hook(d):
            if d['status'] == 'downloading':
                if tqdm and video_id not in self.progress_bars:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total > 0:
                        self.progress_bars[video_id] = tqdm(
                            total=total,
                            unit='iB',
                            unit_scale=True,
                            desc=f"Video {video_id[:8]}",
                            leave=False
                        )
                
                if video_id in self.progress_bars:
                    downloaded = d.get('downloaded_bytes', 0)
                    self.progress_bars[video_id].update(downloaded - self.progress_bars[video_id].n)
            
            elif d['status'] == 'finished' and video_id in self.progress_bars:
                self.progress_bars[video_id].close()
                del self.progress_bars[video_id]
        
        return hook
    
    async def download_batch(self, urls: List[str], target_resolution: Optional[str] = None) -> None:
        """Download multiple videos with maximum concurrency"""
        self.stats.total_videos = len(urls)
        self.stats.start_time = time.time()
        
        print(f"🚀 Starting batch download of {len(urls)} videos")
        print(f"⚡ Max concurrent downloads: {self.max_concurrent}")
        
        # Pre-fetch all metadata in parallel
        print("📊 Pre-fetching video metadata...")
        metadata_tasks = [self.extract_info(url) for url in urls]
        video_infos = await asyncio.gather(*metadata_tasks, return_exceptions=True)
        
        # Filter out failed extractions
        valid_downloads = [
            (url, info) for url, info in zip(urls, video_infos) 
            if isinstance(info, VideoInfo)
        ]
        
        print(f"✅ Metadata fetched for {len(valid_downloads)}/{len(urls)} videos")
        
        # Download all videos concurrently
        download_tasks = [
            self.download_video(url, info) 
            for url, info in valid_downloads
        ]
        
        if tqdm:
            # Overall progress bar
            overall_progress = tqdm(
                total=len(valid_downloads),
                desc="Overall Progress",
                unit="videos"
            )
        
        results = []
        for coro in asyncio.as_completed(download_tasks):
            success, message = await coro
            results.append((success, message))
            
            if tqdm:
                overall_progress.update(1)
            
            # Print result
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        
        if tqdm:
            overall_progress.close()
        
        # Print statistics
        self._print_stats()
    
    def _print_stats(self):
        """Print download statistics"""
        elapsed = time.time() - self.stats.start_time
        
        print("\n" + "="*60)
        print("📊 DOWNLOAD STATISTICS")
        print("="*60)
        print(f"✅ Completed: {self.stats.completed}")
        print(f"⏭️  Skipped: {self.stats.skipped}")
        print(f"❌ Failed: {self.stats.failed}")
        print(f"📊 Total: {self.stats.total_videos}")
        print(f"🎯 Success Rate: {self.stats.success_rate:.1f}%")
        print(f"💾 Total Downloaded: {self._format_bytes(self.stats.total_bytes)}")
        print(f"⏱️  Time Elapsed: {elapsed:.1f} seconds")
        print(f"⚡ Average Speed: {self._format_bytes(self.stats.total_bytes / elapsed)}/s")
        print("="*60)
    
    @staticmethod
    def _format_bytes(bytes: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024
        return f"{bytes:.2f} TB"
    
    async def close(self):
        """Cleanup resources"""
        self.thread_pool.shutdown(wait=True)
        for pb in self.progress_bars.values():
            pb.close()

async def main():
    """Example usage"""
    print("🎥 YouTube Async Downloader - High Performance Edition")
    print("="*60)
    
    # Example URLs
    urls = [
        # Add your URLs here
    ]
    
    downloader = AsyncYoutubeDownloader(max_concurrent=20)
    
    try:
        # Single video download
        if len(urls) == 1:
            success, message = await downloader.download_video(urls[0])
            print(message)
        else:
            # Batch download
            await downloader.download_batch(urls)
    finally:
        await downloader.close()

if __name__ == "__main__":
    # Check for required dependencies
    try:
        import aiohttp
        import aiofiles
    except ImportError:
        print("❌ Missing required dependencies. Please install:")
        print("pip install aiohttp aiofiles tqdm")
        sys.exit(1)
    
    asyncio.run(main())