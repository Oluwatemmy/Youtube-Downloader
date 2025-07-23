#!/usr/bin/env python3
"""
Web-based GUI for YouTube Downloader using Flask
This provides a cross-platform solution that works on any system with a web browser
"""

from flask import Flask, render_template, request, jsonify, send_file
import asyncio
import threading
import queue
import time
import json
import os
from pathlib import Path
import webbrowser
import sys

# Import our enhanced downloader
sys.path.insert(0, str(Path(__file__).parent))
from yt_dlp_enhanced import OptimizedYoutubeDownloader

app = Flask(__name__)
app.secret_key = 'youtube_downloader_secret_key_2024'

# Global variables
download_queue = []
download_status = {}
message_queue = queue.Queue()
is_downloading = False
downloader = None

# Settings
settings = {
    'download_dir': str(Path.home() / 'Downloads' / 'YouTube'),
    'max_concurrent': 3,
    'video_quality': 'best',
    'save_descriptions': False
}

class DownloadItem:
    def __init__(self, url, title="Unknown"):
        self.url = url
        self.title = title
        self.status = "Pending"
        self.progress = 0
        self.speed = ""
        self.size = ""
        self.error = ""
        
    def to_dict(self):
        return {
            'url': self.url,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'size': self.size,
            'error': self.error
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/add_urls', methods=['POST'])
def add_urls():
    """Add URLs to download queue"""
    data = request.get_json()
    urls_text = data.get('urls', '')
    
    if not urls_text.strip():
        return jsonify({'error': 'No URLs provided'}), 400
    
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
    added = 0
    
    for url in urls:
        if any(domain in url for domain in ['youtube.com', 'youtu.be']):
            item = DownloadItem(url)
            download_queue.append(item)
            added += 1
    
    return jsonify({'message': f'Added {added} URLs to queue', 'count': len(download_queue)})

@app.route('/api/queue')
def get_queue():
    """Get current download queue"""
    return jsonify([item.to_dict() for item in download_queue])

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update settings"""
    global settings
    
    if request.method == 'POST':
        data = request.get_json()
        settings.update(data)
        return jsonify({'message': 'Settings updated'})
    
    return jsonify(settings)

@app.route('/api/start_download', methods=['POST'])
def start_download():
    """Start downloading queued items"""
    global is_downloading
    
    if is_downloading:
        return jsonify({'error': 'Download already in progress'}), 400
    
    if not download_queue:
        return jsonify({'error': 'No items in queue'}), 400
    
    # Start download in thread
    thread = threading.Thread(target=download_worker, daemon=True)
    thread.start()
    
    return jsonify({'message': 'Download started'})

@app.route('/api/stop_download', methods=['POST'])
def stop_download():
    """Stop current downloads"""
    global is_downloading
    is_downloading = False
    return jsonify({'message': 'Download stopped'})

@app.route('/api/clear_queue', methods=['POST'])
def clear_queue():
    """Clear download queue"""
    global download_queue
    data = request.get_json()
    clear_type = data.get('type', 'all')
    
    if clear_type == 'completed':
        download_queue = [item for item in download_queue 
                         if item.status not in ['Completed', 'Failed']]
    else:
        download_queue.clear()
    
    return jsonify({'message': 'Queue cleared'})

def download_worker():
    """Worker function for downloads"""
    global is_downloading, downloader
    
    try:
        is_downloading = True
        
        # Create download directory
        Path(settings['download_dir']).mkdir(parents=True, exist_ok=True)
        
        # Get pending items
        pending_items = [item for item in download_queue if item.status == "Pending"]
        
        if not pending_items:
            return
        
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create downloader
        downloader = OptimizedYoutubeDownloader(
            download_dir=settings['download_dir'],
            max_concurrent=settings['max_concurrent']
        )
        
        # Download each item
        for item in pending_items:
            if not is_downloading:
                break
            
            item.status = "Downloading"
            
            try:
                success, message = loop.run_until_complete(
                    downloader.download_video_optimized(item.url)
                )
                
                if success:
                    item.status = "Completed"
                    item.progress = 100
                    if "Downloaded:" in message:
                        item.title = message.replace("Downloaded: ", "")
                else:
                    item.status = "Failed"
                    item.error = message
                    
            except Exception as e:
                item.status = "Failed"
                item.error = str(e)
        
        # Cleanup
        if downloader:
            downloader.cleanup()
        loop.close()
        
    except Exception as e:
        print(f"Download worker error: {e}")
    finally:
        is_downloading = False

# Create HTML template
template_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #ff0000; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; }
        input, select, textarea { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 5px; font-size: 14px; }
        textarea { height: 100px; resize: vertical; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; margin: 5px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .queue-table { width: 100%; border-collapse: collapse; }
        .queue-table th, .queue-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .queue-table th { background: #f8f9fa; font-weight: 600; }
        .status-pending { color: #6c757d; }
        .status-downloading { color: #007bff; }
        .status-completed { color: #28a745; }
        .status-failed { color: #dc3545; }
        .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: #007bff; transition: width 0.3s; }
        .message { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background: #f8d7da; color: #721c24; border: 1px solid #f1aeb5; }
        @media (max-width: 768px) { .settings-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 YouTube Downloader Pro</h1>
            <p>High-performance video downloader with web interface</p>
        </div>

        <div class="card">
            <h2>Add Videos</h2>
            <div class="form-group">
                <label for="urls">YouTube URLs (one per line):</label>
                <textarea id="urls" placeholder="Paste YouTube URLs here..."></textarea>
            </div>
            <button class="btn btn-primary" onclick="addUrls()">Add to Queue</button>
            <button class="btn btn-secondary" onclick="clearInput()">Clear</button>
        </div>

        <div class="card">
            <h2>Settings</h2>
            <div class="settings-grid">
                <div class="form-group">
                    <label for="downloadDir">Download Directory:</label>
                    <input type="text" id="downloadDir" value="">
                </div>
                <div class="form-group">
                    <label for="videoQuality">Video Quality:</label>
                    <select id="videoQuality">
                        <option value="best">Best Quality</option>
                        <option value="1080p">1080p</option>
                        <option value="720p">720p</option>
                        <option value="480p">480p</option>
                        <option value="360p">360p</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="maxConcurrent">Concurrent Downloads:</label>
                    <input type="number" id="maxConcurrent" min="1" max="10" value="3">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="saveDescriptions"> Save video descriptions
                    </label>
                </div>
            </div>
            <button class="btn btn-primary" onclick="saveSettings()">Save Settings</button>
        </div>

        <div class="card">
            <h2>Download Queue</h2>
            <div style="margin-bottom: 15px;">
                <button class="btn btn-success" id="startBtn" onclick="startDownload()">Start Download</button>
                <button class="btn btn-danger" id="stopBtn" onclick="stopDownload()" disabled>Stop</button>
                <button class="btn btn-secondary" onclick="clearQueue('completed')">Clear Completed</button>
                <button class="btn btn-secondary" onclick="clearQueue('all')">Clear All</button>
            </div>
            
            <div id="queueContainer">
                <table class="queue-table">
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Speed</th>
                        </tr>
                    </thead>
                    <tbody id="queueBody">
                        <tr><td colspan="4" style="text-align: center; color: #6c757d;">No items in queue</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let isDownloading = false;

        // Load settings on page load
        window.onload = function() {
            loadSettings();
            updateQueue();
            setInterval(updateQueue, 2000); // Update every 2 seconds
        };

        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();
                
                document.getElementById('downloadDir').value = settings.download_dir;
                document.getElementById('videoQuality').value = settings.video_quality;
                document.getElementById('maxConcurrent').value = settings.max_concurrent;
                document.getElementById('saveDescriptions').checked = settings.save_descriptions;
            } catch (error) {
                showMessage('Error loading settings', 'error');
            }
        }

        async function saveSettings() {
            const settings = {
                download_dir: document.getElementById('downloadDir').value,
                video_quality: document.getElementById('videoQuality').value,
                max_concurrent: parseInt(document.getElementById('maxConcurrent').value),
                save_descriptions: document.getElementById('saveDescriptions').checked
            };

            try {
                await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                showMessage('Settings saved successfully', 'success');
            } catch (error) {
                showMessage('Error saving settings', 'error');
            }
        }

        async function addUrls() {
            const urls = document.getElementById('urls').value;
            if (!urls.trim()) {
                showMessage('Please enter at least one URL', 'error');
                return;
            }

            try {
                const response = await fetch('/api/add_urls', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ urls })
                });

                const result = await response.json();
                if (response.ok) {
                    showMessage(result.message, 'success');
                    document.getElementById('urls').value = '';
                    updateQueue();
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('Error adding URLs', 'error');
            }
        }

        async function startDownload() {
            try {
                const response = await fetch('/api/start_download', { method: 'POST' });
                const result = await response.json();
                
                if (response.ok) {
                    isDownloading = true;
                    document.getElementById('startBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    showMessage('Download started', 'success');
                } else {
                    showMessage(result.error, 'error');
                }
            } catch (error) {
                showMessage('Error starting download', 'error');
            }
        }

        async function stopDownload() {
            try {
                await fetch('/api/stop_download', { method: 'POST' });
                isDownloading = false;
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                showMessage('Download stopped', 'success');
            } catch (error) {
                showMessage('Error stopping download', 'error');
            }
        }

        async function clearQueue(type) {
            try {
                await fetch('/api/clear_queue', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type })
                });
                updateQueue();
                showMessage('Queue cleared', 'success');
            } catch (error) {
                showMessage('Error clearing queue', 'error');
            }
        }

        async function updateQueue() {
            try {
                const response = await fetch('/api/queue');
                const queue = await response.json();
                
                const tbody = document.getElementById('queueBody');
                
                if (queue.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #6c757d;">No items in queue</td></tr>';
                    return;
                }

                tbody.innerHTML = queue.map(item => `
                    <tr>
                        <td>${item.title}</td>
                        <td><span class="status-${item.status.toLowerCase()}">${item.status}</span></td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${item.progress}%"></div>
                            </div>
                            ${item.progress}%
                        </td>
                        <td>${item.speed}</td>
                    </tr>
                `).join('');

            } catch (error) {
                console.error('Error updating queue:', error);
            }
        }

        function clearInput() {
            document.getElementById('urls').value = '';
        }

        function showMessage(text, type) {
            const existing = document.querySelector('.message');
            if (existing) existing.remove();

            const msg = document.createElement('div');
            msg.className = `message ${type}`;
            msg.textContent = text;
            
            const container = document.querySelector('.container');
            container.insertBefore(msg, container.firstChild.nextSibling);
            
            setTimeout(() => msg.remove(), 5000);
        }
    </script>
</body>
</html>
'''

# Create templates directory and save template
def create_template():
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    with open(templates_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(template_html)

def main():
    """Main function to start the web server"""
    create_template()
    
    # Get host and port
    host = '127.0.0.1'
    port = 5000
    
    print(f"YouTube Downloader Pro - Web Interface")
    print(f"Starting server at http://{host}:{port}")
    print("Opening browser...")
    
    # Open browser after short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://{host}:{port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start Flask app
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == "__main__":
    # Install Flask if not available
    try:
        import flask
    except ImportError:
        print("Installing Flask...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
        import flask
    
    main()