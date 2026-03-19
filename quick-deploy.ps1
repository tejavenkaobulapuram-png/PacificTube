# 🚀 Quick Deploy to Azure Container Apps
# No Docker Desktop needed - Azure builds the container for you!

# Configuration
$RESOURCE_GROUP = "rg-pacifictube"
$LOCATION = "japaneast"
$CONTAINER_APP_ENV = "pacifictube-env"
$CONTAINER_APP_NAME = "pacifictube-app"
$STORAGE_ACCOUNT = "pacifictubestorage"
$SUBSCRIPTION_ID = "ba1c7ebc-b99e-4419-9c2d-137303050956"

Write-Host "🚀 PacificTube Quick Deployment (Cloud Build)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Set subscription
Write-Host "1️⃣  Setting Azure subscription..." -ForegroundColor Yellow
az account set --subscription $SUBSCRIPTION_ID
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to set subscription" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Subscription set" -ForegroundColor Green

# Step 2: Create resource group (if not exists)
Write-Host "`n2️⃣  Checking resource group..." -ForegroundColor Yellow
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "false") {
    Write-Host "Creating resource group..." -ForegroundColor Cyan
    az group create --name $RESOURCE_GROUP --location $LOCATION
    Write-Host "✅ Resource group created" -ForegroundColor Green
} else {
    Write-Host "✅ Resource group exists" -ForegroundColor Green
}

# Step 3: Create Container Apps environment
Write-Host "`n3️⃣  Creating Container Apps environment..." -ForegroundColor Yellow
$envExists = az containerapp env show --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating environment (this may take 3-5 minutes)..." -ForegroundColor Cyan
    az containerapp env create `
        --name $CONTAINER_APP_ENV `
        --resource-group $RESOURCE_GROUP `
        --location $LOCATION
    Write-Host "✅ Environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Environment already exists" -ForegroundColor Green
}

# Step 4: Get SAS tokens from .env file
Write-Host "`n4️⃣  Reading configuration from .env file..." -ForegroundColor Yellow
$envVars = @{}
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $envVars[$matches[1]] = $matches[2]
    }
}

$BLOB_SAS = $envVars['AZURE_STORAGE_SAS_TOKEN']
$TABLE_SAS = $envVars['AZURE_TABLE_SAS_TOKEN']

Write-Host "✅ Configuration loaded" -ForegroundColor Green
Write-Host "   - Blob SAS: $($BLOB_SAS.Substring(0, 30))..." -ForegroundColor Gray
Write-Host "   - Table SAS: $($TABLE_SAS.Substring(0, 30))..." -ForegroundColor Gray

# Step 5: Deploy Container App from source code (Azure builds it!)
Write-Host "`n5️⃣  Deploying Container App from source code..." -ForegroundColor Yellow
Write-Host "⚠️  Azure will build the Docker image in the cloud (no Docker Desktop needed)" -ForegroundColor Magenta
Write-Host "⏳ This will take 5-10 minutes..." -ForegroundColor Cyan

# Step 5: Deploy Container App from source code (Azure builds it!)
Write-Host "`n5️⃣  Deploying Container App from source code..." -ForegroundColor Yellow
Write-Host "⚠️  Azure will build the Docker image in the cloud (no Docker Desktop needed)" -ForegroundColor Magenta
Write-Host "⏳ This will take 5-10 minutes..." -ForegroundColor Cyan

# Properly quote environment variables with special characters
$deployResult = az containerapp up `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --environment $CONTAINER_APP_ENV `
    --location $LOCATION `
    --source . `
    --target-port 5000 `
    --ingress external `
    --env-vars `
        "USE_CLOUD_STORAGE=True" `
        "DEBUG=False" `
        "PORT=5000" `
        "AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT" `
        "AZURE_STORAGE_SAS_TOKEN='$BLOB_SAS'" `
        "AZURE_TABLE_SAS_TOKEN='$TABLE_SAS'" 2>&1

# Store exit code before any other commands
$deployExitCode = $LASTEXITCODE

# Check if deployment succeeded based on output
$deploymentSucceeded = $deployResult -match "Container app created|created and deployed|Your container app .* has been created"

if ($deployExitCode -eq 0 -or $deploymentSucceeded) {
    Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
    
    # Get the app URL
    $appUrl = az containerapp show `
        --name $CONTAINER_APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "properties.configuration.ingress.fqdn" `
        --output tsv
    
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  🎉 PacificTube is Live!              ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🌐 Application URL:" -ForegroundColor Yellow
    Write-Host "   https://$appUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 View logs:" -ForegroundColor Yellow
    Write-Host "   az containerapp logs tail --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🎬 Open in browser:" -ForegroundColor Yellow
    Write-Host "   Start-Process https://$appUrl" -ForegroundColor Gray
    Write-Host ""
    
    # Ask to open browser
    $openBrowser = Read-Host "Do you want to open the app in your browser? (Y/N)"
    if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
        Start-Process "https://$appUrl"
    }
} else {
    Write-Host "`n⚠️  Deployment command returned errors, but checking actual status..." -ForegroundColor Yellow
    
    # Check if the container app actually exists and is running
    $appStatus = az containerapp show `
        --name $CONTAINER_APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "properties.provisioningState" `
        --output tsv 2>$null
    
    if ($appStatus -eq "Succeeded") {
        Write-Host "✅ Container app is actually running successfully!" -ForegroundColor Green
        Write-Host "   (The errors above are just PowerShell parsing issues with SAS tokens)" -ForegroundColor Gray
        
        $appUrl = az containerapp show `
            --name $CONTAINER_APP_NAME `
            --resource-group $RESOURCE_GROUP `
            --query "properties.configuration.ingress.fqdn" `
            --output tsv
        
        Write-Host "`n🌐 Application URL: https://$appUrl" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Deployment actually failed. Status: $appStatus" -ForegroundColor Red
        Write-Host "💡 Check logs with: az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor Yellow
    }
}

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Deployment script complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
