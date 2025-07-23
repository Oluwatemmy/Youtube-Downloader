import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional
import webbrowser

# Import our enhanced downloader
sys.path.insert(0, str(Path(__file__).parent))
from yt_dlp_enhanced import OptimizedYoutubeDownloader

class DownloadItem:
    """Represents a download item in the queue"""
    def __init__(self, url: str, title: str = "Unknown", status: str = "Pending"):
        self.url = url
        self.title = title
        self.status = status
        self.progress = 0
        self.speed = ""
        self.eta = ""
        self.size = ""
        self.error = ""

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.geometry("900x700")
        
        # Set icon (if available)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Variables
        self.download_dir = tk.StringVar(value=str(Path.home() / "Downloads" / "YouTube"))
        self.max_concurrent = tk.IntVar(value=3)
        self.video_quality = tk.StringVar(value="best")
        self.save_descriptions = tk.BooleanVar(value=False)
        self.download_queue = []
        self.is_downloading = False
        self.message_queue = queue.Queue()
        
        # Create UI
        self.create_widgets()
        
        # Start message processor
        self.process_messages()
        
        # Load settings
        self.load_settings()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="YouTube Downloader Pro", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # URL Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Add Videos", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="URL(s):").grid(row=0, column=0, sticky=tk.W)
        
        # URL text widget for multiple URLs
        self.url_text = scrolledtext.ScrolledText(input_frame, height=3, width=50)
        self.url_text.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.url_text.insert("1.0", "Enter YouTube URLs (one per line) or playlist URL")
        self.url_text.bind("<FocusIn>", self.on_url_focus)
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=2, sticky=(tk.N, tk.S))
        
        self.add_button = ttk.Button(button_frame, text="Add to Queue", 
                                    command=self.add_to_queue)
        self.add_button.pack(pady=2)
        
        self.paste_button = ttk.Button(button_frame, text="Paste", 
                                      command=self.paste_urls)
        self.paste_button.pack(pady=2)
        
        self.clear_button = ttk.Button(button_frame, text="Clear", 
                                      command=lambda: self.url_text.delete("1.0", tk.END))
        self.clear_button.pack(pady=2)
        
        # Settings Section
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        # Download directory
        ttk.Label(settings_frame, text="Download Directory:").grid(row=0, column=0, sticky=tk.W)
        dir_entry = ttk.Entry(settings_frame, textvariable=self.download_dir)
        dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(settings_frame, text="Browse", 
                  command=self.browse_directory).grid(row=0, column=2)
        
        # Quality selection
        ttk.Label(settings_frame, text="Video Quality:").grid(row=1, column=0, sticky=tk.W, pady=5)
        quality_combo = ttk.Combobox(settings_frame, textvariable=self.video_quality, 
                                    values=["best", "1080p", "720p", "480p", "360p"], 
                                    state="readonly", width=15)
        quality_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Concurrent downloads
        ttk.Label(settings_frame, text="Concurrent Downloads:").grid(row=1, column=1, sticky=tk.E, padx=(50, 5))
        concurrent_spin = ttk.Spinbox(settings_frame, from_=1, to=10, 
                                     textvariable=self.max_concurrent, width=10)
        concurrent_spin.grid(row=1, column=2, pady=5)
        
        # Save descriptions checkbox
        desc_check = ttk.Checkbutton(settings_frame, text="Save video descriptions", 
                                    variable=self.save_descriptions)
        desc_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Download Queue Section
        queue_frame = ttk.LabelFrame(main_frame, text="Download Queue", padding="10")
        queue_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Queue Treeview
        columns = ('Title', 'Status', 'Progress', 'Speed', 'Size')
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show='tree headings', height=10)
        
        # Column configuration
        self.queue_tree.column('#0', width=0, stretch=False)
        self.queue_tree.column('Title', width=300)
        self.queue_tree.column('Status', width=100)
        self.queue_tree.column('Progress', width=100)
        self.queue_tree.column('Speed', width=100)
        self.queue_tree.column('Size', width=100)
        
        # Headings
        self.queue_tree.heading('Title', text='Title')
        self.queue_tree.heading('Status', text='Status')
        self.queue_tree.heading('Progress', text='Progress')
        self.queue_tree.heading('Speed', text='Speed')
        self.queue_tree.heading('Size', text='Size')
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        h_scroll = ttk.Scrollbar(queue_frame, orient=tk.HORIZONTAL, command=self.queue_tree.xview)
        self.queue_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Queue control buttons
        queue_btn_frame = ttk.Frame(queue_frame)
        queue_btn_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.download_button = ttk.Button(queue_btn_frame, text="Start Download", 
                                         command=self.start_download, style='Accent.TButton')
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(queue_btn_frame, text="Stop", 
                                     command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_completed_button = ttk.Button(queue_btn_frame, text="Clear Completed", 
                                               command=self.clear_completed)
        self.clear_completed_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_all_button = ttk.Button(queue_btn_frame, text="Clear All", 
                                         command=self.clear_all)
        self.clear_all_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                          maximum=100, mode='determinate')
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Configure row weights
        main_frame.rowconfigure(3, weight=1)
        
    def on_url_focus(self, event):
        """Clear placeholder text when focused"""
        if self.url_text.get("1.0", "end-1c") == "Enter YouTube URLs (one per line) or playlist URL":
            self.url_text.delete("1.0", tk.END)
    
    def paste_urls(self):
        """Paste URLs from clipboard"""
        try:
            clipboard = self.root.clipboard_get()
            self.url_text.delete("1.0", tk.END)
            self.url_text.insert("1.0", clipboard)
        except:
            pass
    
    def browse_directory(self):
        """Browse for download directory"""
        directory = filedialog.askdirectory(initialdir=self.download_dir.get())
        if directory:
            self.download_dir.set(directory)
            self.save_settings()
    
    def add_to_queue(self):
        """Add URLs to download queue"""
        urls_text = self.url_text.get("1.0", tk.END).strip()
        if not urls_text or urls_text == "Enter YouTube URLs (one per line) or playlist URL":
            messagebox.showwarning("No URLs", "Please enter at least one YouTube URL")
            return
        
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        for url in urls:
            if any(domain in url for domain in ['youtube.com', 'youtu.be']):
                # Add to queue
                item = DownloadItem(url)
                self.download_queue.append(item)
                
                # Add to tree
                self.queue_tree.insert('', 'end', values=(item.title, item.status, 
                                                         "0%", "", ""))
        
        self.url_text.delete("1.0", tk.END)
        self.status_var.set(f"Added {len(urls)} items to queue")
    
    def start_download(self):
        """Start downloading queued items"""
        if self.is_downloading:
            messagebox.showinfo("Already Downloading", "Downloads are already in progress")
            return
        
        if not self.download_queue:
            messagebox.showwarning("Empty Queue", "No items in download queue")
            return
        
        # Update UI
        self.is_downloading = True
        self.download_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Start download thread
        download_thread = threading.Thread(target=self.download_worker, daemon=True)
        download_thread.start()
    
    def download_worker(self):
        """Worker thread for downloads"""
        try:
            # Create download directory
            Path(self.download_dir.get()).mkdir(parents=True, exist_ok=True)
            
            # Get pending items
            pending_items = [item for item in self.download_queue if item.status == "Pending"]
            
            if not pending_items:
                self.message_queue.put(("info", "No pending items to download"))
                return
            
            # Update status
            self.message_queue.put(("status", f"Downloading {len(pending_items)} items..."))
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create downloader
            downloader = OptimizedYoutubeDownloader(
                download_dir=self.download_dir.get(),
                max_concurrent=self.max_concurrent.get()
            )
            
            # Download each item
            for i, item in enumerate(pending_items):
                if not self.is_downloading:
                    break
                
                # Update item status
                item.status = "Downloading"
                self.update_queue_item(item)
                
                # Download
                try:
                    success, message = loop.run_until_complete(
                        downloader.download_video_optimized(item.url)
                    )
                    
                    if success:
                        item.status = "Completed"
                        item.progress = 100
                    else:
                        item.status = "Failed"
                        item.error = message
                    
                except Exception as e:
                    item.status = "Failed"
                    item.error = str(e)
                
                # Update UI
                self.update_queue_item(item)
                self.message_queue.put(("progress", (i + 1) / len(pending_items) * 100))
            
            # Cleanup
            downloader.cleanup()
            loop.close()
            
            # Final status
            completed = sum(1 for item in self.download_queue if item.status == "Completed")
            failed = sum(1 for item in self.download_queue if item.status == "Failed")
            self.message_queue.put(("status", f"Completed: {completed}, Failed: {failed}"))
            
        except Exception as e:
            self.message_queue.put(("error", f"Download error: {str(e)}"))
        finally:
            self.is_downloading = False
            self.message_queue.put(("download_complete", None))
    
    def update_queue_item(self, item: DownloadItem):
        """Update item in queue tree"""
        # Find item in tree
        for child in self.queue_tree.get_children():
            values = list(self.queue_tree.item(child)['values'])
            if values[0] == item.title or values[0] == "Unknown":
                # Update values
                self.queue_tree.item(child, values=(
                    item.title,
                    item.status,
                    f"{item.progress}%",
                    item.speed,
                    item.size
                ))
                break
    
    def stop_download(self):
        """Stop current downloads"""
        self.is_downloading = False
        self.status_var.set("Stopping downloads...")
    
    def clear_completed(self):
        """Clear completed items from queue"""
        # Remove from queue
        self.download_queue = [item for item in self.download_queue 
                             if item.status not in ["Completed", "Failed"]]
        
        # Remove from tree
        for child in self.queue_tree.get_children():
            values = self.queue_tree.item(child)['values']
            if values[1] in ["Completed", "Failed"]:
                self.queue_tree.delete(child)
    
    def clear_all(self):
        """Clear all items from queue"""
        if self.is_downloading:
            if not messagebox.askyesno("Clear All", 
                                     "Downloads are in progress. Clear anyway?"):
                return
        
        self.download_queue.clear()
        for child in self.queue_tree.get_children():
            self.queue_tree.delete(child)
        self.status_var.set("Queue cleared")
    
    def process_messages(self):
        """Process messages from worker thread"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(msg_data)
                elif msg_type == "progress":
                    self.progress_var.set(msg_data)
                elif msg_type == "info":
                    messagebox.showinfo("Information", msg_data)
                elif msg_type == "error":
                    messagebox.showerror("Error", msg_data)
                elif msg_type == "download_complete":
                    self.download_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.progress_var.set(0)
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_messages)
    
    def save_settings(self):
        """Save settings to file"""
        settings = {
            'download_dir': self.download_dir.get(),
            'max_concurrent': self.max_concurrent.get(),
            'video_quality': self.video_quality.get(),
            'save_descriptions': self.save_descriptions.get()
        }
        
        settings_file = Path.home() / '.youtube_downloader_settings.json'
        with open(settings_file, 'w') as f:
            json.dump(settings, f)
    
    def load_settings(self):
        """Load settings from file"""
        settings_file = Path.home() / '.youtube_downloader_settings.json'
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                self.download_dir.set(settings.get('download_dir', self.download_dir.get()))
                self.max_concurrent.set(settings.get('max_concurrent', 3))
                self.video_quality.set(settings.get('video_quality', 'best'))
                self.save_descriptions.set(settings.get('save_descriptions', False))
            except:
                pass

def main():
    """Main application entry point"""
    root = tk.Tk()
    
    # Set DPI awareness for Windows
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    
    app = YouTubeDownloaderGUI(root)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()