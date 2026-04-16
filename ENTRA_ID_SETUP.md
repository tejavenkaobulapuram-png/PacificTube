# Entra ID Authentication Setup Guide

## 📋 Overview
This guide explains how to enable Entra ID (Azure Active Directory) authentication for PacificTube. The code is **already prepared** - you just need to add credentials from the ICT team.

---

## ✅ Current Status (April 16, 2026)

### What's Already Done:
- ✅ Entra ID authentication code implemented
- ✅ MSAL (Microsoft Authentication Library) integrated
- ✅ Flask-Session configured for user sessions
- ✅ Login/Logout routes ready
- ✅ User authentication decorator ready
- ✅ Configuration ready in `.env.example`

### What's Needed from ICT Team:
- ❌ Entra ID App Registration credentials
- ❌ Tenant ID
- ❌ Client ID
- ❌ Client Secret

---

## 📝 Request to ICT Team

**Subject:** Entra ID App Registration Request for PacificTube Application

**Body:**
```
Dear ICT Team,

We need Entra ID (Azure Active Directory) authentication for our PacificTube application.

Application Details:
- Name: PacificTube
- Purpose: Internal video training platform
- URL: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io
- Authentication Type: OAuth 2.0 / OpenID Connect

Please create an App Registration with the following settings:

1. App Registration Name: PacificTube
2. Supported Account Types: Accounts in this organizational directory only
3. Redirect URI: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/auth/callback
4. API Permissions Required:
   - Microsoft Graph -> User.Read (Delegated)
   - Microsoft Graph -> GroupMember.Read.All (Delegated) [optional - for group restrictions]

After creating the app registration, please provide:
1. Tenant ID
2. Application (Client) ID
3. Client Secret (with long expiration, e.g., 24 months)

This will enable secure employee authentication using company Entra ID accounts.

Thank you!
```

---

## 🔧 What ICT Team Will Provide

Once ICT team creates the App Registration, they will give you:

### 1. Tenant ID
- Format: `12345678-1234-1234-1234-123456789012`
- Found in: Azure Portal -> Entra ID -> Overview -> Tenant ID

### 2. Application (Client) ID
- Format: `87654321-4321-4321-4321-210987654321`
- Found in: Azure Portal -> App Registrations -> [Your App] -> Overview -> Application (client) ID

### 3. Client Secret
- Format: `abc123~xyz.789-randomstring`
- Found in: Azure Portal -> App Registrations -> [Your App] -> Certificates & secrets -> Client secrets
- **Important:** Save this immediately - you can only see it once!

---

## 🚀 How to Enable (After Receiving Credentials)

### Step 1: Update `.env` File

Edit your `.env` file and add the credentials from ICT team:

```bash
# Enable Entra ID
ENABLE_ENTRA_ID=True

# Credentials from ICT team
ENTRA_CLIENT_ID=87654321-4321-4321-4321-210987654321
ENTRA_CLIENT_SECRET=abc123~xyz.789-randomstring
ENTRA_TENANT_ID=12345678-1234-1234-1234-123456789012

# This will be automatically constructed
ENTRA_AUTHORITY=https://login.microsoftonline.com/12345678-1234-1234-1234-123456789012

# Callback path (already configured in app)
ENTRA_REDIRECT_PATH=/auth/callback

# Optional: Restrict to specific groups (leave empty for all users)
ENTRA_ALLOWED_GROUPS=

# Session configuration (already optimal)
SESSION_TYPE=filesystem
SESSION_PERMANENT=False
PERMANENT_SESSION_LIFETIME=3600
```

### Step 2: Update Azure Container App Environment Variables

Set these environment variables in Azure Container Apps:

```bash
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --set-env-vars \
    ENABLE_ENTRA_ID=True \
    ENTRA_CLIENT_ID="YOUR_CLIENT_ID" \
    ENTRA_CLIENT_SECRET="YOUR_CLIENT_SECRET" \
    ENTRA_TENANT_ID="YOUR_TENANT_ID" \
    ENTRA_AUTHORITY="https://login.microsoftonline.com/YOUR_TENANT_ID" \
    SECRET_KEY="generate-random-32-char-string" \
    SESSION_TYPE="filesystem"
```

### Step 3: Deploy

```bash
# Commit the code (credentials are in .env, not in code)
git add entra_auth.py app.py requirements.txt .env.example
git commit -m "Add Entra ID authentication support"
git push origin main

# Build and deploy
az acr build --registry ca6de7c5a7f3acr \
  --image pacifictube:latest \
  --image pacifictube:v2.4-entraid \
  --file Dockerfile .

# Restart container app
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --image ca6de7c5a7f3acr.azurecr.io/pacifictube:latest
```

---

## 🔐 Security Features

### Built-in Security:
1. **OAuth 2.0 / OpenID Connect** - Industry standard authentication
2. **Session Management** - Secure server-side sessions
3. **HTTPS Only** - All authentication over encrypted connections
4. **Token Expiration** - Sessions expire after 1 hour (configurable)
5. **CSRF Protection** - Flask built-in protection
6. **Group-based Access Control** - Optional restriction by AD groups

### Optional: Restrict by Group

If you want to restrict access to specific groups:

1. Ask ICT team which group(s) should have access
2. Update `.env`:
   ```bash
   ENTRA_ALLOWED_GROUPS=PacificTube Users,Engineering Team
   ```
3. Only users in these groups can access the app

---

## 🧪 Testing After Setup

### 1. Test Locally First

```bash
# Install new dependencies
pip install -r requirements.txt

# Update your local .env with credentials
# Set ENABLE_ENTRA_ID=True

# Run app
python app.py

# Visit http://localhost:5000
# You should be redirected to Microsoft login
```

### 2. Test in Production

```bash
# Visit production URL
https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io

# Expected flow:
1. Redirected to Microsoft login (login.microsoftonline.com)
2. Enter company email/password
3. Consent to requested permissions (first time only)
4. Redirected back to PacificTube
5. You're logged in!
```

### 3. Test Logout

```bash
# Visit logout URL
https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/logout

# Expected:
1. Session cleared
2. Redirected to Microsoft logout
3. Redirected back to home page
```

---

## 📊 User Experience Changes

### Before Entra ID (ENABLE_ENTRA_ID=False):
- ✅ Anyone with URL can access
- ✅ No login required
- ❌ No user tracking
- ❌ No access control

### After Entra ID (ENABLE_ENTRA_ID=True):
- ✅ Only company employees can access
- ✅ Secure Microsoft login
- ✅ User name/email tracked
- ✅ Can restrict by department/group
- ✅ Automatic logout after inactivity

---

## 🔄 Rollback Plan (If Issues Occur)

If something goes wrong after enabling Entra ID:

### Quick Disable (No Deployment):
```bash
# Just update environment variable
az containerapp update \
  --name pacifictube-app \
  --resource-group rg-pacifictube \
  --set-env-vars ENABLE_ENTRA_ID=False

# Restart app
az containerapp restart \
  --name pacifictube-app \
  --resource-group rg-pacifictube
```

Application will work normally without authentication.

---

## 🐛 Troubleshooting

### Error: "Entra ID not enabled"
- **Cause:** `ENABLE_ENTRA_ID=False` or not set
- **Fix:** Set `ENABLE_ENTRA_ID=True` in environment

### Error: "Invalid client secret"
- **Cause:** Wrong or expired client secret
- **Fix:** Generate new secret from ICT team, update `.env`

### Error: "Redirect URI mismatch"
- **Cause:** Callback URL not registered in App Registration
- **Fix:** Ask ICT team to add: `https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/auth/callback`

### Error: "User not in allowed groups"
- **Cause:** User's AD group not in `ENTRA_ALLOWED_GROUPS`
- **Fix:** Either add user's group to allowed list, or remove group restrictions

### Login Works Locally but Not in Production
- **Cause:** Different redirect URIs
- **Fix:** Ask ICT team to register both:
  - Local: `http://localhost:5000/auth/callback`
  - Production: `https://pacifictube-app.../auth/callback`

---

## 📞 Support Contacts

- **Code Issues:** Development team
- **Entra ID Credentials:** ICT team
- **Azure Deployment:** DevOps team
- **User Access Issues:** IT Help Desk

---

## 📝 Checklist for ICT Team Meeting

When meeting with ICT team, bring this checklist:

- [ ] Application name: PacificTube
- [ ] Production URL: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io
- [ ] Redirect URI: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io/auth/callback
- [ ] Local testing URI: http://localhost:5000/auth/callback (optional)
- [ ] Required permissions: User.Read, GroupMember.Read.All
- [ ] Account type: Single tenant (organization only)
- [ ] Client secret expiration: 24 months minimum

**What you need from them:**
- [ ] Tenant ID
- [ ] Application (Client) ID
- [ ] Client Secret (save immediately!)

---

## ✅ Summary

**Current Status:**
- Code is READY ✅
- Just need credentials from ICT team ⏳

**After Getting Credentials:**
1. Add credentials to `.env` → 5 minutes
2. Update Azure environment variables → 5 minutes
3. Deploy → 5 minutes
4. Test → 5 minutes
**Total setup time: ~20 minutes** 🚀

**Cost Impact:**
- Entra ID authentication: ¥0 (included with Microsoft 365)
- No additional Azure costs ✅

---

**Last Updated:** April 16, 2026  
**Status:** Ready for ICT team credentials
