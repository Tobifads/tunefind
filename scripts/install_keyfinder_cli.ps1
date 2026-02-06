$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ToolsDir = Join-Path $RootDir ".tools"
$SrcDir = Join-Path $ToolsDir "keyfinder-cli-src"
$PrefixDir = Join-Path $ToolsDir "keyfinder-cli"
$VcpkgDir = Join-Path $ToolsDir "vcpkg"
$VcpkgExe = Join-Path $VcpkgDir "vcpkg.exe"
$Toolchain = Join-Path $VcpkgDir "scripts\buildsystems\vcpkg.cmake"

function Test-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WithWinget([string]$Id) {
    if (Test-Command "winget") {
        Write-Host "Installing $Id with winget..."
        & winget install --id $Id --accept-source-agreements --accept-package-agreements --silent
        return $true
    }
    return $false
}

function Install-WithChoco([string]$Name) {
    if (Test-Command "choco") {
        Write-Host "Installing $Name with choco..."
        & choco install -y $Name
        return $true
    }
    return $false
}

function Ensure-Tool([string]$CommandName, [string]$WingetId, [string]$ChocoName) {
    if (Test-Command $CommandName) {
        return
    }
    if (Install-WithWinget $WingetId) {
        return
    }
    if (Install-WithChoco $ChocoName) {
        return
    }
    throw "Missing required tool: $CommandName. Install it manually and re-run."
}

Ensure-Tool "git" "Git.Git" "git"
Ensure-Tool "cmake" "Kitware.CMake" "cmake"
Ensure-Tool "ffmpeg" "Gyan.FFmpeg" "ffmpeg"

New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

if (-not (Test-Path $SrcDir)) {
    & git clone https://github.com/evanpurkhiser/keyfinder-cli $SrcDir
} else {
    & git -C $SrcDir pull --ff-only
}

if (-not (Test-Path $VcpkgExe)) {
    if (-not (Test-Path $VcpkgDir)) {
        & git clone https://github.com/microsoft/vcpkg $VcpkgDir
    }
    & (Join-Path $VcpkgDir "bootstrap-vcpkg.bat")
}

& $VcpkgExe install libkeyfinder:x64-windows fftw3:x64-windows ffmpeg:x64-windows

& cmake -S $SrcDir -B (Join-Path $SrcDir "build") `
    -DCMAKE_INSTALL_PREFIX=$PrefixDir `
    -DCMAKE_BUILD_TYPE=Release `
    -DCMAKE_TOOLCHAIN_FILE=$Toolchain `
    -DVCPKG_TARGET_TRIPLET=x64-windows

& cmake --build (Join-Path $SrcDir "build") --config Release
& cmake --install (Join-Path $SrcDir "build") --config Release

$Bin = Join-Path $PrefixDir "bin\keyfinder-cli.exe"
if (-not (Test-Path $Bin)) {
    throw "keyfinder-cli build finished, but binary was not found at $Bin"
}

Write-Host "keyfinder-cli installed at: $Bin"
