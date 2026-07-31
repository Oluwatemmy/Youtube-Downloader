# Install script -- copies YouTManager into %LOCALAPPDATA%\Programs\
# and creates Start Menu (and optionally Desktop) shortcuts.
# Registers an uninstaller so the app appears in Settings > Apps.
#
# Runs per-user (no admin needed).
# Invoked from install.bat with -ExecutionPolicy Bypass.

$ErrorActionPreference = "Stop"

# Show a real error message and pause instead of the CMD window vanishing
# when something throws — otherwise users can't tell us what failed.
trap {
    Write-Host ""
    Write-Host "  Install failed:" -ForegroundColor Red
    Write-Host "    $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ScriptStackTrace) {
        Write-Host ""
        Write-Host "  Where:" -ForegroundColor DarkGray
        Write-Host "    $($_.ScriptStackTrace -replace "`n", "`n    ")" -ForegroundColor DarkGray
    }
    Write-Host ""
    Read-Host "  Press Enter to close"
    exit 1
}

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
    # Kill the app AND its WebView2 subprocesses. WebView2 spawns
    # msedgewebview2.exe children that outlive the parent by a few
    # hundred ms and keep the .exe / DLLs locked, which makes the copy
    # step below fail with "Access denied" if we don't clear them first.
    Get-Process YouTManager     -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process msedgewebview2  -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -like "$InstallDir*" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    # Give the OS a moment to release handles, then remove and wait for
    # the folder to actually be gone before continuing.
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Milliseconds 400
        try {
            Remove-Item -Recurse -Force $InstallDir -ErrorAction Stop
            break
        } catch {
            if ($i -eq 9) { throw "Could not remove existing install after 10 attempts: $($_.Exception.Message)" }
        }
    }
    while (Test-Path $InstallDir) { Start-Sleep -Milliseconds 200 }
}

# --- Copy the app -----------------------------------------------------
Write-Host "  Copying files to $InstallDir ..."
$null = New-Item -ItemType Directory -Force -Path (Split-Path $InstallDir)
# Robocopy handles antivirus-locked files better than Copy-Item — has
# built-in retry (/R:5 W:1) and mirrors the source tree exactly. Exit
# codes 0-7 are success (files copied / already same); 8+ is real error.
$robocopyOut = & robocopy $SourceDir $InstallDir /MIR /R:5 /W:1 /NP /NDL /NJH /NJS 2>&1
if ($LASTEXITCODE -ge 8) {
    Write-Host $robocopyOut
    throw "robocopy failed with exit code $LASTEXITCODE"
}

$Exe = Join-Path $InstallDir "$AppName.exe"
if (-not (Test-Path $Exe)) {
    Write-Host "  Install failed - $Exe not found after copy" -ForegroundColor Red
    exit 1
}

# --- Shortcuts --------------------------------------------------------
# Small inline C# wrapper over IPropertyStore so we can stamp the shortcut
# with an AppUserModelID. Without this, Windows toast notifications from
# the app can't find the shortcut and fall back to the default Python /
# generic icon instead of assets/icon.ico.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace YT {
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    public class CShellLink {}

    [ComImport, Guid("0000010b-0000-0000-C000-000000000046"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPersistFile {
        [PreserveSig] int GetClassID(out Guid pClassID);
        [PreserveSig] int IsDirty();
        void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
        void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName,
                  [MarshalAs(UnmanagedType.Bool)] bool fRemember);
        void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
        void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PROPERTYKEY {
        public Guid fmtid;
        public uint pid;
    }

    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore {
        void GetCount(out uint cProps);
        void GetAt(uint iProp, out PROPERTYKEY pkey);
        void GetValue(ref PROPERTYKEY key,
                      [MarshalAs(UnmanagedType.Struct)] out object pv);
        void SetValue(ref PROPERTYKEY key,
                      [MarshalAs(UnmanagedType.Struct)] ref object pv);
        void Commit();
    }
}
'@ -ErrorAction SilentlyContinue

function Set-ShortcutAumid([string]$LinkPath, [string]$Aumid) {
    # Activate the ShellLink COM class by CLSID — the returned RCW is a
    # generic __ComObject, and PowerShell's `-as` operator on it triggers
    # a real COM QueryInterface (a plain [Type]$obj cast doesn't).
    $type = [Type]::GetTypeFromCLSID([Guid]'00021401-0000-0000-C000-000000000046')
    $link = [Activator]::CreateInstance($type)

    $pf = $link -as [YT.IPersistFile]
    if (-not $pf) { throw "QI to IPersistFile failed" }
    $pf.Load($LinkPath, 0)

    $key = New-Object YT.PROPERTYKEY
    $key.fmtid = [System.Guid]"9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"  # System.AppUserModel.ID
    $key.pid   = 5
    $val = [object]$Aumid

    $ps = $link -as [YT.IPropertyStore]
    if (-not $ps) { throw "QI to IPropertyStore failed" }
    $ps.SetValue([ref]$key, [ref]$val)
    $ps.Commit()

    $pf.Save($LinkPath, $true)

    # Release RCWs so the file handle drops immediately (otherwise a
    # subsequent Save from a second call can race on the same lock).
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ps)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($pf)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($link)
}

function New-Shortcut([string]$LinkPath, [string]$TargetPath, [string]$IconPath) {
    $wsh = New-Object -ComObject WScript.Shell
    $sc  = $wsh.CreateShortcut($LinkPath)
    $sc.TargetPath       = $TargetPath
    $sc.WorkingDirectory = Split-Path $TargetPath
    $sc.IconLocation     = $IconPath
    $sc.Save()
    # Stamp the AUMID so toast notifications inherit the app icon.
    try { Set-ShortcutAumid $LinkPath "YouTManager" } catch { Write-Host "  (warning: could not set AUMID: $_)" }
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
