# Azure Container Apps Deployment Script for PacificTube
# This script helps deploy the application to Azure Container Apps

# Configuration
$RESOURCE_GROUP = "rg-pacifictube"
$LOCATION = "japaneast"
$CONTAINER_APP_ENV = "pacifictube-env"
$CONTAINER_APP_NAME = "pacifictube-app"
$STORAGE_ACCOUNT = "pacifictubestorage"
$SUBSCRIPTION_ID = "ba1c7ebc-b99e-4419-9c2d-137303050956"

Write-Host "🚀 PacificTube Deployment Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Step 1: Set subscription
Write-Host "`n1️⃣  Setting Azure subscription..." -ForegroundColor Yellow
az account set --subscription $SUBSCRIPTION_ID
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to set subscription. Please login with: az login" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Subscription set successfully" -ForegroundColor Green

# Step 2: Create resource group (if not exists)
Write-Host "`n2️⃣  Checking resource group..." -ForegroundColor Yellow
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "false") {
    Write-Host "Creating resource group: $RESOURCE_GROUP" -ForegroundColor Cyan
    az group create --name $RESOURCE_GROUP --location $LOCATION
    Write-Host "✅ Resource group created" -ForegroundColor Green
} else {
    Write-Host "✅ Resource group already exists" -ForegroundColor Green
}

# Step 3: Generate Table Storage SAS Token
Write-Host "`n3️⃣  Generating Table Storage SAS token..." -ForegroundColor Yellow
Write-Host "⚠️  IMPORTANT: You need a SAS token with Table permissions (rwau)" -ForegroundColor Magenta
Write-Host "Current Blob SAS token expires: 2027-03-19" -ForegroundColor Cyan

$expiryDate = (Get-Date).AddYears(1).ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "`nRun this command to generate Table SAS token:" -ForegroundColor Cyan
Write-Host "az storage table generate-sas --account-name $STORAGE_ACCOUNT --name views --permissions rwau --expiry $expiryDate --https-only --output tsv" -ForegroundColor White

Write-Host "`n⏸️  Please generate the SAS token and update container-app.yaml" -ForegroundColor Yellow
Write-Host "Press Enter when ready to continue..." -ForegroundColor Yellow
Read-Host

# Step 4: Create Container Apps environment
Write-Host "`n4️⃣  Creating Container Apps environment..." -ForegroundColor Yellow
$envExists = az containerapp env show --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating environment: $CONTAINER_APP_ENV" -ForegroundColor Cyan
    az containerapp env create `
        --name $CONTAINER_APP_ENV `
        --resource-group $RESOURCE_GROUP `
        --location $LOCATION
    Write-Host "✅ Environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Environment already exists" -ForegroundColor Green
}

# Step 5: Build and push Docker image
Write-Host "`n5️⃣  Building Docker image..." -ForegroundColor Yellow
Write-Host "⚠️  Choose deployment method:" -ForegroundColor Magenta
Write-Host "  A) Build locally and push to Azure Container Registry" -ForegroundColor White
Write-Host "  B) Build locally and push to Docker Hub" -ForegroundColor White
Write-Host "  C) Skip (image already uploaded)" -ForegroundColor White
$choice = Read-Host "Enter choice (A/B/C)"

switch ($choice.ToUpper()) {
    "A" {
        Write-Host "`nOption A selected: Azure Container Registry" -ForegroundColor Cyan
        Write-Host "You'll need to:" -ForegroundColor Yellow
        Write-Host "1. Create ACR: az acr create --name pacifictubeacr --resource-group $RESOURCE_GROUP --sku Basic" -ForegroundColor White
        Write-Host "2. Login: az acr login --name pacifictubeacr" -ForegroundColor White
        Write-Host "3. Build: docker build -t pacifictubeacr.azurecr.io/pacifictube:latest ." -ForegroundColor White
        Write-Host "4. Push: docker push pacifictubeacr.azurecr.io/pacifictube:latest" -ForegroundColor White
    }
    "B" {
        Write-Host "`nOption B selected: Docker Hub" -ForegroundColor Cyan
        $dockerUser = Read-Host "Enter Docker Hub username"
        Write-Host "Building image..." -ForegroundColor Cyan
        docker build -t ${dockerUser}/pacifictube:latest .
        Write-Host "Pushing to Docker Hub..." -ForegroundColor Cyan
        docker push ${dockerUser}/pacifictube:latest
        Write-Host "✅ Image pushed to Docker Hub" -ForegroundColor Green
    }
    "C" {
        Write-Host "✅ Skipping image build" -ForegroundColor Green
    }
}

# Step 6: Deploy Container App
Write-Host "`n6️⃣  Deploying Container App..." -ForegroundColor Yellow
Write-Host "⚠️  Update container-app.yaml with:" -ForegroundColor Magenta
Write-Host "  - Your container image URL" -ForegroundColor White
Write-Host "  - Blob SAS token (existing)" -ForegroundColor White
Write-Host "  - Table SAS token (newly generated)" -ForegroundColor White

Write-Host "`nPress Enter when container-app.yaml is updated..." -ForegroundColor Yellow
Read-Host

Write-Host "Deploying container app..." -ForegroundColor Cyan
Write-Host "⚠️  Note: Azure CLI doesn't directly support YAML for Container Apps." -ForegroundColor Yellow
Write-Host "You'll need to deploy using these commands:" -ForegroundColor Cyan

$imageUrl = Read-Host "Enter your container image URL (e.g., username/pacifictube:latest)"
$blobSas = Read-Host "Enter Blob SAS token (existing)"
$tableSas = Read-Host "Enter Table SAS token (newly generated)"

az containerapp create `
    --name $CONTAINER_APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --environment $CONTAINER_APP_ENV `
    --image $imageUrl `
    --target-port 5000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 10 `
    --cpu 1.0 `
    --memory 2.0Gi `
    --env-vars `
        "USE_CLOUD_STORAGE=True" `
        "DEBUG=False" `
        "PORT=5000" `
        "AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT" `
    --secrets `
        "sas-token-blob=$blobSas" `
        "sas-token-table=$tableSas" `
    --env-vars `
        "AZURE_STORAGE_SAS_TOKEN=secretref:sas-token-blob" `
        "AZURE_TABLE_SAS_TOKEN=secretref:sas-token-table"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Container App deployed successfully!" -ForegroundColor Green
    
    # Get the app URL
    $appUrl = az containerapp show `
        --name $CONTAINER_APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --query "properties.configuration.ingress.fqdn" `
        --output tsv
    
    Write-Host "`n🌐 Application URL: https://$appUrl" -ForegroundColor Cyan
    Write-Host "`n📊 Monitor your app:" -ForegroundColor Yellow
    Write-Host "   az containerapp logs tail --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor White
} else {
    Write-Host "`n❌ Deployment failed. Check errors above." -ForegroundColor Red
}

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🎉 Deployment script complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
