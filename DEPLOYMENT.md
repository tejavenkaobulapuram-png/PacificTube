# 🚀 Azure Container Apps Deployment Guide

## Prerequisites
- Docker Desktop installed and running
- Azure CLI installed and logged in (`az login`)
- Storage account: `pacifictubestorage` (already created)
- Subscription set: `ba1c7ebc-b99e-4419-9c2d-137303050956`

## 📝 Deployment Steps

### 1️⃣ Generate Table Storage SAS Token

**IMPORTANT:** Your current SAS token only works for Blob Storage. You need a separate token for Table Storage.

```powershell
# Set subscription
az account set --subscription ba1c7ebc-b99e-4419-9c2d-137303050956

# Generate Table SAS token (expires 2027-03-19, same as blob token)
az storage table generate-sas `
    --account-name pacifictubestorage `
    --name views `
    --permissions rwau `
    --expiry 2027-03-19T23:59:59Z `
    --https-only `
    --output tsv
```

**Save this token!** You'll need it in step 4.

---

### 2️⃣ Build Docker Image

```powershell
# Navigate to project directory
cd C:\Users\tejavenka.obulapuram\Documents\GitHub\PacificTube

# Build the image
docker build -t pacifictube:latest .

# Test locally (optional)
docker run -p 5000:5000 `
    -e USE_CLOUD_STORAGE=False `
    -e DEBUG=True `
    pacifictube:latest
```

Open http://localhost:5000 to verify it works.

---

### 3️⃣ Push Image to Docker Hub (or Azure Container Registry)

**Option A: Docker Hub (Easier)**
```powershell
# Login to Docker Hub
docker login

# Tag image with your Docker Hub username
docker tag pacifictube:latest YOUR_DOCKERHUB_USERNAME/pacifictube:latest

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/pacifictube:latest
```

**Option B: Azure Container Registry (More secure)**
```powershell
# Create ACR
az acr create --name pacifictubeacr --resource-group rg-pacifictube --sku Basic --location japaneast

# Login to ACR
az acr login --name pacifictubeacr

# Tag and push
docker tag pacifictube:latest pacifictubeacr.azurecr.io/pacifictube:latest
docker push pacifictubeacr.azurecr.io/pacifictube:latest
```

---

### 4️⃣ Create Container Apps Environment

```powershell
# Create resource group (if not exists)
az group create --name rg-pacifictube --location japaneast

# Create Container Apps environment
az containerapp env create `
    --name pacifictube-env `
    --resource-group rg-pacifictube `
    --location japaneast
```

---

### 5️⃣ Deploy Container App

Replace placeholders with your values:
- `YOUR_IMAGE_URL`: e.g., `username/pacifictube:latest` or `pacifictubeacr.azurecr.io/pacifictube:latest`
- `YOUR_BLOB_SAS_TOKEN`: Your existing blob SAS token (starts with `se=2027-03-19...`)
- `YOUR_TABLE_SAS_TOKEN`: Token generated in step 1

```powershell
az containerapp create `
    --name pacifictube-app `
    --resource-group rg-pacifictube `
    --environment pacifictube-env `
    --image YOUR_IMAGE_URL `
    --target-port 5000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 10 `
    --cpu 1.0 `
    --memory 2.0Gi `
    --secrets `
        "sas-token-blob=YOUR_BLOB_SAS_TOKEN" `
        "sas-token-table=YOUR_TABLE_SAS_TOKEN" `
    --env-vars `
        "USE_CLOUD_STORAGE=True" `
        "DEBUG=False" `
        "PORT=5000" `
        "AZURE_STORAGE_ACCOUNT_NAME=pacifictubestorage" `
        "AZURE_STORAGE_SAS_TOKEN=secretref:sas-token-blob" `
        "AZURE_TABLE_SAS_TOKEN=secretref:sas-token-table"
```

---

### 6️⃣ Get Application URL

```powershell
# Get the public URL
az containerapp show `
    --name pacifictube-app `
    --resource-group rg-pacifictube `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv
```

Visit `https://YOUR_APP_URL.japaneast.azurecontainerapps.io` to access your video gallery!

---

## 🔧 Troubleshooting

### View Logs
```powershell
az containerapp logs tail `
    --name pacifictube-app `
    --resource-group rg-pacifictube `
    --follow
```

### Test Locally with Cloud Storage
```powershell
# Set environment variables with your tokens
$env:USE_CLOUD_STORAGE="True"
$env:AZURE_STORAGE_ACCOUNT_NAME="pacifictubestorage"
$env:AZURE_STORAGE_SAS_TOKEN="YOUR_BLOB_SAS_TOKEN"
$env:AZURE_TABLE_SAS_TOKEN="YOUR_TABLE_SAS_TOKEN"

# Run app
python app.py
```

### Update Existing Container App
```powershell
az containerapp update `
    --name pacifictube-app `
    --resource-group rg-pacifictube `
    --image YOUR_NEW_IMAGE_URL
```

---

## 📊 Cost Monitoring

```powershell
# Check current month costs
az consumption usage list `
    --start-date (Get-Date -Format "yyyy-MM-01") `
    --end-date (Get-Date -Format "yyyy-MM-dd")
```

Expected costs:
- Container Apps: ¥2,000-5,000/month (1-2 instances)
- Blob Storage: ¥200/month (10GB)
- Table Storage: ¥50/month (< 1GB)
- **Total: ¥2,250-5,250/month**

---

## ✨ Features Available After Deployment

✅ YouTube-style video gallery  
✅ Folder navigation sidebar  
✅ Search functionality  
✅ View count tracking (persistent with Table Storage)  
✅ Auto-scaling (1-10 instances)  
✅ HTTPS enabled  
✅ Supports unlimited concurrent users  

---

## 🔐 Security Notes

- All containers are private (not public)
- Access via SAS tokens (no account keys exposed)
- HTTPS only (no HTTP)
- Secrets stored in Container Apps (not in code)
- SAS tokens expire 2027-03-19 (renew before expiry)

---

## 📞 Next Steps

1. **Generate Table SAS token** (Step 1)
2. **Build and push Docker image** (Steps 2-3)
3. **Deploy to Container Apps** (Steps 4-5)
4. **Test and monitor** (Step 6 + Troubleshooting)
5. **Share URL with team** 🎉
