import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import asyncio
import sys
import os
import warnings
from pathlib import Path
from datetime import datetime
import json
import re
from typing import List, Dict, Optional
import webbrowser
from urllib.parse import urlparse, parse_qs

# Suppress the pkg_resources deprecation warning
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Import our enhanced downloader
sys.path.insert(0, str(Path(__file__).parent))
try:
    from yt_dlp_enhanced import OptimizedYoutubeDownloader
    import yt_dlp
except ImportError as e:
    error_msg = "Required dependencies not found. Please install:\n\n"
    error_msg += "pip install yt-dlp aiohttp aiofiles tqdm\n\n"
    error_msg += "And ensure yt_dlp_enhanced.py is in the same directory."

    # Show error in GUI if possible, otherwise print
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Missing Dependencies", error_msg)
        root.destroy()
    except Exception:
        print(error_msg)
    sys.exit(1)


class VideoInfo:
    """Enhanced video information class"""

    def __init__(self, url: str, title: str = "Unknown", duration: str = "",
                 thumbnail: str = "", uploader: str = "", view_count: int = 0,
                 upload_date: str = "", description: str = "", format_info: str = "", status: str = "Pending"):
        self.url = url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.uploader = uploader
        self.view_count = view_count
        self.upload_date = upload_date
        self.description = description
        self.format_info = format_info
        self.status = status
        self.progress = 0
        self.speed = ""
        self.eta = ""
        self.size = ""
        self.error = ""
        self.file_path = ""
        self.tree_item_id = None  # Store reference to tree item


class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro - Enhanced")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # Set icon (if available)
        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass

        # Variables
        self.download_dir = tk.StringVar(value=str(Path.home() / "Downloads" / "YouTube"))
        self.max_concurrent = tk.IntVar(value=3)
        self.video_quality = tk.StringVar(value="best")
        self.save_descriptions = tk.BooleanVar(value=False)
        self.auto_load_info = tk.BooleanVar(value=True)

        # Data
        self.download_queue = []
        self.is_downloading = False
        self.is_loading_info = False
        self.message_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        # Analytics tracking with persistent storage
        self.analytics_file = Path.home() / '.youtube_downloader_analytics.json'
        self.analytics = self.load_analytics()

        # Current session tracking
        self.current_session = {
            'session_start': datetime.now().isoformat(),
            'downloads_this_session': 0,
            'data_this_session': 0
        }

        # Validation patterns
        self.youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)'
        ]

        # Create UI
        self.create_widgets()

        # Start message processors
        self.process_messages()
        self.process_progress()

        # Load settings
        self.load_settings()

    def create_widgets(self):
        """Create all GUI widgets with modern styling"""
        # Enhanced styling
        style = ttk.Style()

        # Try to use a modern theme
        try:
            style.theme_use('vista')  # Windows
        except Exception:
            try:
                style.theme_use('aqua')  # macOS
            except Exception:
                style.theme_use('clam')  # Fallback

        # Configure modern color scheme
        colors = {
            'bg': '#f0f0f0',
            'fg': '#333333',
            'select_bg': '#0078d4',
            'select_fg': '#ffffff',
            'accent': '#0078d4',
            'success': '#107c10',
            'warning': '#ff8c00',
            'error': '#d13438',
            'border': '#d1d1d1'
        }

        # Configure ONLY valid ttk styles
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=colors['accent'])
        style.configure('Heading.TLabel', font=('Segoe UI', 12, 'bold'), foreground=colors['fg'])
        style.configure('Modern.TButton', padding=(10, 5))

        # Configure button styles (these work reliably)
        try:
            style.map('Accent.TButton',
                      background=[('active', '#106ebe'), ('!active', colors['accent'])])
            style.map('Success.TButton',
                      background=[('active', '#0e6b0e'), ('!active', colors['success'])])
            style.map('Warning.TButton',
                      background=[('active', '#e67c00'), ('!active', colors['warning'])])
        except:
            pass

        # Entry styles
        try:
            style.configure('Valid.TEntry', fieldbackground='#e8f5e8', borderwidth=2)
            style.configure('Invalid.TEntry', fieldbackground='#ffe8e8', borderwidth=2)
        except:
            pass

        # Label styles
        style.configure('Success.TLabel', foreground=colors['success'], font=('Segoe UI', 9))
        style.configure('Error.TLabel', foreground=colors['error'], font=('Segoe UI', 9))
        style.configure('Info.TLabel', foreground=colors['accent'], font=('Segoe UI', 9))

        # Treeview styles
        try:
            style.configure('Modern.Treeview', rowheight=28)
            style.configure('Modern.Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        except:
            pass

        # Configure default LabelFrame with modern look
        try:
            style.configure('TLabelFrame',
                            padding=15,
                            borderwidth=1,
                            relief='solid',
                            background=colors['bg'])
            style.configure('TLabelFrame.Label',
                            font=('Segoe UI', 11, 'bold'),
                            foreground=colors['accent'])
        except:
            # Fallback to basic styling
            style.configure('TLabelFrame', padding=10)

        # Configure the root window
        self.root.configure(bg=colors['bg'])

        # Create main container with padding
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Modern header with app title and subtitle
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        title_label = ttk.Label(header_frame, text="🎬 YouTube Downloader Pro",
                                style='Title.TLabel')
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(header_frame, text="Enhanced Edition • Download videos with style and speed",
                                   font=('Segoe UI', 10), foreground='#666666')
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Create notebook with modern styling
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Style the notebook
        try:
            style.configure('TNotebook.Tab', padding=[20, 8], font=('Segoe UI', 10))
        except:
            pass

        # Main download tab
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="📥 Download")

        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")

        # Analytics tab
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="📊 Analytics")

        self.create_main_tab()
        self.create_settings_tab()
        self.create_analytics_tab()

    def create_main_tab(self):
        """Create main download tab with modern design"""
        main_frame = self.main_frame
        main_frame.configure(padding="20")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Make download queue expand

        # URL Input Section with modern card design
        input_card = ttk.LabelFrame(main_frame, text="🔗 Add Videos or Playlists", padding="20")
        input_card.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        input_card.columnconfigure(1, weight=1)

        # Single URL input with smart validation
        url_input_frame = ttk.Frame(input_card)
        url_input_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        url_input_frame.columnconfigure(1, weight=1)

        ttk.Label(url_input_frame, text="🎯 Quick Add:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0,
                                                                                            sticky=tk.W)

        # URL entry with modern styling
        self.url_entry = ttk.Entry(url_input_frame, width=60)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.url_entry.bind('<KeyRelease>', self.validate_url)
        self.url_entry.bind('<FocusOut>', self.on_url_focus_out)
        self.url_entry.bind('<Return>', lambda e: self.add_to_queue())

        # Add placeholder text
        self.url_entry.insert(0, "Paste YouTube URL here (video, playlist, or channel)")
        self.url_entry.bind('<FocusIn>', self.on_url_entry_focus)
        self.url_entry.configure(foreground='#999999')

        # Validation indicator with modern styling
        self.validation_label = ttk.Label(url_input_frame, text="", font=('Segoe UI', 9))
        self.validation_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))

        # Separator
        separator1 = ttk.Separator(input_card, orient='horizontal')
        separator1.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)

        # Multi-URL section
        ttk.Label(input_card, text="📝 Batch Add:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0,
                                                                                       sticky=(tk.N, tk.W))

        # Text widget with modern scrollbar
        text_frame = ttk.Frame(input_card)
        text_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.url_text = scrolledtext.ScrolledText(text_frame, height=4, width=50, wrap=tk.WORD)
        self.url_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.url_text.insert("1.0", "Enter multiple YouTube URLs (one per line)")
        self.url_text.bind("<FocusIn>", self.on_url_text_focus)
        self.url_text.configure(foreground='#999999')

        # Modern action buttons with icons
        button_frame = ttk.Frame(input_card)
        button_frame.grid(row=2, column=2, sticky=(tk.N, tk.S), padx=(15, 0))

        self.add_button = ttk.Button(button_frame, text="➕ Add to Queue",
                                     command=self.add_to_queue, width=15)
        self.add_button.pack(pady=(0, 8), fill=tk.X)

        self.paste_button = ttk.Button(button_frame, text="📋 Paste",
                                       command=self.paste_urls, width=15)
        self.paste_button.pack(pady=4, fill=tk.X)

        self.clear_button = ttk.Button(button_frame, text="🗑️ Clear",
                                       command=self.clear_inputs, width=15)
        self.clear_button.pack(pady=4, fill=tk.X)

        # Quick actions
        quick_frame = ttk.Frame(input_card)
        quick_frame.grid(row=3, column=1, sticky=tk.W, pady=(10, 0))

        self.auto_load_check = ttk.Checkbutton(quick_frame, text="🚀 Auto-load video info",
                                               variable=self.auto_load_info)
        self.auto_load_check.pack(side=tk.LEFT)

        # Download Queue Section with integrated progress overview
        queue_card = ttk.LabelFrame(main_frame, text="📋 Download Queue & Progress", padding="15")
        queue_card.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        queue_card.columnconfigure(0, weight=1)
        queue_card.rowconfigure(1, weight=1)  # Make the tree expand

        # Queue stats and progress header
        stats_frame = ttk.Frame(queue_card)
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        stats_frame.columnconfigure(1, weight=1)

        # Left side - Queue stats
        queue_info_frame = ttk.Frame(stats_frame)
        queue_info_frame.grid(row=0, column=0, sticky=tk.W)

        self.queue_stats_label = ttk.Label(queue_info_frame, text="📊 0 videos in queue",
                                           font=('Segoe UI', 10, 'bold'))
        self.queue_stats_label.pack(anchor=tk.W)

        # Queue filter buttons
        filter_frame = ttk.Frame(queue_info_frame)
        filter_frame.pack(anchor=tk.W, pady=(5, 0))

        ttk.Button(filter_frame, text="All", command=lambda: self.filter_queue("all"),
                   width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(filter_frame, text="Pending", command=lambda: self.filter_queue("pending"),
                   width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="Completed", command=lambda: self.filter_queue("completed"),
                   width=8).pack(side=tk.LEFT, padx=2)

        # Right side - Progress overview
        progress_overview_frame = ttk.Frame(stats_frame)
        progress_overview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(20, 0))
        progress_overview_frame.columnconfigure(1, weight=1)

        # Overall progress
        ttk.Label(progress_overview_frame, text="🌐 Overall Progress:",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)

        overall_frame = ttk.Frame(progress_overview_frame)
        overall_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        overall_frame.columnconfigure(0, weight=1)

        self.overall_progress_var = tk.DoubleVar()
        self.overall_progress_bar = ttk.Progressbar(overall_frame, variable=self.overall_progress_var,
                                                    maximum=100, mode='determinate', length=300)
        self.overall_progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.overall_progress_label = ttk.Label(overall_frame, text="0%",
                                                font=('Segoe UI', 9, 'bold'))
        self.overall_progress_label.grid(row=0, column=1, padx=(10, 0))

        # Current download progress
        ttk.Label(progress_overview_frame, text="⬇️ Current Download:",
                  font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(8, 0))

        current_frame = ttk.Frame(progress_overview_frame)
        current_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(8, 0))
        current_frame.columnconfigure(0, weight=1)

        self.current_progress_var = tk.DoubleVar()
        self.current_progress_bar = ttk.Progressbar(current_frame, variable=self.current_progress_var,
                                                    maximum=100, mode='determinate', length=300)
        self.current_progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))

        self.current_progress_label = ttk.Label(current_frame, text="0%",
                                                font=('Segoe UI', 9, 'bold'))
        self.current_progress_label.grid(row=0, column=1, padx=(10, 0))

        # Enhanced Queue Treeview with modern styling
        tree_frame = ttk.Frame(queue_card)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ('Status', 'Title', 'Duration', 'Uploader', 'Progress', 'Speed', 'ETA', 'Size')
        try:
            self.queue_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings',
                                           height=12, style='Modern.Treeview')
        except:
            self.queue_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=12)

        # Enhanced column configuration
        self.queue_tree.column('#0', width=0, stretch=False)
        self.queue_tree.column('Status', width=120, minwidth=100)
        self.queue_tree.column('Title', width=350, minwidth=200)
        self.queue_tree.column('Duration', width=80, minwidth=60)
        self.queue_tree.column('Uploader', width=150, minwidth=100)
        self.queue_tree.column('Progress', width=150, minwidth=120)
        self.queue_tree.column('Speed', width=100, minwidth=80)
        self.queue_tree.column('ETA', width=80, minwidth=60)
        self.queue_tree.column('Size', width=80, minwidth=60)

        # Modern headings with icons
        self.queue_tree.heading('Status', text='📊 Status')
        self.queue_tree.heading('Title', text='🎬 Title')
        self.queue_tree.heading('Duration', text='⏱️ Duration')
        self.queue_tree.heading('Uploader', text='👤 Uploader')
        self.queue_tree.heading('Progress', text='📈 Progress')
        self.queue_tree.heading('Speed', text='🚀 Speed')
        self.queue_tree.heading('ETA', text='⏰ ETA')
        self.queue_tree.heading('Size', text='💾 Size')

        # Modern scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.queue_tree.xview)
        self.queue_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Grid with proper spacing
        self.queue_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Context menu
        self.create_context_menu()

        # Modern control panel
        control_panel = ttk.Frame(queue_card)
        control_panel.grid(row=2, column=0, pady=(15, 0), sticky=(tk.W, tk.E))
        control_panel.columnconfigure(1, weight=1)

        # Primary action buttons
        primary_buttons = ttk.Frame(control_panel)
        primary_buttons.grid(row=0, column=0, sticky=tk.W)

        self.download_button = ttk.Button(primary_buttons, text="▶️ Start Download",
                                          command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=(0, 8))

        self.pause_button = ttk.Button(primary_buttons, text="⏸️ Pause",
                                       command=self.pause_download, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=4)

        self.stop_button = ttk.Button(primary_buttons, text="⏹️ Stop",
                                      command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=4)

        # Secondary action buttons
        secondary_buttons = ttk.Frame(control_panel)
        secondary_buttons.grid(row=0, column=1, sticky=tk.E)

        self.clear_completed_button = ttk.Button(secondary_buttons, text="✅ Clear Completed",
                                                 command=self.clear_completed)
        self.clear_completed_button.pack(side=tk.LEFT, padx=4)

        self.clear_all_button = ttk.Button(secondary_buttons, text="🗑️ Clear All",
                                           command=self.clear_all)
        self.clear_all_button.pack(side=tk.LEFT, padx=4)

        print("Control buttons created successfully")  # Debug print

        # Status bar with modern styling (moved to bottom of main frame)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="📋", font=('Segoe UI', 12)).grid(row=0, column=0, padx=(0, 5))

        self.status_var = tk.StringVar(value="Ready to download")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                 font=('Segoe UI', 10), foreground='#666666')
        status_label.grid(row=0, column=1, sticky=tk.W)

    def create_settings_tab(self):
        """Create settings tab with modern design"""
        settings_frame = self.settings_frame
        settings_frame.configure(padding="20")
        settings_frame.columnconfigure(0, weight=1)

        # Settings header
        header_frame = ttk.Frame(settings_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        ttk.Label(header_frame, text="⚙️ Application Settings",
                  font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(header_frame, text="Customize your download experience",
                  font=('Segoe UI', 10), foreground='#666666').pack(anchor=tk.W, pady=(5, 0))

        # Settings sections
        settings_container = ttk.Frame(settings_frame)
        settings_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        settings_container.columnconfigure(0, weight=1)

        # Download Settings Card
        download_card = ttk.LabelFrame(settings_container, text="📁 Download Settings", padding="20")
        download_card.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        download_card.columnconfigure(1, weight=1)

        # Download directory with browse button
        ttk.Label(download_card, text="📂 Download Folder:",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        dir_frame = ttk.Frame(download_card)
        dir_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        dir_frame.columnconfigure(0, weight=1)

        dir_entry = ttk.Entry(dir_frame, textvariable=self.download_dir)
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        ttk.Button(dir_frame, text="📁 Browse",
                   command=self.browse_directory).grid(row=0, column=1)

        # Quality and performance settings
        quality_frame = ttk.Frame(download_card)
        quality_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        quality_frame.columnconfigure(1, weight=1)

        ttk.Label(quality_frame, text="🎬 Video Quality:",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)

        quality_combo = ttk.Combobox(quality_frame, textvariable=self.video_quality,
                                     values=["best", "best[height<=1080p]", "best[height<=720p]",
                                             "best[height<=480p]", "best[height<=360p]", "worst"],
                                     state="readonly", width=20)
        quality_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(quality_frame, text="⚡ Concurrent Downloads:",
                  font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        concurrent_spin = ttk.Spinbox(quality_frame, from_=1, to=10,
                                      textvariable=self.max_concurrent, width=15)
        concurrent_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))

        # Behavior Settings Card
        behavior_card = ttk.LabelFrame(settings_container, text="🎯 Behavior Settings", padding="20")
        behavior_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        options_frame = ttk.Frame(behavior_card)
        options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

        desc_check = ttk.Checkbutton(options_frame, text="📝 Save video descriptions",
                                     variable=self.save_descriptions)
        desc_check.grid(row=0, column=0, sticky=tk.W, pady=5)

        auto_check = ttk.Checkbutton(options_frame, text="🚀 Auto-load video information",
                                     variable=self.auto_load_info)
        auto_check.grid(row=1, column=0, sticky=tk.W, pady=5)

        # Advanced Settings Card
        advanced_card = ttk.LabelFrame(settings_container, text="🔧 Advanced Settings", padding="20")
        advanced_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        # Add some advanced options
        advanced_frame = ttk.Frame(advanced_card)
        advanced_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

        ttk.Label(advanced_frame, text="🔄 Retry attempts:",
                  font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)

        self.retry_attempts = tk.IntVar(value=3)
        retry_spin = ttk.Spinbox(advanced_frame, from_=1, to=10,
                                 textvariable=self.retry_attempts, width=15)
        retry_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(advanced_frame, text="⏱️ Timeout (seconds):",
                  font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        self.timeout_seconds = tk.IntVar(value=30)
        timeout_spin = ttk.Spinbox(advanced_frame, from_=10, to=120,
                                   textvariable=self.timeout_seconds, width=15)
        timeout_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))

        # Action buttons
        action_frame = ttk.Frame(settings_container)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=20)

        ttk.Button(action_frame, text="💾 Save Settings",
                   command=self.save_settings).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(action_frame, text="🔄 Reset to Defaults",
                   command=self.reset_settings).pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="📁 Open Download Folder",
                   command=self.open_download_folder).pack(side=tk.LEFT, padx=5)

    def create_analytics_tab(self):
        """Create analytics tab with download statistics"""
        analytics_frame = self.analytics_frame
        analytics_frame.configure(padding="20")
        analytics_frame.columnconfigure(0, weight=1)

        # Analytics header
        header_frame = ttk.Frame(analytics_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        ttk.Label(header_frame, text="📊 Download Analytics",
                  font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(header_frame, text="Track your download performance and statistics",
                  font=('Segoe UI', 10), foreground='#666666').pack(anchor=tk.W, pady=(5, 0))

        # Statistics cards
        stats_container = ttk.Frame(analytics_frame)
        stats_container.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        stats_container.columnconfigure((0, 1, 2, 3), weight=1)

        # Create stat cards and store references for updating
        self.total_downloads_label = self.create_stat_card(stats_container, "📥 Total Downloads", "0", 0, 0)
        self.successful_downloads_label = self.create_stat_card(stats_container, "✅ Successful", "0", 0, 1)
        self.failed_downloads_label = self.create_stat_card(stats_container, "❌ Failed", "0", 0, 2)
        self.data_downloaded_label = self.create_stat_card(stats_container, "💾 Data Downloaded", "0 MB", 0, 3)

        # Session info
        session_frame = ttk.LabelFrame(analytics_frame, text="📈 Current Session", padding="15")
        session_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        session_frame.columnconfigure(1, weight=1)

        # Session stats
        session_stats_frame = ttk.Frame(session_frame)
        session_stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        session_stats_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.session_downloads_label = self.create_stat_card(session_stats_frame, "🔄 This Session", "0", 0, 0)
        self.session_data_label = self.create_stat_card(session_stats_frame, "📊 Session Data", "0 MB", 0, 1)

        # Analytics actions
        actions_frame = ttk.Frame(session_frame)
        actions_frame.grid(row=1, column=0, pady=(15, 0), sticky=(tk.W, tk.E))

        ttk.Button(actions_frame, text="🔄 Refresh Stats",
                   command=self.refresh_analytics).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(actions_frame, text="📤 Export Analytics",
                   command=self.export_analytics).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🗑️ Clear History",
                   command=self.clear_analytics_history).pack(side=tk.LEFT, padx=5)

        # Recent activity
        activity_frame = ttk.LabelFrame(analytics_frame, text="🕒 Recent Activity", padding="15")
        activity_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        activity_frame.columnconfigure(0, weight=1)
        activity_frame.rowconfigure(0, weight=1)

        # Activity list
        self.activity_text = scrolledtext.ScrolledText(activity_frame, height=8, wrap=tk.WORD)
        self.activity_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.activity_text.insert("1.0", "No recent activity")
        self.activity_text.configure(state=tk.DISABLED)

        # Load and display initial analytics
        try:
            self.update_analytics()
            self.update_session_analytics()
        except AttributeError:
            # Methods not defined yet, will be called later
            pass

    def update_analytics(self):
        """Update analytics display with current data"""
        try:
            self.total_downloads_label.config(text=str(self.analytics['total_downloads']))
            self.successful_downloads_label.config(text=str(self.analytics['successful_downloads']))
            self.failed_downloads_label.config(text=str(self.analytics['failed_downloads']))

            # Format data downloaded with appropriate units
            total_mb = self.analytics['total_data_downloaded']
            if total_mb >= 1024:
                data_text = f"{total_mb / 1024:.2f} GB"
            else:
                data_text = f"{total_mb:.1f} MB"

            self.data_downloaded_label.config(text=data_text)
        except AttributeError:
            # Labels not created yet
            pass

    def update_session_analytics(self):
        """Update session-specific analytics"""
        try:
            self.session_downloads_label.config(text=str(self.current_session['downloads_this_session']))

            session_mb = self.current_session['data_this_session']
            if session_mb >= 1024:
                session_data_text = f"{session_mb / 1024:.2f} GB"
            else:
                session_data_text = f"{session_mb:.1f} MB"

            self.session_data_label.config(text=session_data_text)
        except AttributeError:
            # Labels not created yet
            pass

    def create_stat_card(self, parent, title, value, row, col):
        """Create a statistics card"""
        card = ttk.LabelFrame(parent, text=title, padding="10")
        card.grid(row=row, column=col, sticky=(tk.W, tk.E), padx=5)

        value_label = ttk.Label(card, text=value, font=('Segoe UI', 18, 'bold'),
                                foreground='#0078d4')
        value_label.pack()

        return value_label

    def log_activity(self, message):
        """Log activity to analytics tab"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.activity_text.configure(state=tk.NORMAL)
            self.activity_text.insert("1.0", f"[{timestamp}] {message}\n")
            # Keep only last 100 lines
            lines = self.activity_text.get("1.0", tk.END).split('\n')
            if len(lines) > 100:
                self.activity_text.delete("100.0", tk.END)
            self.activity_text.configure(state=tk.DISABLED)
        except AttributeError:
            # Activity text not created yet
            pass

    def refresh_analytics(self):
        """Refresh analytics display"""
        self.update_analytics()
        self.update_session_analytics()
        self.log_activity("📊 Analytics refreshed")

    def export_analytics(self):
        """Export analytics to a file"""
        try:
            from tkinter import filedialog

            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Analytics Data"
            )

            if filename:
                export_data = {
                    'analytics': self.analytics,
                    'current_session': self.current_session,
                    'export_timestamp': datetime.now().isoformat()
                }

                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)

                self.log_activity(f"📤 Analytics exported to {Path(filename).name}")
                messagebox.showinfo("Export Complete", f"Analytics exported to:\n{filename}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export analytics:\n{str(e)}")

    def clear_analytics_history(self):
        """Clear analytics history after confirmation"""
        if messagebox.askyesno("Clear Analytics",
                               "Are you sure you want to clear all analytics history?\n\nThis action cannot be undone."):
            self.analytics = {
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'total_data_downloaded': 0.0,
                'first_use_date': datetime.now().isoformat(),
                'last_update': datetime.now().isoformat(),
                'download_history': []
            }
            self.save_analytics()
            self.update_analytics()
            self.log_activity("🗑️ Analytics history cleared")

    def create_stat_card(self, parent, title, value, row, col):
        """Create a statistics card"""
        card = ttk.LabelFrame(parent, text=title, padding="10")
        card.grid(row=row, column=col, sticky=(tk.W, tk.E), padx=5)

        value_label = ttk.Label(card, text=value, font=('Segoe UI', 18, 'bold'),
                                foreground='#0078d4')
        value_label.pack()

        return value_label

    def load_analytics(self):
        """Load analytics data from persistent storage"""
        default_analytics = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_data_downloaded': 0.0,  # in MB
            'first_use_date': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat(),
            'download_history': []  # List of download records
        }

        if self.analytics_file.exists():
            try:
                with open(self.analytics_file, 'r') as f:
                    data = json.load(f)
                # Ensure all required keys exist
                for key, default_value in default_analytics.items():
                    if key not in data:
                        data[key] = default_value
                return data
            except Exception as e:
                print(f"Error loading analytics: {e}")
                return default_analytics
        else:
            return default_analytics

    def save_analytics(self):
        """Save analytics data to persistent storage"""
        try:
            self.analytics['last_update'] = datetime.now().isoformat()
            with open(self.analytics_file, 'w') as f:
                json.dump(self.analytics, f, indent=2)
        except Exception as e:
            print(f"Error saving analytics: {e}")

    def record_download(self, video_info: VideoInfo, success: bool, file_size_mb: float = 0.0):
        """Record a download attempt with details"""
        download_record = {
            'timestamp': datetime.now().isoformat(),
            'title': video_info.title,
            'url': video_info.url,
            'uploader': video_info.uploader,
            'duration': video_info.duration,
            'success': success,
            'file_size_mb': file_size_mb,
            'error': video_info.error if not success else None
        }

        # Update main analytics
        if success:
            self.analytics['successful_downloads'] += 1
            self.analytics['total_data_downloaded'] += file_size_mb
            self.current_session['downloads_this_session'] += 1
            self.current_session['data_this_session'] += file_size_mb
        else:
            self.analytics['failed_downloads'] += 1

        self.analytics['total_downloads'] += 1

        # Add to history (keep last 1000 records)
        self.analytics['download_history'].append(download_record)
        if len(self.analytics['download_history']) > 1000:
            self.analytics['download_history'] = self.analytics['download_history'][-1000:]

        # Save to file
        self.save_analytics()

        # Update UI
        self.update_analytics()

    def get_file_size_mb(self, file_path):
        """Get file size in MB"""
        try:
            if file_path and Path(file_path).exists():
                size_bytes = Path(file_path).stat().st_size
                return size_bytes / (1024 * 1024)  # Convert to MB
        except Exception:
            pass
        return 0.0

    def estimate_file_size_from_progress(self, video_info: VideoInfo):
        """Estimate file size from download progress data"""
        try:
            # If we have size info from progress
            size_str = video_info.size
            if size_str:
                if 'GB' in size_str:
                    return float(size_str.replace('GB', '').strip()) * 1024
                elif 'MB' in size_str:
                    return float(size_str.replace('MB', '').strip())
                elif 'KB' in size_str:
                    return float(size_str.replace('KB', '').strip()) / 1024
        except Exception:
            pass
        return 0.0
        """Update analytics display"""
        try:
            self.total_downloads_label.config(text=str(self.analytics['total_downloads']))
            self.successful_downloads_label.config(text=str(self.analytics['successful_downloads']))
            self.failed_downloads_label.config(text=str(self.analytics['failed_downloads']))
            self.data_downloaded_label.config(text=f"{self.analytics['total_data_downloaded']:.1f} MB")
        except AttributeError:
            # Labels not created yet
            pass

    def log_activity(self, message):
        """Log activity to analytics tab"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.activity_text.configure(state=tk.NORMAL)
            self.activity_text.insert("1.0", f"[{timestamp}] {message}\n")
            # Keep only last 100 lines
            lines = self.activity_text.get("1.0", tk.END).split('\n')
            if len(lines) > 100:
                self.activity_text.delete("100.0", tk.END)
            self.activity_text.configure(state=tk.DISABLED)
        except AttributeError:
            # Activity text not created yet
            pass

    def create_context_menu(self):
        """Create context menu for queue"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self.remove_selected)
        self.context_menu.add_command(label="Retry", command=self.retry_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open File Location", command=self.open_file_location)
        self.context_menu.add_command(label="Copy URL", command=self.copy_url)

        self.queue_tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu"""
        item = self.queue_tree.identify_row(event.y)
        if item:
            self.queue_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def validate_url(self, event=None):
        """Enhanced URL validation with automatic adding to queue"""
        url = self.url_entry.get().strip()

        # Don't validate placeholder text
        if not url or url == "Paste YouTube URL here (video, playlist, or channel)":
            self.validation_label.config(text="", style='TLabel')
            self.url_entry.config(style='TEntry')
            return

        is_valid = any(re.match(pattern, url) for pattern in self.youtube_patterns)

        if is_valid:
            # Determine URL type for better feedback
            if 'playlist' in url.lower():
                self.validation_label.config(text="✅ Valid Playlist URL - Will add all videos", style='Success.TLabel')
            elif 'channel' in url.lower() or '/@' in url:
                self.validation_label.config(text="✅ Valid Channel URL", style='Success.TLabel')
            else:
                self.validation_label.config(text="✅ Valid Video URL", style='Success.TLabel')

            try:
                self.url_entry.config(style='Valid.TEntry')
            except:
                pass

            # Auto-load info and add to queue if enabled
            if self.auto_load_info.get() and not self.is_loading_info:
                self.root.after(1500, lambda: self.auto_add_validated_url(url))
        else:
            self.validation_label.config(text="❌ Invalid YouTube URL", style='Error.TLabel')
            try:
                self.url_entry.config(style='Invalid.TEntry')
            except:
                pass

    def auto_add_validated_url(self, url):
        """Automatically add validated URL to queue"""
        if self.url_entry.get().strip() == url:  # Only if URL hasn't changed
            self.add_to_queue()

    def on_url_focus_out(self, event=None):
        """Handle URL entry focus out"""
        pass

    def on_url_text_focus(self, event):
        """Clear placeholder text when multi-URL text widget is focused"""
        content = self.url_text.get("1.0", "end-1c")
        if content == "Enter multiple YouTube URLs (one per line)":
            self.url_text.delete("1.0", tk.END)
            self.url_text.configure(foreground='#333333')

    def on_url_entry_focus(self, event):
        """Handle URL entry focus in"""
        if self.url_entry.get() == "Paste YouTube URL here (video, playlist, or channel)":
            self.url_entry.delete(0, tk.END)
            self.url_entry.configure(foreground='#333333')

    def filter_queue(self, filter_type):
        """Filter queue display by status"""
        # This would implement filtering logic
        # For now, just update the stats
        self.update_queue_stats()

    def update_queue_stats(self):
        """Update queue statistics display"""
        total = len(self.download_queue)
        pending = sum(1 for item in self.download_queue if item.status == "Pending")
        downloading = sum(1 for item in self.download_queue if item.status == "Downloading")
        completed = sum(1 for item in self.download_queue if item.status == "Completed")
        failed = sum(1 for item in self.download_queue if item.status == "Failed")

        stats_text = f"📊 {total} videos • ⏳ {pending} pending • ⬇️ {downloading} downloading • ✅ {completed} completed"
        if failed > 0:
            stats_text += f" • ❌ {failed} failed"

        self.queue_stats_label.config(text=stats_text)

    def paste_urls(self):
        """Paste URLs from clipboard"""
        try:
            clipboard = self.root.clipboard_get()
            if not self.url_entry.get().strip() or self.url_entry.get() == "Paste YouTube URL here (video, playlist, or channel)":
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard)
                self.url_entry.configure(foreground='#333333')
                self.validate_url()
            else:
                self.url_text.delete("1.0", tk.END)
                self.url_text.insert("1.0", clipboard)
                self.url_text.configure(foreground='#333333')
        except Exception:
            pass

    def clear_inputs(self):
        """Clear all input fields with placeholder restoration"""
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, "Paste YouTube URL here (video, playlist, or channel)")
        self.url_entry.configure(foreground='#999999')

        self.url_text.delete("1.0", tk.END)
        self.url_text.insert("1.0", "Enter multiple YouTube URLs (one per line)")
        self.url_text.configure(foreground='#999999')

        self.validation_label.config(text="")
        try:
            self.url_entry.config(style='TEntry')
        except:
            pass

    def get_urls_from_inputs(self) -> List[str]:
        """Get URLs from input fields"""
        urls = []

        # Single URL entry
        single_url = self.url_entry.get().strip()
        if single_url and single_url != "Paste YouTube URL here (video, playlist, or channel)":
            urls.append(single_url)

        # Multiple URLs text
        multi_text = self.url_text.get("1.0", tk.END).strip()
        if multi_text and multi_text != "Enter multiple YouTube URLs (one per line)":
            for line in multi_text.split('\n'):
                url = line.strip()
                if url and url not in urls:
                    urls.append(url)

        return urls

    def add_to_queue(self):
        """Enhanced add to queue with automatic playlist expansion"""
        urls = self.get_urls_from_inputs()
        if not urls:
            messagebox.showwarning("No URLs", "Please enter at least one YouTube URL")
            return

        # Clear inputs immediately to show responsiveness
        self.clear_inputs()

        # Start loading process in background
        self.load_and_add_urls(urls)

    def load_and_add_urls(self, urls):
        """Load video/playlist info and add to queue with better URL handling"""

        def worker():
            try:
                total_added = 0
                total_duplicates = 0

                for url in urls:
                    # Clean and validate URL
                    clean_url = self.clean_youtube_url(url)
                    if not clean_url:
                        self.message_queue.put(("error", f"Invalid URL: {url}"))
                        continue

                    self.message_queue.put(("status", f"Loading: {clean_url}"))

                    try:
                        # Load video/playlist info with better options
                        ydl_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'extract_flat': False,
                            'socket_timeout': 30,
                            'no_check_certificate': True,
                            'ignore_errors': False,
                        }

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(clean_url, download=False)

                        if info:
                            if 'entries' in info and info['entries']:
                                # Playlist - add all videos
                                playlist_title = info.get('title', 'Unknown Playlist')
                                self.message_queue.put(
                                    ("status", f"Adding playlist: {playlist_title} ({len(info['entries'])} videos)"))

                                for i, entry in enumerate(info['entries']):
                                    if entry:
                                        # Use the original YouTube URL, not the direct stream URL
                                        video_id = entry.get('id')
                                        if video_id:
                                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                                        else:
                                            video_url = entry.get('webpage_url', entry.get('url', ''))

                                        if video_url and not any(v.url == video_url for v in self.download_queue):
                                            video_info = VideoInfo(
                                                url=video_url,
                                                title=entry.get('title', f'Video {i + 1}'),
                                                duration=self.format_duration(entry.get('duration', 0)),
                                                uploader=entry.get('uploader', info.get('uploader', 'Unknown')),
                                                view_count=entry.get('view_count', 0),
                                                status="Pending"
                                            )

                                            self.download_queue.append(video_info)

                                            # Add to tree
                                            item_id = self.queue_tree.insert('', 'end', values=(
                                                "⏳ Pending",
                                                video_info.title,
                                                video_info.duration,
                                                video_info.uploader,
                                                "0%",
                                                "",
                                                "",
                                                ""
                                            ))
                                            video_info.tree_item_id = item_id
                                            total_added += 1
                                        else:
                                            total_duplicates += 1
                            else:
                                # Single video - ensure we have the correct URL format
                                video_id = info.get('id')
                                if video_id:
                                    clean_url = f"https://www.youtube.com/watch?v={video_id}"

                                if not any(v.url == clean_url for v in self.download_queue):
                                    video_info = VideoInfo(
                                        url=clean_url,
                                        title=info.get('title', 'Unknown'),
                                        duration=self.format_duration(info.get('duration', 0)),
                                        uploader=info.get('uploader', 'Unknown'),
                                        view_count=info.get('view_count', 0),
                                        status="Pending"
                                    )

                                    self.download_queue.append(video_info)

                                    # Add to tree
                                    item_id = self.queue_tree.insert('', 'end', values=(
                                        "⏳ Pending",
                                        video_info.title,
                                        video_info.duration,
                                        video_info.uploader,
                                        "0%",
                                        "",
                                        "",
                                        ""
                                    ))
                                    video_info.tree_item_id = item_id
                                    total_added += 1
                                else:
                                    total_duplicates += 1
                        else:
                            self.message_queue.put(("error", f"Failed to load: {url}"))

                    except yt_dlp.DownloadError as e:
                        self.message_queue.put(("error", f"Video unavailable: {url} - {str(e)}"))
                    except Exception as e:
                        self.message_queue.put(("error", f"Error loading {url}: {str(e)}"))

                # Final status update
                status_msg = f"✅ Added {total_added} video(s) to queue"
                if total_duplicates > 0:
                    status_msg += f" ({total_duplicates} duplicate(s) skipped)"

                self.message_queue.put(("status", status_msg))
                self.message_queue.put(("update_stats", None))

                # Log activity
                self.message_queue.put(("log_activity", f"➕ Added {total_added} video(s) to queue"))

            except Exception as e:
                self.message_queue.put(("error", f"Error adding to queue: {str(e)}"))

        # Start worker thread
        threading.Thread(target=worker, daemon=True).start()

    def is_valid_youtube_url(self, url):
        """Check if URL is a valid YouTube URL format"""
        if not url:
            return False
        return any(re.match(pattern, url) for pattern in self.youtube_patterns)

    def clean_youtube_url(self, url):
        """Clean and normalize YouTube URLs"""
        if not url or not url.strip():
            return None

        url = url.strip()

        # If it's already a proper YouTube URL, return as-is
        if any(re.match(pattern, url) for pattern in self.youtube_patterns):
            return url

        # Extract video ID from various YouTube URL formats
        video_id_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in video_id_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"

        # Check if it's a playlist URL
        playlist_patterns = [
            r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
        ]

        for pattern in playlist_patterns:
            match = re.search(pattern, url)
            if match:
                playlist_id = match.group(1)
                return f"https://www.youtube.com/playlist?list={playlist_id}"

        # If we can't clean it, return None
        return None

    def start_download(self):
        """Start downloading queued items"""
        if self.is_downloading:
            messagebox.showinfo("Already Downloading", "Downloads are already in progress")
            return

        pending_items = [item for item in self.download_queue if item.status == "Pending"]
        if not pending_items:
            messagebox.showwarning("No Items", "No pending items to download")
            return

        # Update UI
        self.is_downloading = True
        self.download_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)

        # Start download thread
        download_thread = threading.Thread(target=self.download_worker, daemon=True)
        download_thread.start()

    def download_worker(self):
        """Worker thread for downloads"""
        try:
            # Create download directory
            download_path = Path(self.download_dir.get())
            download_path.mkdir(parents=True, exist_ok=True)

            pending_items = [item for item in self.download_queue if item.status == "Pending"]
            total_items = len(pending_items)

            if total_items == 0:
                self.message_queue.put(("status", "No pending items to download"))
                return

            self.message_queue.put(("status", f"Starting download of {total_items} items..."))

            # Run the async download function
            asyncio.run(self.async_download_worker(pending_items, download_path, total_items))

        except Exception as e:
            self.message_queue.put(("error", f"Unexpected download error: {str(e)}"))
        finally:
            self.is_downloading = False
            self.message_queue.put(("download_complete", None))

    async def async_download_worker(self, pending_items, download_path, total_items):
        """Async download worker with proper progress tracking"""
        try:
            successful_downloads = 0
            failed_downloads = 0

            # Download each item
            for i, item in enumerate(pending_items):
                if not self.is_downloading:
                    self.message_queue.put(("status", "Download cancelled by user"))
                    break

                try:
                    # Update item status
                    item.status = "Downloading"
                    self.progress_queue.put(("video_status", item))
                    self.message_queue.put(("status", f"Downloading: {item.title[:50]}..."))

                    # Debug: Log the URL being downloaded
                    print(f"DEBUG: Attempting to download URL: {item.url}")

                    # Validate URL format before downloading
                    if not self.is_valid_youtube_url(item.url):
                        item.status = "Failed"
                        item.error = f"Invalid YouTube URL format: {item.url}"
                        self.progress_queue.put(("video_status", item))
                        failed_downloads += 1
                        continue

                    # Create progress callback for this specific item
                    def progress_callback(d):
                        if d['status'] == 'downloading':
                            try:
                                downloaded = d.get('downloaded_bytes', 0)
                                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

                                if total > 0:
                                    progress = (downloaded / total) * 100
                                    item.progress = min(int(progress), 100)

                                    # Format speed
                                    speed = d.get('speed', 0)
                                    if speed:
                                        if speed > 1024 * 1024:
                                            item.speed = f"{speed / (1024 * 1024):.1f} MB/s"
                                        elif speed > 1024:
                                            item.speed = f"{speed / 1024:.1f} KB/s"
                                        else:
                                            item.speed = f"{speed:.0f} B/s"

                                    # Format ETA
                                    eta = d.get('eta')
                                    if eta:
                                        if eta > 3600:
                                            item.eta = f"{eta // 3600:02d}:{(eta % 3600) // 60:02d}:{eta % 60:02d}"
                                        else:
                                            item.eta = f"{eta // 60:02d}:{eta % 60:02d}"

                                    # Format size
                                    if total:
                                        if total > 1024 * 1024 * 1024:
                                            item.size = f"{total / (1024 * 1024 * 1024):.1f} GB"
                                        elif total > 1024 * 1024:
                                            item.size = f"{total / (1024 * 1024):.1f} MB"
                                        else:
                                            item.size = f"{total / 1024:.1f} KB"

                                    # Update current progress bar
                                    self.progress_queue.put(("current_progress", item.progress))
                                    self.progress_queue.put(("video_status", item))

                            except Exception as e:
                                pass  # Don't let progress errors stop downloads

                    # Use download method with progress tracking
                    success, message = await self.simple_download_fallback(item.url, download_path,
                                                                           progress_callback)

                    # If that fails, try the most basic approach
                    if not success:
                        self.message_queue.put(("status", f"Trying basic download method..."))
                        success, message = await self.basic_download_fallback(item.url, download_path)

                    if success:
                        item.status = "Completed"
                        item.progress = 100
                        item.speed = ""
                        item.eta = ""
                        successful_downloads += 1

                        # Calculate file size for analytics
                        file_size_mb = 0.0

                        # Try to find the downloaded file and get its size
                        try:
                            # Look for the file in the download directory
                            for file_path in download_path.glob("*"):
                                if file_path.is_file() and any(ext in file_path.suffix.lower()
                                                               for ext in ['.mp4', '.webm', '.mkv', '.mp3', '.m4a']):
                                    # Check if file was modified recently (within last 2 minutes)
                                    if (datetime.now().timestamp() - file_path.stat().st_mtime) < 120:
                                        item.file_path = str(file_path)
                                        file_size_mb = self.get_file_size_mb(str(file_path))
                                        break
                        except Exception:
                            pass

                        # If we couldn't find the file, estimate from progress data
                        if file_size_mb == 0.0:
                            file_size_mb = self.estimate_file_size_from_progress(item)

                        # Record successful download
                        self.record_download(item, True, file_size_mb)

                    else:
                        item.status = "Failed"
                        item.error = message
                        item.progress = 0
                        item.speed = ""
                        item.eta = ""
                        failed_downloads += 1

                        # Record failed download
                        self.record_download(item, False, 0.0)

                except Exception as e:
                    item.status = "Failed"
                    item.error = f"Download error: {str(e)}"
                    item.progress = 0
                    failed_downloads += 1

                    # Record failed download
                    self.record_download(item, False, 0.0)

                # Update overall progress
                overall_progress = ((i + 1) / total_items) * 100
                self.progress_queue.put(("overall_progress", overall_progress))
                self.progress_queue.put(("video_status", item))

                # Reset current progress for next video
                self.progress_queue.put(("current_progress", 0))

                # Small delay to prevent overwhelming the UI
                await asyncio.sleep(0.1)

            # Final status
            if self.is_downloading:  # Only show completion message if not cancelled
                self.message_queue.put(("status",
                                        f"Download complete! ✓ {successful_downloads} successful, "
                                        f"✗ {failed_downloads} failed"))

        except Exception as e:
            self.message_queue.put(("error", f"Download setup error: {str(e)}"))

    async def simple_download_fallback(self, url, download_path, progress_callback=None):
        """Enhanced download with multiple format fallbacks"""
        try:
            import concurrent.futures

            def download_sync():
                # Progress hook that calls our callback
                def progress_hook(d):
                    if progress_callback:
                        progress_callback(d)

                # Try multiple format selectors in order of preference
                quality_setting = self.video_quality.get()

                # Define format fallback chain
                format_chains = {
                    "best": [
                        "best[height<=1080][ext=mp4]",
                        "best[height<=1080]",
                        "best[ext=mp4]",
                        "best"
                    ],
                    "best[height<=1080p]": [
                        "best[height<=1080][ext=mp4]",
                        "best[height<=1080]",
                        "best[ext=mp4]",
                        "best"
                    ],
                    "best[height<=720p]": [
                        "best[height<=720][ext=mp4]",
                        "best[height<=720]",
                        "best[height<=1080][ext=mp4]",
                        "best[ext=mp4]",
                        "best"
                    ],
                    "best[height<=480p]": [
                        "best[height<=480][ext=mp4]",
                        "best[height<=480]",
                        "best[height<=720][ext=mp4]",
                        "best[ext=mp4]",
                        "best"
                    ],
                    "best[height<=360p]": [
                        "best[height<=360][ext=mp4]",
                        "best[height<=360]",
                        "best[height<=480][ext=mp4]",
                        "best[ext=mp4]",
                        "best"
                    ],
                    "worst": [
                        "worst[ext=mp4]",
                        "worst"
                    ]
                }

                formats_to_try = format_chains.get(quality_setting, format_chains["best"])

                # Try each format in the chain
                for format_selector in formats_to_try:
                    try:
                        ydl_opts = {
                            'outtmpl': str(download_path / '%(title)s.%(ext)s'),
                            'format': format_selector,
                            'quiet': True,
                            'no_warnings': True,
                            'extractaudio': False,
                            'writesubtitles': self.save_descriptions.get(),
                            'writeautomaticsub': False,
                            'ignoreerrors': False,
                            'retries': 2,
                            'fragment_retries': 2,
                            'socket_timeout': 30,
                            'progress_hooks': [progress_hook] if progress_callback else [],
                            # Additional options for better compatibility
                            'cookiefile': None,
                            'no_check_certificate': True,
                        }

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            result = ydl.download([url])
                            if result == 0:
                                return True, f"Downloaded successfully using format: {format_selector}"

                    except yt_dlp.DownloadError as e:
                        # If this format failed, try the next one
                        if "Requested format is not available" in str(e):
                            continue
                        else:
                            # Different error, might be worth reporting
                            if format_selector == formats_to_try[-1]:  # Last format
                                return False, f"yt-dlp error: {str(e)}"
                            continue
                    except Exception as e:
                        # Other errors, try next format
                        if format_selector == formats_to_try[-1]:  # Last format
                            return False, f"Download failed: {str(e)}"
                        continue

                # If all formats failed
                return False, "All format options failed - video may be unavailable or restricted"

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                success, message = await loop.run_in_executor(executor, download_sync)
                return success, message

        except Exception as e:
            return False, f"Fallback error: {str(e)}"

    def pause_download(self):
        """Pause current downloads"""
        # Implementation would pause current downloads
        pass

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
        for child in list(self.queue_tree.get_children()):
            values = self.queue_tree.item(child)['values']
            if len(values) > 0 and any(status in values[0] for status in ["✅ Completed", "❌ Failed"]):
                self.queue_tree.delete(child)

        self.update_queue_stats()

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
        self.update_queue_stats()

    def remove_selected(self):
        """Remove selected items from queue"""
        selected = self.queue_tree.selection()
        if not selected:
            return

        for item_id in selected:
            # Find corresponding queue item and remove it
            for i, item in enumerate(self.download_queue):
                if hasattr(item, 'tree_item_id') and item.tree_item_id == item_id:
                    del self.download_queue[i]
                    break

            # Remove from tree
            self.queue_tree.delete(item_id)

        self.update_queue_stats()
        self.status_var.set("Removed selected items")

    def retry_selected(self):
        """Retry selected failed downloads"""
        selected = self.queue_tree.selection()
        if not selected:
            return

        for item_id in selected:
            # Find corresponding queue item
            for item in self.download_queue:
                if hasattr(item, 'tree_item_id') and item.tree_item_id == item_id:
                    if item.status in ["Failed", "Error"]:
                        item.status = "Pending"
                        item.progress = 0
                        item.speed = ""
                        item.eta = ""
                        item.error = ""
                        self.update_queue_item(item)
                    break

        self.update_queue_stats()

    def open_file_location(self):
        """Open file location for selected item"""
        selected = self.queue_tree.selection()
        if not selected:
            return

        for item_id in selected:
            # Find corresponding queue item
            for item in self.download_queue:
                if hasattr(item, 'tree_item_id') and item.tree_item_id == item_id:
                    if item.file_path and Path(item.file_path).exists():
                        import subprocess
                        import platform

                        try:
                            if platform.system() == "Windows":
                                subprocess.run(["explorer", "/select,", item.file_path])
                            elif platform.system() == "Darwin":  # macOS
                                subprocess.run(["open", "-R", item.file_path])
                            else:  # Linux
                                subprocess.run(["xdg-open", str(Path(item.file_path).parent)])
                        except Exception as e:
                            messagebox.showerror("Error", f"Could not open file location: {e}")
                    else:
                        messagebox.showinfo("File Not Found", "File not found or download not completed")
                    break

    def copy_url(self):
        """Copy URL of selected item"""
        selected = self.queue_tree.selection()
        if not selected:
            return

        for item_id in selected:
            # Find corresponding queue item
            for item in self.download_queue:
                if hasattr(item, 'tree_item_id') and item.tree_item_id == item_id:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(item.url)
                    self.status_var.set("URL copied to clipboard")
                    break

    def browse_directory(self):
        """Browse for download directory"""
        directory = filedialog.askdirectory(initialdir=self.download_dir.get())
        if directory:
            self.download_dir.set(directory)
            self.save_settings()

    def reset_settings(self):
        """Reset settings to defaults"""
        self.download_dir.set(str(Path.home() / "Downloads" / "YouTube"))
        self.max_concurrent.set(3)
        self.video_quality.set("best")
        self.save_descriptions.set(False)
        self.auto_load_info.set(True)
        self.retry_attempts.set(3)
        self.timeout_seconds.set(30)
        self.status_var.set("Settings reset to defaults")

    def open_download_folder(self):
        """Open the download folder in file explorer"""
        import subprocess
        import platform

        folder_path = self.download_dir.get()
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", folder_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def format_duration(self, seconds):
        """Format duration in seconds to readable format"""
        if not seconds:
            return ""

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def format_views(self, views):
        """Format view count"""
        if views >= 1000000:
            return f"{views / 1000000:.1f}M"
        elif views >= 1000:
            return f"{views / 1000:.1f}K"
        else:
            return str(views)

    def process_messages(self):
        """Process messages from worker threads"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()

                if msg_type == "status":
                    self.status_var.set(msg_data)
                elif msg_type == "info":
                    messagebox.showinfo("Information", msg_data)
                elif msg_type == "error":
                    messagebox.showerror("Error", msg_data)
                elif msg_type == "update_stats":
                    self.update_queue_stats()
                elif msg_type == "log_activity":
                    self.log_activity(msg_data)
                elif msg_type == "download_complete":
                    self.download_button.config(state=tk.NORMAL)
                    self.pause_button.config(state=tk.DISABLED)
                    self.stop_button.config(state=tk.DISABLED)
                    self.overall_progress_var.set(0)
                    self.current_progress_var.set(0)

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_messages)

    def process_progress(self):
        """Process progress updates with visual enhancements"""
        try:
            updates_processed = 0
            while updates_processed < 10:  # Limit updates per cycle to prevent UI lag
                msg_type, msg_data = self.progress_queue.get_nowait()

                if msg_type == "overall_progress":
                    self.overall_progress_var.set(msg_data)
                    self.overall_progress_label.config(text=f"{int(msg_data)}%")
                elif msg_type == "current_progress":
                    self.current_progress_var.set(msg_data)
                    self.current_progress_label.config(text=f"{int(msg_data)}%")
                elif msg_type == "video_status":
                    self.update_queue_item(msg_data)
                    self.update_queue_stats()

                updates_processed += 1

        except queue.Empty:
            pass

        # Schedule next check - more frequent for better responsiveness
        self.root.after(50, self.process_progress)

    def save_settings(self):
        """Enhanced settings saving with user feedback"""
        settings = {
            'download_dir': self.download_dir.get(),
            'max_concurrent': self.max_concurrent.get(),
            'video_quality': self.video_quality.get(),
            'save_descriptions': self.save_descriptions.get(),
            'auto_load_info': self.auto_load_info.get(),
            'retry_attempts': getattr(self, 'retry_attempts', tk.IntVar(value=3)).get(),
            'timeout_seconds': getattr(self, 'timeout_seconds', tk.IntVar(value=30)).get()
        }

        settings_file = Path.home() / '.youtube_downloader_enhanced_settings.json'
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            self.status_var.set("💾 Settings saved successfully")

            # Show temporary success message
            self.root.after(3000, lambda: self.status_var.set("Ready to download"))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def load_settings(self):
        """Enhanced settings loading with defaults"""
        settings_file = Path.home() / '.youtube_downloader_enhanced_settings.json'
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)

                self.download_dir.set(settings.get('download_dir', self.download_dir.get()))
                self.max_concurrent.set(settings.get('max_concurrent', 3))
                self.video_quality.set(settings.get('video_quality', 'best'))
                self.save_descriptions.set(settings.get('save_descriptions', False))
                self.auto_load_info.set(settings.get('auto_load_info', True))

                # Initialize new settings with defaults if they don't exist
                if not hasattr(self, 'retry_attempts'):
                    self.retry_attempts = tk.IntVar(value=settings.get('retry_attempts', 3))
                else:
                    self.retry_attempts.set(settings.get('retry_attempts', 3))

                if not hasattr(self, 'timeout_seconds'):
                    self.timeout_seconds = tk.IntVar(value=settings.get('timeout_seconds', 30))
                else:
                    self.timeout_seconds.set(settings.get('timeout_seconds', 30))

            except Exception as e:
                print(f"Error loading settings: {e}")
                # Initialize defaults if loading fails
                if not hasattr(self, 'retry_attempts'):
                    self.retry_attempts = tk.IntVar(value=3)
                if not hasattr(self, 'timeout_seconds'):
                    self.timeout_seconds = tk.IntVar(value=30)
        else:
            # Initialize defaults for new installations
            if not hasattr(self, 'retry_attempts'):
                self.retry_attempts = tk.IntVar(value=3)
            if not hasattr(self, 'timeout_seconds'):
                self.timeout_seconds = tk.IntVar(value=30)

    def update_queue_item(self, video_info: VideoInfo):
        """Update item in queue tree using stored tree item reference"""
        # Track analytics changes (removed duplicate analytics tracking since it's now in record_download)
        try:
            # Try to use stored tree item ID first
            if hasattr(video_info, 'tree_item_id') and video_info.tree_item_id:
                try:
                    # Check if the item still exists
                    if self.queue_tree.exists(video_info.tree_item_id):
                        self.update_tree_item(video_info.tree_item_id, video_info)
                        return
                except Exception:
                    pass

            # Fallback to URL matching
            for child in self.queue_tree.get_children():
                try:
                    # Find item by matching with download queue
                    for queue_item in self.download_queue:
                        if (hasattr(queue_item, 'tree_item_id') and
                                queue_item.tree_item_id == child and
                                queue_item.url == video_info.url):
                            video_info.tree_item_id = child
                            self.update_tree_item(child, video_info)
                            return
                except Exception:
                    continue

        except Exception as e:
            print(f"Error updating queue item: {e}")

        # Update session analytics display
        try:
            self.update_session_analytics()
        except AttributeError:
            pass

    def update_tree_item(self, item_id, video_info: VideoInfo):
        """Update a specific tree item with enhanced progress visualization"""
        try:
            # Format progress with visual indicator
            progress_text = f"{video_info.progress}%"
            if video_info.status == "Downloading" and video_info.progress > 0:
                # Add visual progress bar - 20 characters max for better fit
                filled = video_info.progress // 5  # Each █ represents 5%
                empty = 20 - filled
                progress_text = f"{video_info.progress}% [{'█' * filled}{'░' * empty}]"

            # Color-code status with emojis
            status_text = video_info.status
            if video_info.status == "Completed":
                status_text = "✅ Completed"
            elif video_info.status == "Failed":
                status_text = "❌ Failed"
            elif video_info.status == "Downloading":
                status_text = "⬇️ Downloading"
            elif video_info.status == "Pending":
                status_text = "⏳ Pending"
            elif video_info.status == "Loading Info":
                status_text = "🔄 Loading Info"
            elif video_info.status == "Info Failed":
                status_text = "❌ Info Failed"
            elif video_info.status == "Unavailable":
                status_text = "🚫 Unavailable"
            elif video_info.status == "Error":
                status_text = "⚠️ Error"

            # Clean up title display
            title_text = video_info.title
            if title_text.startswith("📡 "):
                title_text = title_text[2:]  # Remove loading emoji once loaded

            # Update the tree item
            self.queue_tree.item(item_id, values=(
                status_text,
                title_text,
                video_info.duration,
                video_info.uploader,
                progress_text,
                video_info.speed,
                video_info.eta,
                video_info.size
            ))

            # Scroll to the current item if it's downloading
            if video_info.status == "Downloading":
                self.queue_tree.see(item_id)

            # Force UI update
            self.root.update_idletasks()

        except Exception as e:
            print(f"Error updating tree item: {e}")


def main():
    """Enhanced main application entry point"""
    root = tk.Tk()

    # Set modern window properties
    root.title("🎬 YouTube Downloader Pro - Enhanced Edition")
    root.geometry("1400x900")
    root.minsize(1000, 700)

    # Set DPI awareness for Windows
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    # Set window icon if available
    try:
        # Try to set a modern icon
        root.iconbitmap("icon.ico")
    except Exception:
        pass

    # Apply modern styling to the root window
    root.configure(bg='#f0f0f0')

    # Create the application
    app = YouTubeDownloaderGUI(root)

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Add a modern app icon to taskbar (Windows)
    try:
        import tkinter.messagebox
        root.wm_iconname("YouTube Downloader Pro")
    except Exception:
        pass

    # Handle window closing gracefully
    def on_closing():
        if app.is_downloading:
            if messagebox.askyesno("Confirm Exit",
                                   "Downloads are in progress. Are you sure you want to exit?"):
                app.stop_download()
                root.after(1000, root.destroy)  # Give time for cleanup
            else:
                return
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()