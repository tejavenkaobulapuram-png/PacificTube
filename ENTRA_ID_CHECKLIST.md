# ✅ Entra ID Configuration Checklist

**Date:** April 16, 2026  
**Status:** Credentials received from ICT team

---

## 📋 What We Have:

✅ **Client ID:** `4d0907a1-b963-42b2-963b-bf6b17ab10a4`  
✅ **Client Secret:** `[REDACTED - See .env file]`  
✅ **Tenant ID:** `1436d589-92e5-4e3b-a67a-1e65a9b1ba02`  
✅ **Authority URL:** `https://login.microsoftonline.com/1436d589-92e5-4e3b-a67a-1e65a9b1ba02`  

---

## ⚠️ IMPORTANT: Verify with ICT Team

**Before enabling authentication, please confirm with ICT team that these redirect URIs are registered:**

### Required Redirect URIs:

1. **Production:**
   ```
   https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/auth/callback
   ```

2. **Local Testing (Optional):**
   ```
   http://localhost:5000/auth/callback
   ```

### How ICT Team Registers Redirect URIs:

1. Azure Portal → Entra ID → App registrations
2. Find app with Client ID: `4d0907a1-b963-42b2-963b-bf6b17ab10a4`
3. Click "Authentication" in left menu
4. Under "Platform configurations" → Click "Add a platform" → "Web"
5. Add redirect URI(s) above
6. Click "Configure"

**Email to ICT Team:**
```
Subject: Redirect URI Registration for PacificTube Entra ID App

Hi ICT Team,

Thank you for providing the Entra ID credentials (Client ID: 4d0907a1-b963-42b2-963b-bf6b17ab10a4).

Could you please confirm that the following redirect URIs are registered in the app registration:

Production:
https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/auth/callback

Local Testing (optional):
http://localhost:5000/auth/callback

This is required for the OAuth callback to work correctly.

Thank you!
```

---

## 🧪 Testing Steps

### Step 1: Test Locally (Recommended First)

```powershell
# Install dependencies
pip install msal Flask-Session

# Make sure ENABLE_ENTRA_ID=False in .env (test without auth first)
# Start app
python app.py

# Visit http://localhost:5000
# Should work normally without authentication
```

### Step 2: Enable Authentication Locally

```powershell
# Edit .env file
# Change: ENABLE_ENTRA_ID=False
# To:     ENABLE_ENTRA_ID=True

# Restart app
python app.py

# Visit http://localhost:5000
# Expected: Redirected to Microsoft login
```

**If you see "Redirect URI mismatch" error:**
- ICT team needs to add: `http://localhost:5000/auth/callback`

### Step 3: Deploy to Production

```powershell
# Commit code (NOT credentials - they're in .env which is .gitignored)
git add entra_auth.py app.py requirements.txt .env.example ENTRA_ID_SETUP.md
git commit -m "Add Entra ID authentication support"
git push origin main

# Build Docker image
az account set --subscription ba1c7ebc-b99e-4419-9c2d-137303050956

az acr build --registry ca6de7c5a7f3acr \
  --image pacifictube:latest \
  --image pacifictube:v2.4-entraid \
  --file Dockerfile .

# Update Container App with environment variables
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --set-env-vars \
    ENABLE_ENTRA_ID=True \
    ENTRA_CLIENT_ID="4d0907a1-b963-42b2-963b-bf6b17ab10a4" \
    ENTRA_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE" \
    ENTRA_TENANT_ID="1436d589-92e5-4e3b-a67a-1e65a9b1ba02" \
    ENTRA_AUTHORITY="https://login.microsoftonline.com/1436d589-92e5-4e3b-a67a-1e65a9b1ba02" \
    ENTRA_REDIRECT_PATH="/auth/callback" \
    SECRET_KEY="$(openssl rand -hex 32)" \
    SESSION_TYPE="filesystem"

# Deploy the new image
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --image ca6de7c5a7f3acr.azurecr.io/pacifictube:latest
```

### Step 4: Test Production

```
1. Visit: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io
2. Should redirect to: login.microsoftonline.com
3. Login with company email/password
4. Should redirect back to PacificTube
5. ✅ Success!
```

---

## 🚨 Quick Rollback (If Needed)

If authentication fails in production:

```powershell
# Disable authentication (keeps app running)
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --set-env-vars ENABLE_ENTRA_ID=False
```

App will work normally without authentication.

---

## 📊 Current Status

- [x] Credentials received
- [x] Code implemented
- [x] Local .env configured
- [ ] Redirect URIs confirmed with ICT team ⚠️
- [ ] Local testing
- [ ] Production deployment
- [ ] Production testing

---

## 🔐 Security Notes

✅ **Credentials are secure:**
- Stored in `.env` (not committed to git)
- `.env` is in `.gitignore`
- Production credentials in Azure environment variables (encrypted)

✅ **Client secret expires:** Check with ICT team when it expires (usually 12-24 months)

⚠️ **Before expiration:** Request new secret from ICT team

---

## 💡 Next Steps

**Option 1: Enable Now (After ICT Confirms Redirect URIs)**
1. Confirm redirect URIs with ICT team
2. Test locally: Set `ENABLE_ENTRA_ID=True` in `.env`
3. If works: Deploy to production

**Option 2: Enable Later**
1. Keep `ENABLE_ENTRA_ID=False` for now
2. App works normally without authentication
3. Enable when needed by setting to `True`

---

**Ready to enable?** Just change `ENABLE_ENTRA_ID=False` → `ENABLE_ENTRA_ID=True` in `.env` and restart!
