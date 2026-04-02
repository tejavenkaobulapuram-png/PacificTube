# 生成AI Videos Restoration Script
# Run this script to restore all 生成AI videos after re-uploading to Azure

Write-Host "=== 生成AI Videos Restoration Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if backup exists
if (-not (Test-Path "生成AI_videos_backup.json")) {
    Write-Host "ERROR: Backup file not found!" -ForegroundColor Red
    exit 1
}

$backup = Get-Content "生成AI_videos_backup.json" | ConvertFrom-Json
Write-Host "✓ Backup file loaded (created: $($backup.backup_date))" -ForegroundColor Green

# Step 2: Restore chapter files
Write-Host ""
Write-Host "Step 1: Restoring chapter files..." -ForegroundColor Yellow
if (Test-Path "chapters_backup") {
    Copy-Item "chapters_backup\*.chapters.json" -Destination "chapters\" -Verbose
    Write-Host "✓ Chapter files restored" -ForegroundColor Green
} else {
    Write-Host "⚠ chapters_backup folder not found, skipping chapter restoration" -ForegroundColor Yellow
}

# Step 3: Restore metadata entries
Write-Host ""
Write-Host "Step 2: Restoring video metadata..." -ForegroundColor Yellow
$currentMetadata = Get-Content "video_metadata.json" | ConvertFrom-Json

# Add backup entries to current metadata
foreach ($prop in $backup.video_metadata.PSObject.Properties) {
    $currentMetadata | Add-Member -MemberType NoteProperty -Name $prop.Name -Value $prop.Value -Force
}

$currentMetadata | ConvertTo-Json -Depth 10 | Set-Content "video_metadata.json" -Encoding UTF8
Write-Host "✓ Video metadata restored" -ForegroundColor Green

# Step 4: Restore view data (optional)
Write-Host ""
Write-Host "Step 3: Restoring view data..." -ForegroundColor Yellow
if (Test-Path "views.json") {
    $currentViews = Get-Content "views.json" | ConvertFrom-Json
    foreach ($prop in $backup.view_data.PSObject.Properties) {
        $currentViews | Add-Member -MemberType NoteProperty -Name $prop.Name -Value $prop.Value -Force
    }
    $currentViews | ConvertTo-Json -Depth 10 | Set-Content "views.json" -Encoding UTF8
    Write-Host "✓ View data restored" -ForegroundColor Green
} else {
    Write-Host "⚠ views.json not found, creating new file" -ForegroundColor Yellow
    $backup.view_data | ConvertTo-Json -Depth 10 | Set-Content "views.json" -Encoding UTF8
}

Write-Host ""
Write-Host "=== Restoration Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Make sure videos are uploaded to Azure Blob Storage"
Write-Host "2. If subtitles are missing, regenerate with: python generate_dual_subtitles.py [video_path] ja en"
Write-Host "3. If thumbnails are missing, regenerate with: python generate_thumbnails.py"
Write-Host "4. Deploy to Azure: .\quick-deploy.ps1"
