# Uninstall script -- removes the app, shortcuts, and the uninstall
# registry entry. Preserves user data by default (settings, queue,
# history, downloaded files) so a reinstall picks up where it left off.

$ErrorActionPreference = "Stop"

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
Get-Process YouTManager -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 400

# --- Remove app files -------------------------------------------------
if (Test-Path $InstallDir) {
    Write-Host "  Removing $InstallDir ..."
    # Try a few times -- Windows may still hold locks on freshly-closed
    # WebView2 subprocess resources.
    for ($i = 0; $i -lt 5; $i++) {
        try {
            Remove-Item -Recurse -Force $InstallDir
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (Test-Path $InstallDir) {
        Write-Host "  Warning: could not fully remove $InstallDir" -ForegroundColor Yellow
        Write-Host "  Some files may be locked. Delete manually after logging out."
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
