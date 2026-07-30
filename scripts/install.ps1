# Install script -- copies YouTManager into %LOCALAPPDATA%\Programs\
# and creates Start Menu (and optionally Desktop) shortcuts.
# Registers an uninstaller so the app appears in Settings > Apps.
#
# Runs per-user (no admin needed).
# Invoked from install.bat with -ExecutionPolicy Bypass.

$ErrorActionPreference = "Stop"

$AppName    = "YouTManager"
$Publisher  = "Oluwatemmy"
$SourceDir  = Join-Path $PSScriptRoot "YouTManager"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
$SmDir      = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$SmLnk      = Join-Path $SmDir "$AppName.lnk"
$DeskLnk    = Join-Path $env:USERPROFILE "Desktop\$AppName.lnk"
$UninstKey  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"

Write-Host ""
Write-Host "  YouT Manager - install" -ForegroundColor Cyan
Write-Host "  ----------------------" -ForegroundColor Cyan

if (-not (Test-Path $SourceDir)) {
    Write-Host "  Source folder not found: $SourceDir" -ForegroundColor Red
    Write-Host "  Extract the zip first, then run install.bat from the extracted folder."
    Read-Host "  Press Enter to close"
    exit 1
}

# --- Overwrite check --------------------------------------------------
if (Test-Path $InstallDir) {
    Write-Host "  Existing install found at $InstallDir"
    $reply = Read-Host "  Overwrite? [Y/n]"
    if ($reply -match "^[Nn]") {
        Write-Host "  Cancelled." -ForegroundColor Yellow
        exit 0
    }
    # Kill any running instance so we can overwrite the .exe
    Get-Process YouTManager -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Milliseconds 400
    Remove-Item -Recurse -Force $InstallDir
}

# --- Copy the app -----------------------------------------------------
Write-Host "  Copying files to $InstallDir ..."
$null = New-Item -ItemType Directory -Force -Path (Split-Path $InstallDir)
Copy-Item -Recurse $SourceDir $InstallDir

$Exe = Join-Path $InstallDir "$AppName.exe"
if (-not (Test-Path $Exe)) {
    Write-Host "  Install failed - $Exe not found after copy" -ForegroundColor Red
    exit 1
}

# --- Shortcuts --------------------------------------------------------
function New-Shortcut([string]$LinkPath, [string]$TargetPath, [string]$IconPath) {
    $wsh = New-Object -ComObject WScript.Shell
    $sc  = $wsh.CreateShortcut($LinkPath)
    $sc.TargetPath       = $TargetPath
    $sc.WorkingDirectory = Split-Path $TargetPath
    $sc.IconLocation     = $IconPath
    $sc.Save()
}

$IconPath = Join-Path $InstallDir "assets\icon.ico"
if (-not (Test-Path $IconPath)) { $IconPath = $Exe }

Write-Host "  Creating Start Menu shortcut ..."
$null = New-Item -ItemType Directory -Force -Path $SmDir
New-Shortcut $SmLnk $Exe $IconPath

$deskReply = Read-Host "  Also create a Desktop shortcut? [Y/n]"
if ($deskReply -notmatch "^[Nn]") {
    New-Shortcut $DeskLnk $Exe $IconPath
    Write-Host "  Desktop shortcut created."
}

# --- Register with Windows so it shows up in Settings > Apps ---------
Write-Host "  Registering uninstaller ..."
$null = New-Item -Path $UninstKey -Force
Set-ItemProperty $UninstKey -Name "DisplayName"      -Value "YouT Manager"
Set-ItemProperty $UninstKey -Name "DisplayIcon"      -Value $IconPath
Set-ItemProperty $UninstKey -Name "Publisher"        -Value $Publisher
Set-ItemProperty $UninstKey -Name "InstallLocation"  -Value $InstallDir
Set-ItemProperty $UninstKey -Name "NoModify"         -Value 1 -Type DWord
Set-ItemProperty $UninstKey -Name "NoRepair"         -Value 1 -Type DWord
# The uninstaller command Windows invokes:
$UninstallCmd = "powershell.exe -ExecutionPolicy Bypass -File `"$InstallDir\uninstall.ps1`""
Set-ItemProperty $UninstKey -Name "UninstallString"  -Value $UninstallCmd

# Copy the uninstall script into the install dir so Windows can call it
Copy-Item (Join-Path $PSScriptRoot "uninstall.ps1") (Join-Path $InstallDir "uninstall.ps1")

Write-Host ""
Write-Host "  Installed to $InstallDir" -ForegroundColor Green
Write-Host "  Launch: Start Menu -> YouTManager, or double-click the desktop shortcut."
Write-Host ""

$launchReply = Read-Host "  Launch now? [Y/n]"
if ($launchReply -notmatch "^[Nn]") {
    Start-Process $Exe
}
