#!/usr/bin/env python3
"""
Standalone YouTube Downloader - Windows-safe launcher
No Unicode characters to avoid encoding issues on Windows console
"""

import sys
import os
import threading
import time
import webbrowser
from pathlib import Path

# Add current directory to path for bundled files
if hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller bundle
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
else:
    # Running as script
    bundle_dir = Path(__file__).parent
    sys.path.insert(0, str(bundle_dir))

class YouTubeDownloaderLauncher:
    """Main launcher class with fallback options"""
    
    def __init__(self):
        self.gui_available = False
        self.web_available = False
        self.enhanced_cli_available = False
        
        self.check_capabilities()
    
    def safe_print(self, message):
        """Print message safely, handling encoding issues"""
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback to ASCII-safe version
            safe_message = message.encode('ascii', 'replace').decode('ascii')
            print(safe_message)
    
    def check_capabilities(self):
        """Check what UI options are available"""
        
        # Check GUI (tkinter)
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.destroy()
            self.gui_available = True
            self.safe_print("[OK] Desktop GUI available")
        except Exception as e:
            self.safe_print(f"[SKIP] Desktop GUI not available: {e}")
        
        # Check Web interface (Flask)
        try:
            import flask
            self.web_available = True
            self.safe_print("[OK] Web interface available")
        except ImportError:
            try:
                import subprocess
                self.safe_print("[INFO] Installing Flask for web interface...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
                import flask
                self.web_available = True
                self.safe_print("[OK] Web interface available (Flask installed)")
            except Exception as e:
                self.safe_print(f"[SKIP] Web interface not available: {e}")
        
        # Check enhanced CLI
        try:
            from yt_dlp_enhanced import OptimizedYoutubeDownloader
            self.enhanced_cli_available = True
            self.safe_print("[OK] Enhanced CLI available")
        except Exception as e:
            self.safe_print(f"[SKIP] Enhanced CLI not available: {e}")
    
    def show_menu(self):
        """Show interactive menu"""
        # Try to get version info
        version = "Unknown"
        try:
            from version import get_version
            version = get_version()
        except ImportError:
            pass
        
        self.safe_print("\n" + "=" * 60)
        self.safe_print(f"YouTube Downloader Pro v{version} - Standalone Edition")
        self.safe_print("=" * 60)
        
        options = []
        
        if self.gui_available:
            options.append(("1", "Desktop GUI (Recommended)", self.launch_gui))
        
        if self.web_available:
            options.append((str(len(options) + 1), "Web Interface", self.launch_web))
        
        if self.enhanced_cli_available:
            options.append((str(len(options) + 1), "Enhanced CLI", self.launch_enhanced_cli))
        
        # Always available basic CLI
        options.append((str(len(options) + 1), "Basic CLI", self.launch_basic_cli))
        
        if not options:
            self.safe_print("ERROR: No interface options available!")
            self.safe_print("Please ensure Python and required dependencies are installed.")
            input("Press Enter to exit...")
            return
        
        self.safe_print("\nAvailable interfaces:")
        for key, description, _ in options:
            self.safe_print(f"  {key}. {description}")
        
        self.safe_print(f"  {len(options) + 1}. Exit")
        
        while True:
            try:
                choice = input(f"\nSelect option (1-{len(options) + 1}): ").strip()
                
                if choice == str(len(options) + 1):
                    self.safe_print("Goodbye!")
                    return
                
                for key, _, func in options:
                    if choice == key:
                        func()
                        return
                
                self.safe_print("ERROR: Invalid choice. Please try again.")
            
            except KeyboardInterrupt:
                self.safe_print("\n\nGoodbye!")
                return
            except Exception as e:
                self.safe_print(f"ERROR: {e}")
    
    def launch_gui(self):
        """Launch desktop GUI"""
        try:
            self.safe_print("\nLaunching Desktop GUI...")
            
            # Import and run GUI
            if hasattr(sys, '_MEIPASS'):
                # Running from executable - import from bundle
                sys.path.insert(0, sys._MEIPASS)
            
            from youtube_downloader_gui import main
            main()
            
        except Exception as e:
            self.safe_print(f"ERROR: Failed to launch GUI: {e}")
            self.safe_print("Falling back to web interface...")
            if self.web_available:
                self.launch_web()
            else:
                input("Press Enter to exit...")
    
    def launch_web(self):
        """Launch web interface"""
        try:
            self.safe_print("\nLaunching Web Interface...")
            self.safe_print("The interface will open in your default browser.")
            self.safe_print("If it doesn't open automatically, visit: http://127.0.0.1:5000")
            self.safe_print("Press Ctrl+C to stop the server.\n")
            
            # Import and run web interface
            if hasattr(sys, '_MEIPASS'):
                sys.path.insert(0, sys._MEIPASS)
            
            from youtube_downloader_web import main
            main()
            
        except KeyboardInterrupt:
            self.safe_print("\n\nServer stopped by user")
        except Exception as e:
            self.safe_print(f"ERROR: Failed to launch web interface: {e}")
            self.safe_print("Falling back to CLI...")
            if self.enhanced_cli_available:
                self.launch_enhanced_cli()
            else:
                self.launch_basic_cli()
    
    def launch_enhanced_cli(self):
        """Launch enhanced CLI"""
        try:
            self.safe_print("\nLaunching Enhanced CLI...")
            
            if hasattr(sys, '_MEIPASS'):
                sys.path.insert(0, sys._MEIPASS)
            
            from yt_dlp_enhanced import interactive_mode
            import asyncio
            asyncio.run(interactive_mode())
            
        except Exception as e:
            self.safe_print(f"ERROR: Failed to launch enhanced CLI: {e}")
            self.safe_print("Falling back to basic CLI...")
            self.launch_basic_cli()
    
    def launch_basic_cli(self):
        """Launch basic CLI as last resort"""
        self.safe_print("\nBasic CLI Mode")
        self.safe_print("=" * 40)
        
        try:
            import yt_dlp
            
            while True:
                url = input("\nEnter YouTube URL (or 'quit' to exit): ").strip()
                
                if url.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not url:
                    continue
                
                if 'youtube.com' not in url and 'youtu.be' not in url:
                    self.safe_print("ERROR: Please enter a valid YouTube URL")
                    continue
                
                # Simple download
                try:
                    self.safe_print(f"Downloading: {url}")
                    
                    # Create downloads directory
                    download_dir = Path.home() / "Downloads" / "YouTube"
                    download_dir.mkdir(parents=True, exist_ok=True)
                    
                    ydl_opts = {
                        'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                        'format': 'best[height<=720]'  # Limit to 720p for compatibility
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    
                    self.safe_print(f"SUCCESS: Download completed! Saved to: {download_dir}")
                    
                except Exception as e:
                    self.safe_print(f"ERROR: Download failed: {e}")
        
        except ImportError:
            self.safe_print("ERROR: yt-dlp not available. Please install dependencies.")
        except KeyboardInterrupt:
            self.safe_print("\n\nGoodbye!")
        except Exception as e:
            self.safe_print(f"ERROR: {e}")
        
        input("\nPress Enter to exit...")

def main():
    """Main entry point"""
    try:
        launcher = YouTubeDownloaderLauncher()
        
        # Auto-launch best available option if no args
        if len(sys.argv) == 1:
            if launcher.gui_available:
                launcher.launch_gui()
            elif launcher.web_available:
                launcher.launch_web()
            else:
                launcher.show_menu()
        else:
            # Handle command line arguments
            arg = sys.argv[1].lower()
            if arg in ['gui', 'desktop']:
                if launcher.gui_available:
                    launcher.launch_gui()
                else:
                    launcher.safe_print("ERROR: Desktop GUI not available")
                    launcher.show_menu()
            elif arg in ['web', 'browser']:
                if launcher.web_available:
                    launcher.launch_web()
                else:
                    launcher.safe_print("ERROR: Web interface not available")
                    launcher.show_menu()
            elif arg in ['cli', 'terminal']:
                if launcher.enhanced_cli_available:
                    launcher.launch_enhanced_cli()
                else:
                    launcher.launch_basic_cli()
            else:
                launcher.show_menu()
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()