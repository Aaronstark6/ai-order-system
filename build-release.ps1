$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$envName = "ai-order-system"
$releaseDir = Join-Path $PSScriptRoot "dist\ai-order-system-release"
$buildDistDir = Join-Path $PSScriptRoot "build\release-dist"
$buildWorkDir = Join-Path $PSScriptRoot "build\pyinstaller"
$builtAppDir = Join-Path $buildDistDir "ai-order-system"

Write-Host "Checking PyInstaller in conda environment: $envName"
conda run -n $envName python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found. Installing..."
    conda run -n $envName python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller install failed."
    }
}

Write-Host "Checking release dependencies..."
conda run -n $envName python -c "import pystray, PIL"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Release dependencies missing. Installing from requirements.txt..."
    conda run -n $envName python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Release dependency install failed."
    }
}

if (Test-Path $releaseDir) {
    Remove-Item -LiteralPath $releaseDir -Recurse -Force
}
if (Test-Path $buildDistDir) {
    Remove-Item -LiteralPath $buildDistDir -Recurse -Force
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Write-Host "Building executable..."
conda run -n $envName python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --noconsole `
    --paths $PSScriptRoot `
    --collect-submodules app `
    --hidden-import app.main `
    --hidden-import app.routes `
    --hidden-import app.routes.images `
    --hidden-import app.routes.parse `
    --hidden-import app.routes.templates `
    --hidden-import pystray `
    --hidden-import pystray._win32 `
    --hidden-import PIL `
    --hidden-import PIL.Image `
    --hidden-import PIL.ImageDraw `
    --name ai-order-system `
    --distpath $buildDistDir `
    --workpath $buildWorkDir `
    app_launcher.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Copy-Item -Path (Join-Path $builtAppDir "*") -Destination $releaseDir -Recurse -Force

foreach ($dirName in @("static", "templates", "data", "uploads", "output")) {
    $source = Join-Path $PSScriptRoot $dirName
    $target = Join-Path $releaseDir $dirName
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination $releaseDir -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
    }
}

if (Test-Path (Join-Path $PSScriptRoot ".env.example")) {
    Copy-Item -Path (Join-Path $PSScriptRoot ".env.example") -Destination $releaseDir -Force
} elseif (Test-Path (Join-Path $PSScriptRoot ".env")) {
    Copy-Item -Path (Join-Path $PSScriptRoot ".env") -Destination $releaseDir -Force
}

$releaseLogsDir = Join-Path $releaseDir "logs"
New-Item -ItemType Directory -Path $releaseLogsDir -Force | Out-Null
$releaseLogFile = Join-Path $releaseLogsDir "app.log"
if (-not (Test-Path $releaseLogFile)) {
    New-Item -ItemType File -Path $releaseLogFile -Force | Out-Null
}

if (Test-Path (Join-Path $PSScriptRoot "debug-start.bat")) {
    Copy-Item -Path (Join-Path $PSScriptRoot "debug-start.bat") -Destination $releaseDir -Force
}

Write-Host "Release ready: $releaseDir"
