# Build script for YouT Manager
# ------------------------------
# Produces dist\YouTManager\ (folder + .exe) and dist\YouTManager-<ver>.zip.
# Run from the repo root:
#     powershell -ExecutionPolicy Bypass -File scripts\build.ps1
# Or via the wrapper:
#     scripts\build.ps1
#
# Options:
#     -Version 1.0.0     stamped into the zip filename (default: dev)
#     -Clean             wipe .venv-build and dist first

param(
    [string]$Version = "dev",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BuildVenv  = Join-Path $RepoRoot ".venv-build"
$DistDir    = Join-Path $RepoRoot "dist"
$SpecFile   = Join-Path $RepoRoot "packaging\youtube_downloader.spec"

if ($Clean) {
    Write-Host "[clean] removing .venv-build and dist" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BuildVenv -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $DistDir   -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $RepoRoot "build") -ErrorAction SilentlyContinue
}

# --- 1. Fresh venv ---------------------------------------------------
if (-not (Test-Path $BuildVenv)) {
    Write-Host "[venv] creating $BuildVenv" -ForegroundColor Cyan
    # Prefer the `py` launcher when present (standard on Python installer);
    # fall back to `python` on systems where only python.exe is on PATH.
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        py -3 -m venv $BuildVenv
    } else {
        python -m venv $BuildVenv
    }
}

$Python = Join-Path $BuildVenv "Scripts\python.exe"
$Pip    = Join-Path $BuildVenv "Scripts\pip.exe"

if (-not (Test-Path $Python)) {
    throw "venv creation failed -- python.exe not found at $Python"
}

# --- 2. Install runtime + build deps --------------------------------
Write-Host "[deps] installing runtime + pyinstaller" -ForegroundColor Cyan
& $Pip install --quiet --upgrade pip
& $Pip install --quiet -r (Join-Path $RepoRoot "requirements.txt")
& $Pip install --quiet pyinstaller

# --- 3. Build --------------------------------------------------------
Write-Host "[build] running pyinstaller" -ForegroundColor Cyan
Push-Location $RepoRoot
try {
    & (Join-Path $BuildVenv "Scripts\pyinstaller.exe") $SpecFile --noconfirm --clean
    if ($LASTEXITCODE -ne 0) { throw "pyinstaller exited $LASTEXITCODE" }
} finally {
    Pop-Location
}

$BuiltExe = Join-Path $DistDir "YouTManager\YouTManager.exe"
if (-not (Test-Path $BuiltExe)) {
    throw "expected exe not found at $BuiltExe"
}

$ExeSize = (Get-Item $BuiltExe).Length
if ($ExeSize -lt 100KB) {
    throw "built exe is suspiciously small ($ExeSize bytes) -- build likely broken"
}
Write-Host "[build] $BuiltExe ($([math]::Round((Get-Item $BuiltExe).Length / 1MB, 1)) MB)" -ForegroundColor Green

# --- 4. Zip the folder for distribution -----------------------------
$ZipName = "YouTManager-$Version.zip"
$ZipPath = Join-Path $DistDir $ZipName
Write-Host "[zip] packaging $ZipName" -ForegroundColor Cyan
if (Test-Path $ZipPath) { Remove-Item $ZipPath }

# Include the install/uninstall scripts so users get a one-click setup
# straight out of the extracted zip.
$StagingDir = Join-Path $DistDir "_stage"
if (Test-Path $StagingDir) { Remove-Item -Recurse -Force $StagingDir }
New-Item -ItemType Directory -Path $StagingDir | Out-Null
Copy-Item -Recurse (Join-Path $DistDir "YouTManager") (Join-Path $StagingDir "YouTManager")
Copy-Item (Join-Path $RepoRoot "scripts\install.ps1")   (Join-Path $StagingDir "install.ps1")
Copy-Item (Join-Path $RepoRoot "scripts\uninstall.ps1") (Join-Path $StagingDir "uninstall.ps1")
Copy-Item (Join-Path $RepoRoot "install.bat")           (Join-Path $StagingDir "install.bat")
Copy-Item (Join-Path $RepoRoot "README.md")             (Join-Path $StagingDir "README.md")
Copy-Item (Join-Path $RepoRoot "LICENSE")               (Join-Path $StagingDir "LICENSE")

# Compress-Archive can trip on locks held by Windows Defender scanning
# freshly-written PyInstaller binaries. Give it a beat and retry a
# few times before giving up.
$compressed = $false
for ($i = 0; $i -lt 5; $i++) {
    try {
        Start-Sleep -Seconds 2
        Compress-Archive -Path (Join-Path $StagingDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal -Force
        $compressed = $true
        break
    } catch {
        Write-Host "[zip] attempt $($i + 1) failed ($($_.Exception.Message)); retrying..." -ForegroundColor Yellow
    }
}
if (-not $compressed) { throw "Compress-Archive kept failing -- files may be locked by antivirus" }
Remove-Item -Recurse -Force $StagingDir

$ZipSize = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "[done] $ZipPath ($ZipSize MB)" -ForegroundColor Green
Write-Host ""
Write-Host "Next: extract the zip and run install.bat to test the install cycle."
