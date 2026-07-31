# Uninstall script -- removes the app, shortcuts, and the uninstall
# registry entry. Preserves user data by default (settings, queue,
# history, downloaded files) so a reinstall picks up where it left off.

$ErrorActionPreference = "Stop"

# Same visible-error pattern as install.ps1 — surface the real message
# instead of the CMD window silently closing on failure.
trap {
    Write-Host ""
    Write-Host "  Uninstall failed:" -ForegroundColor Red
    Write-Host "    $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Read-Host "  Press Enter to close"
    exit 1
}

$AppName    = "YouTManager"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
$SmLnk      = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName.lnk"
$DeskLnk    = Join-Path $env:USERPROFILE "Desktop\$AppName.lnk"
$UninstKey  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
$UserData   = Join-Path $env:APPDATA "YouTubeDownloader"

Write-Host ""
Write-Host "  YouT Manager - uninstall" -ForegroundColor Cyan
Write-Host "  ------------------------" -ForegroundColor Cyan
Write-Host "  Install location: $InstallDir"

$reply = Read-Host "  Uninstall? [y/N]"
if ($reply -notmatch "^[Yy]") {
    Write-Host "  Cancelled." -ForegroundColor Yellow
    exit 0
}

# --- Kill any running instance ---------------------------------------
# Kill the app AND its WebView2 subprocesses. Just killing YouTManager
# leaves msedgewebview2.exe children alive for a few hundred ms, and
# those children keep DLLs locked so the folder can't be removed.
Get-Process YouTManager     -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process msedgewebview2  -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "$InstallDir*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 600

# --- Remove app files -------------------------------------------------
if (Test-Path $InstallDir) {
    Write-Host "  Removing $InstallDir ..."
    # Delete files one-by-one (skipping locked ones) then the folder — a
    # single Remove-Item -Recurse aborts on the first locked file and
    # leaves everything else behind.
    for ($i = 0; $i -lt 8; $i++) {
        Get-ChildItem $InstallDir -Recurse -File -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        try {
            Remove-Item -Recurse -Force $InstallDir -ErrorAction Stop
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (Test-Path $InstallDir) {
        Write-Host "  Warning: could not fully remove $InstallDir" -ForegroundColor Yellow
        Write-Host "  Some files stayed locked (typically Windows Defender / Search Indexer)." -ForegroundColor Yellow
        Write-Host "  Reboot and delete the folder manually, or re-run this script after reboot." -ForegroundColor Yellow
    }
}

# --- Remove shortcuts -------------------------------------------------
foreach ($lnk in @($SmLnk, $DeskLnk)) {
    if (Test-Path $lnk) {
        Remove-Item -Force $lnk
        Write-Host "  Removed shortcut: $lnk"
    }
}

# --- Remove uninstall registry entry ---------------------------------
if (Test-Path $UninstKey) {
    Remove-Item -Recurse -Force $UninstKey
    Write-Host "  Removed uninstall registry entry"
}

# --- Ask about user data ---------------------------------------------
if (Test-Path $UserData) {
    Write-Host ""
    Write-Host "  User data folder: $UserData"
    Write-Host "  Contains: settings.json, queue.json, history.json, cookies path"
    $wipe = Read-Host "  Also delete user data? [y/N]"
    if ($wipe -match "^[Yy]") {
        Remove-Item -Recurse -Force $UserData
        Write-Host "  User data removed."
    } else {
        Write-Host "  Kept - a reinstall will pick up where you left off."
    }
}

Write-Host ""
Write-Host "  Uninstall complete." -ForegroundColor Green
Read-Host "  Press Enter to close"
