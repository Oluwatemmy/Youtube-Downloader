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

## Who this is for

If you download YouTube videos more than "once in a while" and any of these
sound familiar, this is built for you:

- You want to **watch videos offline** on flights, on the road, or while your
  internet is being weird
- You **edit clips** out of YouTube content (for personal projects, memes,
  reactions, study notes) and need the raw file, not a screen recording
- You **rip audio** from music videos, podcasts, lectures, or interviews to
  listen on the go
- You save **lectures / tutorials / how-to videos** for reference — Python
  full courses, cooking playlists, DIY channels
- You back up **your own uploads** or channel content you want to keep even
  if the creator deletes it
- You just prefer **your own player** (VLC, MPC, PotPlayer) over YouTube's
  chrome — better volume control, playback speed, hotkeys, no ads

**What it's not:** it's not for hosting a redistribution site, not for
mass-scraping channels for a dataset, and not for downloading paid content
you don't own. Use it in line with YouTube's terms and the creator's rights.

### Privacy

**Everything stays on your machine.** No signups, no accounts on our end,
no telemetry, no phone-home. The app talks to two servers: YouTube
(to fetch the videos you asked for) and PyPI (only when you click Check
for updates on yt-dlp). Your queue, history, cookies, and downloaded
files live in `%APPDATA%\YouTubeDownloader\` and your chosen download
folder — nobody else can see any of it unless you copy it out yourself.

## What it does

- **Real per-video format list** — after you paste a URL the Quality dropdown
  fills with the actual streams YouTube has for that video, each with its
  file size (`1080p MP4 · 138 MB`), not a guess-and-hope generic ladder.
  Sizes only show when yt-dlp actually knows them — no misleading estimates
- **Video preview in Add URL** — thumbnail, title, uploader, duration, and
  view count populate a card as soon as metadata is fetched, so you know
  you pasted the right link before hitting Download
- **MP3 extraction** with a bitrate ladder (320 / 256 / 192 / 128 / 96 kbps)
  — pulls the audio and produces a real `.mp3` via FFmpeg, not just the
  source audio stream
- **Playlist support** — paste a playlist URL, get a checklist of videos;
  batch or subset, all queued into a subfolder named after the playlist
- **Subtitle dropdown in Add URL** — lists every language YouTube has for
  the video (English, Spanish, French, etc., with `(auto)` on
  machine-transcribed tracks). Pick one and it gets embedded into the
  `.mp4` as a soft subtitle track, so the final file is one tidy video
  with toggleable subs in VLC / Movies & TV. Hidden when the video has
  no subtitles or you're in Audio (MP3) mode.
- **Duplicate detection** — paste a URL you've already downloaded and get
  a styled prompt showing how many copies you have and the latest
  filename; Open file / Show in queue / Download again. "Download again"
  saves as `Title (1).mp4` so the original stays intact. Prompt is
  skipped if you'd already deleted the earlier file. Bulk playlist and
  multi-URL adds get a single summary prompt ("3 of 20 already exist —
  skip duplicates / download all / cancel").
- **Playlist picker with availability chips** — enumerates the whole
  playlist quickly, marks Private / Deleted / Copyright-blocked /
  Region-blocked / Members-only entries with a chip and a lock icon so
  you don't accidentally queue up dead URLs
- **Bundled QuickJS** for YouTube's `nsig` signature decryption — no
  external Node or Deno install needed. Ships in `bin/qjs.exe` (~1.8 MB)
- **Age-restricted retry** — when yt-dlp's default clients hit an age
  gate, the app automatically retries with the `tv_embedded` player
  client + cookies (the only combo that YouTube accepts for age-gated
  content). Needs cookies from a signed-in adult account.
- **URL normalization** — strips the auto-radio garbage YouTube attaches
  to Music links (`&list=RD…&start_radio=1&pp=…`) so single-video adds
  don't waste time enumerating a bogus playlist context
- **Cookies-friendly** — a first-run wizard walks you through exporting
  `cookies.txt` from a browser extension so YouTube's 2026 bot check
  doesn't gate you to 360p
- **Auto-installs FFmpeg** on first launch (~100 MB, one-time) so 1080p+
  merging works without any manual setup
- **Live per-item speed chart and log** — click a row, watch its throughput
  in the Speed tab, read yt-dlp's own output in the Log tab. Logs persist
  to disk across app restarts and have a **Copy log** button so you can
  paste the exact output into a bug report.
- **Clear progress across stages** — during a video with subtitles + audio,
  the progress bar climbs monotonically instead of bouncing. Speed column
  shows what's currently happening: `4.5 MB/s ETA 2m` (video) →
  `audio · 1.3 MB/s ETA 4m` (audio stream) → `Merging…` (ffmpeg mux) →
  Done at 100%.
- **Real Pause vs Stop** — pause keeps the `.part` file so Resume continues;
  Stop discards it so the next attempt starts fresh
- **Delete cleans up thoroughly** — removes the video file, its `.part`
  fragments, any `.vtt` / `.srt` subtitles, and the `.description` / info
  files. Won't touch sibling `Title (1).mp4` duplicates from prior
  re-downloads.
- **Windows-native window** — proper drag, resize, min/max, snap-to-edges;
  dark and light themes
- **Per-video Windows toast** — one notification per completed / failed
  download with that video's title, so a queue of 5 videos produces 5
  clear toasts (not "5 complete" accumulated). Suppressed while the app
  window is focused.
- **Speed limit** — per-download cap in Settings → Advanced (`500K`, `1M`);
  useful when you don't want a queue to hog bandwidth
- **Persistent queue and history** — quit mid-download, reopen, everything
  is there. Analytics tab has date-range + status + search filters,
  paginated history table, and shows totals + per-day chart. History rows
  show the actual on-disk filename so re-downloaded copies read as
  `Title`, `Title (1)`, `Title (2)`.
- **Clipboard detection** — copy a YouTube URL, alt-tab to the app, get a
  one-click prompt to add it
- **Friendly errors** — raw yt-dlp errors get translated into actionable
  messages: rate-limited (wait an hour or use cookies), age-restricted
  (set cookies), private, region-blocked, 403 (session expired), 5xx
  (YouTube outage), network unreachable
- **yt-dlp auto-updater** — Settings has a "Check for updates" button and
  a quiet weekly check that shows a dot in the sidebar when a new release
  is out. Sticks to stable releases (nightlies can regress the size column).
- **Report an issue** — link in the sidebar footer and Settings that opens
  the GitHub issues page in your default browser
- **Crash handler** — uncaught errors surface as a real dialog with the
  traceback and a Copy button, instead of dying to stderr

## Install

### For use (recommended)

1. Go to the [Releases page](https://github.com/Oluwatemmy/Youtube-Downloader/releases)
   and download the latest `YouTManager-*.zip`
2. Extract it anywhere (e.g. your Downloads folder)
3. Double-click `install.bat` inside the extracted folder
4. Windows SmartScreen may show a "Windows protected your PC" dialog — click
   **More info** → **Run anyway**. This is because the installer isn't
   code-signed (a solo-developer thing; you can verify the source in this
   repo). The `.bat` runs the PowerShell install script, which copies the
   app to `%LOCALAPPDATA%\Programs\YouTManager\` and creates Start Menu +
   Desktop shortcuts. No admin rights needed.

Uninstall via **Settings → Apps → YouT Manager → Uninstall**, or run
`uninstall.ps1` from the install folder directly. The uninstaller asks
whether to also wipe `%APPDATA%\YouTubeDownloader\` (settings / queue /
history) — defaults to keeping it, so a reinstall picks up where you left off.

### From source (developers)

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

To build the packaged version:

```powershell
scripts\build.ps1 -Version 1.0.0
```

Produces `dist\YouTManager\YouTManager.exe` and a distributable
`dist\YouTManager-1.0.0.zip` (installer scripts + app folder, ~22 MB).

### First launch (either path)

1. If FFmpeg isn't already on your PATH, the app downloads a static build
   to `<app>/ffmpeg/bin/` (~100 MB). One-time.
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
Two possible causes; the app's diagnosis line under the Quality dropdown
will say which one:
- Bundled `bin\qjs.exe` is missing or antivirus-quarantined — the JS
  runtime that decrypts YouTube's `nsig` signature isn't reachable, so
  yt-dlp only sees low-res streams. Restore the file or install Node.js.
- Cookies aren't reaching yt-dlp. Either the cookies file wasn't picked,
  the Chrome cookie DB is locked (close Chrome), or your session expired
  (re-export).

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
launcher.py                 Bootstrap: picks the pywebview UI if
                            available, otherwise falls back to Tkinter
install.bat                 User-facing installer entry (calls the PS
                            script with -ExecutionPolicy Bypass)

app/                        Runtime Python
  main.py                     pywebview entry, ffmpeg auto-install
  bridge.py                   DownloadManager, PyBridge JS API,
                              persistence, cookies fallback chain
  legacy_gui.py               Tkinter fallback UI
  legacy_backend.py           Async yt-dlp wrapper for legacy_gui

ui/                         Single-page frontend (the "YouT Manager" design)
  index.html                  Markup
  styles.css                  Design tokens + component styles
  app.js                      State, rendering, dialogs, playlist picker,
                              crash modal, clipboard prompt

assets/                     App icon (multi-resolution .ico + png/icns)
bin/                        Bundled QuickJS binary (~1.8 MB) — yt-dlp
                            needs a JS runtime to decrypt YouTube's nsig
                            signature; without it many videos would fail
                            with "Requested format is not available"
scripts/                    Dev + build tooling
  create_icon.py              Renders the icon from the design
  build.ps1                   Reproducible build (venv + PyInstaller + zip)
  install.ps1                 Copies to %LOCALAPPDATA%, creates shortcuts,
                              registers uninstaller in Settings > Apps
  uninstall.ps1               Reverse of install; asks about user data
packaging/
  youtube_downloader.spec     PyInstaller spec (one-folder, --windowed)
docs/                       Screenshot + release-facing docs
```

Downloads are managed by `DownloadManager` (a thread-pool wrapping yt-dlp
calls). The frontend talks to `PyBridge` via `window.pywebview.api.<method>`;
progress and log events push the other way via
`window.evaluate_js('window.onEvent(...)')`.

## Roadmap

Rough order of what's next:

- Code-signed installer — removes the SmartScreen prompt and the "unknown
  publisher" reputation reset on every rebuild
- AUMID stamping fix — so toast notifications pick up the app icon
  (currently they fall back to a generic Windows icon)
- Minimize to tray for long-running queues
- Auto-follow OS theme (currently a manual toggle)
- Drag-and-drop URLs from the browser
- PO token / bgutil sidecar — for the "age-restricted and only available
  on YouTube" class of videos that need a full authenticated web client.
  Currently not shipped because it adds ~250 MB of Node runtime.

## Reporting bugs

The **Report an issue** link in the sidebar footer (and in Settings →
Advanced) opens the GitHub issues page in your browser. When you file
one, the more of this you can include, the faster it gets fixed:

1. **What you did** — the URL you pasted, the quality you picked, whether
   subtitles were on, whether cookies were set, etc.
2. **What you expected** vs **what happened**
3. **The per-video log** — click the affected row → **Log** tab → **Copy
   log** button (top-right of the pane) → paste into the issue. This is
   yt-dlp's own output for THAT specific download and usually tells us
   exactly what YouTube returned.
4. **Screenshots** if the UI is wrong (progress stuck, filename off, etc.)
5. **Your yt-dlp version** — shown at the bottom of the sidebar
   (e.g. `v1.0.0 · yt-dlp 2026.07.04`)

Please **redact any personal info** from cookies files before attaching
them. Better: describe whether cookies were set, don't upload them.

## Contributing

Contributions are welcome — this is a small hobby project and any polish
is appreciated. Rough guidelines:

- **Bugs first, features second.** If you see something broken (in the UI
  or a specific YouTube behaviour), a fix PR is very welcome.
- **Talk before big changes.** For anything larger than a bug fix — new
  tabs, new panels, restructuring — open an issue first so we can align
  on the approach before you spend hours on it.
- **Match the existing style.** Python code is fairly conventional; JS
  uses vanilla DOM (no frameworks); PowerShell scripts stay `-NoProfile`
  and use the `trap` pattern for visible errors. CSS uses design tokens
  from `styles.css` — don't hardcode colours.
- **Test in dev mode** — `venv\Scripts\python launcher.py` runs against
  live source. If your change affects the packaged exe (PyInstaller spec,
  install scripts), test with a fresh build via `scripts\build.ps1`.
- **Keep the installer small.** The current ~27 MB is a feature; be
  cautious about adding heavy dependencies. If you want to add PO token
  support / bgutil / Node bundling / etc., open an issue first — the
  size trade-off was intentional.
- **Update the README** — add your feature to the "What it does" list
  (or move an item from "Roadmap") and credit yourself in the Credits.

Fork → branch → commit → PR. No CLA, no lawyers, just be nice.

### Ideas for contributors

Small pickings:
- Subtitle language picker: remember the last-used language as the default
- Playlist picker: bulk-invert selection (currently only "Select all" /
  "Clear")
- Analytics: bar chart of downloads per hour-of-day
- Right-click "Copy shareable URL" that omits the noisy tracking params

Bigger ones:
- Any item from the Roadmap above
- macOS / Linux support (currently Windows-only for the packaged install;
  the app itself runs on any pywebview-supported platform)
- Auto-updater for the app itself (not just yt-dlp) — check GitHub
  releases, download new zip, install in place

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — does the actual heavy lifting
- [pywebview](https://pywebview.flowrl.com/) — Python + native WebView2
- [Ajayi Oluwaseyi Temitope](https://github.com/Oluwatemmy) — author,
  design, and the whole application layer
- [QuickJS-NG](https://github.com/quickjs-ng/quickjs) — bundled JavaScript
  runtime used to decrypt YouTube's `nsig` signature
- [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) — static
  Windows FFmpeg used by the auto-installer
- [truststore](https://truststore.readthedocs.io/) — makes Python's ssl use
  the Windows cert store, without which antivirus HTTPS scanning breaks
  every request
- [winotify](https://pypi.org/project/winotify/) — Windows toast
  notifications for finished downloads
- [@reissbruno](https://github.com/reissbruno) — proposed MP3 extraction in
  [PR #5](https://github.com/Oluwatemmy/Youtube-Downloader/pull/5); the
  current dialog toggle borrows the "format as top-level choice" idea

## License

MIT — see [LICENSE](LICENSE).
