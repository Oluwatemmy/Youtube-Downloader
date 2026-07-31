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
# Small inline C# wrapper over IPropertyStore so we can stamp the shortcut
# with an AppUserModelID. Without this, Windows toast notifications from
# the app can't find the shortcut and fall back to the default Python /
# generic icon instead of assets/icon.ico.
Add-Type -Namespace YT -Name PropStore -MemberDefinition @'
[System.Runtime.InteropServices.ComImport, System.Runtime.InteropServices.Guid("00021401-0000-0000-C000-000000000046")]
public class CShellLink {}

[System.Runtime.InteropServices.ComImport, System.Runtime.InteropServices.Guid("0000010b-0000-0000-C000-000000000046"),
 System.Runtime.InteropServices.InterfaceType(System.Runtime.InteropServices.ComInterfaceType.InterfaceIsIUnknown)]
public interface IPersistFile {
    [System.Runtime.InteropServices.PreserveSig] int GetClassID(out System.Guid pClassID);
    [System.Runtime.InteropServices.PreserveSig] int IsDirty();
    void Load([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string pszFileName, uint dwMode);
    void Save([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string pszFileName, [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)] bool fRemember);
    void SaveCompleted([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] string pszFileName);
    void GetCurFile([System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] out string ppszFileName);
}

[System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential, Pack = 4)]
public struct PROPERTYKEY {
    public System.Guid fmtid;
    public uint pid;
}

[System.Runtime.InteropServices.ComImport, System.Runtime.InteropServices.Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"),
 System.Runtime.InteropServices.InterfaceType(System.Runtime.InteropServices.ComInterfaceType.InterfaceIsIUnknown)]
public interface IPropertyStore {
    void GetCount(out uint cProps);
    void GetAt(uint iProp, out PROPERTYKEY pkey);
    void GetValue(ref PROPERTYKEY key, [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Struct)] out object pv);
    void SetValue(ref PROPERTYKEY key, [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Struct)] ref object pv);
    void Commit();
}
'@

function Set-ShortcutAumid([string]$LinkPath, [string]$Aumid) {
    $link = New-Object YT.PropStore+CShellLink
    ([YT.PropStore+IPersistFile]$link).Load($LinkPath, 0)
    $key = New-Object YT.PropStore+PROPERTYKEY
    $key.fmtid = [System.Guid]"9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"  # System.AppUserModel.ID
    $key.pid   = 5
    $val = [object]$Aumid
    ([YT.PropStore+IPropertyStore]$link).SetValue([ref]$key, [ref]$val)
    ([YT.PropStore+IPropertyStore]$link).Commit()
    ([YT.PropStore+IPersistFile]$link).Save($LinkPath, $true)
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
