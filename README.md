# YouT Manager

A Windows desktop YouTube downloader — batch queue, real per-video format
picker, MP3 extraction, playlists, and a first-run cookies flow so 1080p and
above actually work in 2026.

<p align="left">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2B-lightgrey" alt="Windows 10+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
  <img src="https://img.shields.io/badge/UI-pywebview-red" alt="pywebview UI">
</p>

<!-- Drop a screenshot into docs/screenshot.png and it'll show up here -->
![Screenshot of YouT Manager main view](docs/screenshot.png)

## Why this exists

I wanted to download a YouTube video to watch on my laptop with a proper
player — the built-in volume in YouTube's own player was too quiet, and I
wanted to edit clips out of it. Online "YouTube to MP4" sites were flaky,
throttled, or capped at 720p. Meanwhile the exact tool that could do it well
(`yt-dlp`) already existed as a Python library, but opening a terminal every
time I want to save a video is friction.

So this is that Python library wearing a proper installable Windows app: copy
a YouTube link, focus the app, and it already knows the URL from your
clipboard. Click Download, and the file lands in your downloads folder ready
to play in VLC / Movies & TV / whatever, or drag into a video editor.

## What it does

- **Real per-video format list** — after you paste a URL the Quality dropdown
  fills with the actual streams YouTube has for that video, each with its
  file size (`1080p MP4 · 138 MB`), not a guess-and-hope generic ladder
- **MP3 extraction** with a bitrate ladder (320 / 256 / 192 / 128 / 96 kbps)
  — pulls the audio and produces a real `.mp3` via FFmpeg, not just the
  source audio stream
- **Playlist support** — paste a playlist URL, get a checklist of videos;
  batch or subset, all queued into a subfolder named after the playlist
- **Cookies-friendly** — a first-run wizard walks you through exporting
  `cookies.txt` from a browser extension so YouTube's 2026 bot check
  doesn't gate you to 360p
- **Auto-installs FFmpeg** on first launch (~100 MB, one-time) so 1080p+
  merging works without any manual setup
- **Live per-item speed chart and log** — click a row, watch its throughput
  in the Speed tab, read yt-dlp's own output in the Log tab
- **Real Pause vs Stop** — pause keeps the `.part` file so Resume continues;
  Stop discards it so the next attempt starts fresh
- **Windows-native window** — proper drag, resize, min/max, snap-to-edges;
  dark and light themes
- **Persistent queue and history** — quit mid-download, reopen, everything
  is there. Analytics tab shows totals + per-day chart
- **Clipboard detection** — copy a YouTube URL, alt-tab to the app, get a
  one-click prompt to add it
- **yt-dlp auto-updater** — Settings has a "Check for updates" button and a
  quiet weekly check that shows a dot in the sidebar when a new release is
  out. YouTube changes their site monthly, so this is important.
- **Crash handler** — uncaught errors surface as a real dialog with the
  traceback and a Copy button, instead of dying to stderr

## Install (from source)

**Requirements:** Windows 10 or 11, Python 3.10+, ~200 MB free (for the
bundled FFmpeg download on first run).

```powershell
git clone https://github.com/Oluwatemmy/Youtube-Downloader.git
cd Youtube-Downloader

python -m venv venv
venv\Scripts\pip install -r requirements.txt

venv\Scripts\python launcher.py
```

Or double-click `run_youtube_downloader.bat` after the venv is set up.

On first launch:

1. If FFmpeg isn't on your PATH, the app downloads a static build to
   `<app>/ffmpeg/bin/` (~100 MB). You'll see a small progress dialog for it.
2. The **cookies setup wizard** opens. Follow it — takes about a minute and
   is the difference between getting 360p and getting 4K on any video.

## Using it

- **Add URL** (or Ctrl+N) — paste a single video URL, playlist URL, or use
  the Multiple URLs tab for a mixed batch
- Switch **Video ↔ Audio (MP3)** at the top of the dialog
- Pick a quality from the real per-video list (or a generic ladder for
  batches / playlists), pick where to save, hit Download
- **Row hover** shows a primary action button that changes with status:
  Pause / Resume / Retry / Open folder
- **Double-click** a completed row to open the file in your default player
  (also right-click → Open file, or Enter with the row selected)
- **Right-click** any row for status-aware actions
- **Analytics tab** — 30-day chart, total downloads, success rate, last 8
  activity entries. Export to CSV from the top-right

## Cookies (the important part)

As of 2026 YouTube gates most high-quality streams behind a "Sign in to
confirm you're not a bot" check. Without valid session cookies, you get 360p
at best and outright rejection on age-restricted / region-locked videos.

**The one-time setup:**

1. Install the browser extension
   [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   (Chromium browsers) or
   [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt-one-click/)
   (Firefox)
2. While signed into YouTube, click the extension icon → **Export** →
   save as `cookies.txt`
3. In the app: **Settings → Advanced → Cookies file** → **Browse…** → pick
   the file
4. That's it. Nothing gets uploaded — the file stays on your machine.

**Alternative:** the "Cookies from browser" dropdown reads directly from
Chrome / Edge / Firefox / Brave / etc. Only catch: Chromium browsers lock
their cookie DB while running, so you'd have to close Chrome first. A
cookies.txt file avoids that.

**Session cookies expire.** If downloads suddenly drop to 360p after
previously working, re-export cookies.txt and Browse to the new file. YouTube
also invalidates sessions on password change, new-device sign-in, or
periodic security refreshes (weeks to months).

## Troubleshooting

**"Only 360p is available."**
Cookies aren't reaching yt-dlp. Either the cookies file wasn't picked, the
Chrome cookie DB is locked (close Chrome), or your session expired
(re-export). Look under the Quality dropdown for the app's own diagnosis.

**"Requested format is not available."**
Usually means yt-dlp is out of date. Settings → **yt-dlp version** → **Check
for updates**. Install → restart the app.

**"HTTP Error 403" on a specific video.**
Either the video is age-restricted (needs signed-in cookies) or your session
expired. Same fix as above.

**Downloads sit at Queued forever.**
Increase `Concurrent downloads` in Settings, or make sure the currently
Downloading item hasn't stalled. Right-click → Stop then Retry as a nuke.

**A row shows the wrong size before completion.**
For fragmented DASH videos the `Size` column shows an estimate mid-download;
the real size lands after the file is written. If it's *still* wrong after
"Done", re-download that item — earlier queue entries were captured before
the size-from-disk fix.

**Where do the logs live?**
Per-row: click the row, then the **Log** tab in the detail panel. Session
crash traces come from the crash modal (Copy details button).

## Config file locations

Everything the app writes lives under `%APPDATA%\YouTubeDownloader\`:

| File | What it holds |
|---|---|
| `settings.json` | UI preferences, cookies path, mp3 bitrate, ffmpeg last-check |
| `queue.json` | Current queue, restored on restart |
| `history.json` | Completed / failed download log — powers Analytics |

Wipe these to fully reset. Downloads themselves go to your chosen download
folder (defaults to `%USERPROFILE%\Downloads\YouTube\`); playlists get their
own subfolder inside it.

FFmpeg (if auto-downloaded) sits in `<app>\ffmpeg\bin\ffmpeg.exe`.

## How it's put together

```
launcher.py                       Bootstrap: picks the pywebview UI if
                                  available, otherwise falls back to Tkinter
youtube_downloader_pywebview.py   Main entry — window + PyBridge
pywebview_bridge.py               Python side: DownloadManager, PyBridge
                                  JS API, persistence, ffmpeg auto-install,
                                  cookies fallback chain
ui/index.html                     Single-page frontend (the "YouT Manager"
                                  design)
ui/styles.css                     Design tokens + component styles
ui/app.js                         State, rendering, dialogs, playlist
                                  picker, crash modal
yt_dlp_enhanced.py                Legacy async backend — only used by the
                                  Tkinter fallback UI
youtube_downloader_gui.py         Legacy Tkinter UI — fallback when
                                  pywebview / WebView2 unavailable
create_icon.py                    Renders the app icon from the design
YouTube app design system/        Reference design mockups (gitignored)
```

Downloads are managed by `DownloadManager` (a thread-pool wrapping yt-dlp
calls). The frontend talks to `PyBridge` via `window.pywebview.api.<method>`;
progress and log events push the other way via
`window.evaluate_js('window.onEvent(...)')`.

## Roadmap

Rough order of what's next:

- Windows installer (PyInstaller + Start Menu shortcut + uninstaller)
- Drag-and-drop URLs from the browser
- Subtitle download option in the Add URL dialog
- Windows toast notification when a batch completes
- Speed limit per download
- Minimize to tray for long-running queues

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — does the actual heavy lifting
- [pywebview](https://pywebview.flowrl.com/) — Python + native WebView2
- [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) — static
  Windows FFmpeg used by the auto-installer
- [truststore](https://truststore.readthedocs.io/) — makes Python's ssl use
  the Windows cert store, without which antivirus HTTPS scanning breaks
  every request
- [@reissbruno](https://github.com/reissbruno) — proposed MP3 extraction in
  [PR #5](https://github.com/Oluwatemmy/Youtube-Downloader/pull/5); the
  current dialog toggle borrows the "format as top-level choice" idea

## License

MIT — see [LICENSE](LICENSE).
