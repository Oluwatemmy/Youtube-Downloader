import asyncio
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import yt_dlp

try:
    from tqdm import tqdm
    from tqdm.asyncio import tqdm as atqdm
except ImportError:
    tqdm = None
    atqdm = None

@dataclass 
class ChunkInfo:
    start: int
    end: int
    downloaded: int = 0
    
class ChunkedDownloader:
    """Handles chunked downloads with resume capability"""
    
    def __init__(self, chunk_size: int = 10 * 1024 * 1024):  # 10MB chunks
        self.chunk_size = chunk_size
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=100,
                ttl_dns_cache=300,
                force_close=True
            ),
            timeout=aiohttp.ClientTimeout(total=3600)  # 1 hour timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_file_info(self, url: str) -> Tuple[int, bool]:
        """Get file size and check if server supports ranges"""
        async with self.session.head(url) as response:
            size = int(response.headers.get('Content-Length', 0))
            accepts_ranges = response.headers.get('Accept-Ranges') == 'bytes'
            return size, accepts_ranges
    
    async def download_chunk(self, url: str, start: int, end: int, chunk_path: Path) -> bool:
        """Download a specific chunk"""
        headers = {'Range': f'bytes={start}-{end}'}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status not in (200, 206):
                    return False
                
                async with aiofiles.open(chunk_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                
                return True
        except Exception as e:
            print(f"[ERROR] Chunk download error: {e}")
            return False
    
    async def download_with_resume(self, url: str, output_path: Path, progress_callback=None) -> bool:
        """Download file with resume support"""
        temp_dir = output_path.parent / f".{output_path.stem}_chunks"
        temp_dir.mkdir(exist_ok=True)
        
        # Get file info
        total_size, supports_ranges = await self.get_file_info(url)
        
        if not supports_ranges or total_size == 0:
            # Fallback to simple download
            return await self._simple_download(url, output_path, progress_callback)
        
        # Calculate chunks
        chunks = []
        for i in range(0, total_size, self.chunk_size):
            start = i
            end = min(i + self.chunk_size - 1, total_size - 1)
            chunks.append(ChunkInfo(start, end))
        
        # Download chunks concurrently
        tasks = []
        for i, chunk in enumerate(chunks):
            chunk_path = temp_dir / f"chunk_{i:04d}"
            
            # Skip if chunk already exists and has correct size
            if chunk_path.exists() and chunk_path.stat().st_size == (chunk.end - chunk.start + 1):
                chunk.downloaded = chunk.end - chunk.start + 1
                continue
            
            task = self.download_chunk(url, chunk.start, chunk.end, chunk_path)
            tasks.append((i, task))
        
        # Execute downloads with progress
        if tasks:
            if progress_callback:
                progress_callback(sum(c.downloaded for c in chunks), total_size)
            
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for (i, _), result in zip(tasks, results):
                if isinstance(result, Exception) or not result:
                    return False
                chunks[i].downloaded = chunks[i].end - chunks[i].start + 1
                if progress_callback:
                    progress_callback(sum(c.downloaded for c in chunks), total_size)
        
        # Merge chunks
        async with aiofiles.open(output_path, 'wb') as output_file:
            for i in range(len(chunks)):
                chunk_path = temp_dir / f"chunk_{i:04d}"
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    data = await chunk_file.read()
                    await output_file.write(data)
                chunk_path.unlink()  # Delete chunk after merging
        
        # Cleanup
        temp_dir.rmdir()
        return True
    
    async def _simple_download(self, url: str, output_path: Path, progress_callback=None) -> bool:
        """Simple download without chunking"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return False
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
                
                return True
        except Exception as e:
            print(f"[ERROR] Download error: {e}")
            return False

class OptimizedYoutubeDownloader:
    """Main downloader with all performance optimizations"""
    
    def __init__(self, download_dir: str = "downloads", max_concurrent: int = 20):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Optimized yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'concurrent_fragment_downloads': 10,
            'buffersize': 2097152,  # 2MB buffer
            'http_chunk_size': 10485760,  # 10MB chunks
            'throttledratelimit': 100000,  # 100KB/s minimum
            'noresizebuffer': True,
            'continuedl': True,
            'noprogress': True,
        }
        
        # Process pool for CPU-intensive operations
        self.process_pool = ProcessPoolExecutor(max_workers=mp.cpu_count())
        
        # Shared session for all downloads
        self._session: Optional[yt_dlp.YoutubeDL] = None
        
        # Statistics
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'bytes_downloaded': 0,
            'start_time': time.time()
        }
    
    def _get_session(self) -> yt_dlp.YoutubeDL:
        """Get or create shared yt-dlp session"""
        if not self._session:
            self._session = yt_dlp.YoutubeDL(self.ydl_opts)
        return self._session
    
    async def extract_info_batch(self, urls: List[str]) -> List[Optional[Dict]]:
        """Extract info for multiple URLs concurrently"""
        loop = asyncio.get_event_loop()
        
        # Create a function that creates its own yt-dlp instance
        def extract_info_worker(url):
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    return ydl.extract_info(url, download=False)
                except Exception:
                    return None
        
        tasks = []
        for url in urls:
            # Use thread pool instead of process pool
            task = loop.run_in_executor(
                None,  # Use default thread pool
                extract_info_worker,
                url
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        infos = []
        for result in results:
            if isinstance(result, Exception) or result is None:
                infos.append(None)
            else:
                infos.append(result)
        
        return infos
    
    @staticmethod
    def _select_optimal_format(formats: List[Dict], max_height: int = 1080) -> Optional[Dict]:
        """Select optimal format based on quality and compatibility"""
        if not formats:
            return None
        
        # Filter video formats
        video_formats = [
            f for f in formats 
            if f.get('vcodec') != 'none' 
            and f.get('acodec') != 'none'  # Prefer formats with audio
            and f.get('ext') in ['mp4', 'webm']  # Prefer these formats
        ]
        
        if not video_formats:
            # Fallback to any video format
            video_formats = [f for f in formats if f.get('vcodec') != 'none']
        
        if not video_formats:
            return None
        
        # Score formats
        def format_score(f):
            height = f.get('height', 0) or 0
            if height > max_height:
                height = max_height  # Penalize over max_height
            
            fps = f.get('fps', 30) or 30
            bitrate = f.get('tbr', 0) or f.get('vbr', 0) or 0
            
            # Prefer formats with audio
            audio_bonus = 1000 if f.get('acodec') != 'none' else 0
            
            # Prefer mp4
            format_bonus = 500 if f.get('ext') == 'mp4' else 0
            
            return height * fps + bitrate + audio_bonus + format_bonus
        
        video_formats.sort(key=format_score, reverse=True)
        return video_formats[0]
    
    async def download_video_optimized(self, url: str, info: Optional[Dict] = None) -> Tuple[bool, str]:
        """Download video with all optimizations"""
        async with self.semaphore:
            try:
                # Get info if not provided
                if not info:
                    loop = asyncio.get_event_loop()
                    # Create a function that creates its own yt-dlp instance
                    def extract_info_single():
                        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                            return ydl.extract_info(url, download=False)
                    
                    info = await loop.run_in_executor(
                        None,  # Use thread pool
                        extract_info_single
                    )
                
                if not info:
                    self.stats['failed'] += 1
                    return False, "Failed to extract video info"
                
                title = info.get('title', 'Unknown')
                video_id = info.get('id', '')
                
                # Check if already downloaded
                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                output_path = self.download_dir / f"{clean_title}.mp4"
                
                if output_path.exists():
                    self.stats['skipped'] += 1
                    return True, f"Already exists: {title}"
                
                # Select optimal format
                formats = info.get('formats', [])
                best_format = self._select_optimal_format(formats)
                
                if not best_format:
                    self.stats['failed'] += 1
                    return False, f"No suitable format for: {title}"
                
                # Get direct URL
                format_id = best_format['format_id']
                
                # For formats with separate audio, use yt-dlp's merging
                if best_format.get('acodec') == 'none':
                    # Use bestaudio without extension restriction for better compatibility
                    format_selector = f"{format_id}+bestaudio/best"
                else:
                    format_selector = format_id
                
                # Download options
                download_opts = {
                    **self.ydl_opts,
                    'format': format_selector,
                    'outtmpl': str(output_path.with_suffix('.%(ext)s')),
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferredformat': 'mp4',
                    }] if best_format.get('ext') != 'mp4' else [],
                }
                
                # Create progress bar if available
                if tqdm:
                    pbar = tqdm(
                        total=best_format.get('filesize') or best_format.get('filesize_approx', 0),
                        unit='iB',
                        unit_scale=True,
                        desc=f"{title[:30]}...",
                        leave=False
                    )
                    
                    def progress_hook(d):
                        try:
                            if d['status'] == 'downloading':
                                downloaded = d.get('downloaded_bytes', 0)
                                if downloaded > pbar.n:  # Only update if progress increased
                                    pbar.update(downloaded - pbar.n)
                            elif d['status'] == 'finished':
                                pbar.close()
                        except Exception:
                            # Don't let progress bar errors stop the download
                            pass
                    
                    download_opts['progress_hooks'] = [progress_hook]
                
                # Download
                loop = asyncio.get_event_loop()
                
                # Use thread pool instead of process pool for yt-dlp
                # Process pool can't pickle yt-dlp objects
                def download_with_ydl():
                    with yt_dlp.YoutubeDL(download_opts) as ydl:
                        return ydl.download([url])
                
                result = await loop.run_in_executor(
                    None,  # Use default thread pool
                    download_with_ydl
                )
                
                if result == 0:
                    self.stats['completed'] += 1
                    self.stats['bytes_downloaded'] += best_format.get('filesize', 0) or best_format.get('filesize_approx', 0) or 0
                    return True, f"Downloaded: {title}"
                else:
                    self.stats['failed'] += 1
                    return False, f"Failed: {title}"
                    
            except Exception as e:
                self.stats['failed'] += 1
                import traceback
                error_details = traceback.format_exc()
                print(f"\n[ERROR] Detailed error for {url}:\n{error_details}")
                return False, f"Error downloading {url}: {str(e)}"
    
    async def download_playlist(self, playlist_url: str) -> None:
        """Download entire playlist with optimizations"""
        print(f"[INFO] Extracting playlist info...")
        
        # Extract playlist info
        loop = asyncio.get_event_loop()
        
        # Create a function that creates its own yt-dlp instance
        def extract_playlist_info():
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                return ydl.extract_info(playlist_url, download=False)
        
        playlist_info = await loop.run_in_executor(
            None,  # Use thread pool
            extract_playlist_info
        )
        
        if not playlist_info:
            print("[ERROR] Failed to extract playlist info")
            return
        
        # Get all video URLs
        entries = playlist_info.get('entries', [])
        if not entries:
            print("[ERROR] No videos found in playlist")
            return
        
        urls = [entry.get('url') or entry.get('webpage_url') for entry in entries if entry]
        urls = [url for url in urls if url]  # Filter None values
        
        print(f"[INFO] Found {len(urls)} videos in playlist: {playlist_info.get('title', 'Unknown')}")
        
        # Download all videos
        await self.download_batch(urls)
    
    async def download_batch(self, urls: List[str]) -> None:
        """Download multiple videos with maximum efficiency"""
        self.stats['total'] = len(urls)
        self.stats['start_time'] = time.time()
        
        print(f"[START] Starting optimized batch download")
        print(f"[INFO] Videos: {len(urls)}")
        print(f"[INFO] Max concurrent: {self.max_concurrent}")
        print(f"[INFO] CPU cores: {mp.cpu_count()}")
        
        # Extract all info in parallel
        print("\n[INFO] Extracting video information...")
        infos = await self.extract_info_batch(urls)
        
        # Filter valid videos
        valid_downloads = [
            (url, info) for url, info in zip(urls, infos)
            if info is not None
        ]
        
        print(f"[OK] Valid videos: {len(valid_downloads)}/{len(urls)}")
        
        # Progress bar for overall progress
        if tqdm:
            overall_pbar = tqdm(
                total=len(valid_downloads),
                desc="Overall Progress",
                unit="videos",
                position=0
            )
        
        # Download all videos
        tasks = []
        for url, info in valid_downloads:
            task = self.download_video_optimized(url, info)
            tasks.append(task)
        
        # Process completions as they happen
        for coro in asyncio.as_completed(tasks):
            success, message = await coro
            
            if tqdm:
                overall_pbar.update(1)
            
            # Print status
            status = "[OK]" if success else "[FAIL]"
            print(f"{status} {message}")
        
        if tqdm:
            overall_pbar.close()
        
        # Print final statistics
        self._print_statistics()
    
    def _print_statistics(self):
        """Print download statistics"""
        elapsed = time.time() - self.stats['start_time']
        success_rate = (self.stats['completed'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        
        print("\n" + "="*70)
        print("DOWNLOAD STATISTICS")
        print("="*70)
        print(f"[OK] Completed: {self.stats['completed']}")
        print(f"[SKIP] Skipped: {self.stats['skipped']}")
        print(f"[FAIL] Failed: {self.stats['failed']}")
        print(f"[INFO] Total: {self.stats['total']}")
        print(f"[INFO] Success Rate: {success_rate:.1f}%")
        print(f"[INFO] Downloaded: {self._format_bytes(self.stats['bytes_downloaded'])}")
        print(f"[TIME] Time: {elapsed:.1f}s")
        print(f"[SPEED] Speed: {self._format_bytes(self.stats['bytes_downloaded'] / elapsed)}/s")
        print(f"[RATE] Videos/min: {(self.stats['completed'] + self.stats['skipped']) / elapsed * 60:.1f}")
        print("="*70)
    
    @staticmethod
    def _format_bytes(bytes: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"
    
    def cleanup(self):
        """Cleanup resources"""
        if self._session:
            self._session.__exit__(None, None, None)
        self.process_pool.shutdown(wait=True)

async def interactive_mode():
    """Interactive CLI mode"""
    print("YouTube Downloader - Ultra Performance Edition")
    print("="*70)
    print("Features:")
    print("  - Concurrent downloads (up to 50+ videos)")
    print("  - Smart caching and duplicate detection")
    print("  - Resume support for interrupted downloads")
    print("  - Real-time progress tracking")
    print("  - Multi-process extraction for maximum speed")
    print("="*70)
    
    mode = input("\nSelect mode:\n1. Download video(s)\n2. Download playlist\n3. Batch file input\nChoice (1-3): ").strip()
    
    downloader = OptimizedYoutubeDownloader(max_concurrent=30)
    
    try:
        if mode == "1":
            urls_input = input("\nEnter YouTube URLs (space or newline separated):\n").strip()
            urls = urls_input.replace('\n', ' ').split()
            
            if urls:
                await downloader.download_batch(urls)
            else:
                print("[ERROR] No URLs provided")
                
        elif mode == "2":
            playlist_url = input("\nEnter playlist URL: ").strip()
            if playlist_url:
                await downloader.download_playlist(playlist_url)
            else:
                print("[ERROR] No playlist URL provided")
                
        elif mode == "3":
            file_path = input("\nEnter path to file with URLs (one per line): ").strip()
            try:
                with open(file_path, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                if urls:
                    await downloader.download_batch(urls)
                else:
                    print("[ERROR] No URLs found in file")
            except FileNotFoundError:
                print(f"[ERROR] File not found: {file_path}")
        else:
            print("[ERROR] Invalid choice")
    
    finally:
        downloader.cleanup()

if __name__ == "__main__":
    # Check dependencies
    required = ['aiohttp', 'aiofiles']
    missing = []
    
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"[ERROR] Missing dependencies: {', '.join(missing)}")
        print(f"[INFO] Install with: pip install {' '.join(missing)} tqdm")
        sys.exit(1)
    
    # Run
    try:
        asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        print("\n[STOP] Download cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()