# Download and Setup Portable FFmpeg (No Admin Rights Needed)

Write-Host "📦 Downloading portable FFmpeg..." -ForegroundColor Cyan

$ffmpegDir = "$PSScriptRoot\ffmpeg"
$ffmpegZip = "$PSScriptRoot\ffmpeg.zip"
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Create directory
if (-not (Test-Path $ffmpegDir)) {
    New-Item -ItemType Directory -Path $ffmpegDir | Out-Null
}

# Download FFmpeg
Write-Host "⏬ Downloading from gyan.dev..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip -UseBasicParsing
    Write-Host "✅ Download complete!" -ForegroundColor Green
} catch {
    Write-Host "❌ Download failed: $_" -ForegroundColor Red
    exit 1
}

# Extract
Write-Host "📂 Extracting FFmpeg..." -ForegroundColor Yellow
Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegDir -Force

# Find ffmpeg.exe
$ffmpegExe = Get-ChildItem -Path $ffmpegDir -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1

if ($ffmpegExe) {
    $ffmpegPath = $ffmpegExe.DirectoryName
    Write-Host "✅ FFmpeg extracted to: $ffmpegPath" -ForegroundColor Green
    
    # Add to PATH for current session
    $env:PATH = "$ffmpegPath;$env:PATH"
    
    # Test
    Write-Host "`n🧪 Testing FFmpeg..." -ForegroundColor Cyan
    & "$ffmpegPath\ffmpeg.exe" -version | Select-Object -First 1
    
    Write-Host "`n✅ FFmpeg is ready to use!" -ForegroundColor Green
    Write-Host "📝 Location: $ffmpegPath\ffmpeg.exe" -ForegroundColor White
    
    Write-Host "`n💡 No .env change needed - FFmpeg will be auto-detected!" -ForegroundColor Cyan
} else {
    Write-Host "❌ ffmpeg.exe not found after extraction" -ForegroundColor Red
    exit 1
}

# Cleanup
Remove-Item $ffmpegZip -Force
Write-Host "`n🎉 Setup complete!" -ForegroundColor Green
