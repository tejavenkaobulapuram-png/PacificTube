# PacificTube Team Setup Guide
## For Team Members Cloning from GitHub

This guide helps team members set up **automatic subtitle generation** after cloning the PacificTube repository.

---

## 📋 Prerequisites

1. **Python 3.13** (or Python 3.8+)
2. **Git** (to clone the repository)
3. **Azure credentials** (ask team lead for .env file)

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Clone the Repository

```powershell
cd C:\Your\Projects\Folder
git clone https://github.com/YOUR-TEAM/PacificTube.git
cd PacificTube
```

### Step 2: Install Python Dependencies

```powershell
pip install -r requirements.txt
```

Required packages:
- `azure-cognitiveservices-speech` (for subtitle generation)
- `azure-storage-blob` (for video storage)
- `flask` (web framework)
- `python-dotenv` (environment variables)

### Step 3: Install FFmpeg (Required for Subtitles)

**Option A: Automatic (Recommended)**

Run the provided setup script:

```powershell
.\setup_ffmpeg.ps1
```

This will:
- ✅ Download portable FFmpeg (no admin rights needed)
- ✅ Extract to `./ffmpeg/` folder
- ✅ Auto-detect FFmpeg path (no configuration needed)

**Option B: Manual Installation**

If you prefer to install FFmpeg globally:

**Windows:**
```powershell
choco install ffmpeg -y
```
(Requires [Chocolatey](https://chocolatey.org/) and admin rights)

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg       # CentOS/RHEL
```

---

## 🔑 Environment Variables (.env file)

Ask your team lead for the `.env` file containing Azure credentials:

```env
# Azure Storage
AZURE_STORAGE_ACCOUNT_NAME=pacifictubestorage
AZURE_STORAGE_SAS_TOKEN=se=2027...
AZURE_TABLE_SAS_TOKEN=se=2027...

# Azure Speech Services
AZURE_SPEECH_KEY=CHDG1rnYNBw...
AZURE_SPEECH_REGION=japaneast

# Optional: Custom FFmpeg path (auto-detected if not set)
# FFMPEG_PATH=ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe
```

**⚠️ SECURITY:** Never commit `.env` file to GitHub!  
The `.env` file is in `.gitignore` to prevent accidental commits.

---

## ✅ Verify Setup

Test that everything is configured correctly:

```powershell
python test_setup.py
```

Expected output:
```
1️⃣ Azure Speech Services:
   ✅ Speech Key: CHDG1rnYNB...WvtS (masked)
   ✅ Region: japaneast
2️⃣ Azure Storage:
   ✅ Storage Account: pacifictubestorage
3️⃣ FFmpeg:
   ✅ Version: ffmpeg version 8.1-essentials_build
4️⃣ Python Packages:
   ✅ azure-cognitiveservices-speech installed
   ✅ azure-storage-blob installed

✅ Setup is complete! Ready to generate subtitles!
```

---

## 🎬 Generate Your First Subtitle

Once setup is complete, try generating subtitles:

```powershell
python quick_subtitle.py
```

This will:
1. Download a test video from Azure Blob Storage
2. Extract audio using FFmpeg
3. Transcribe audio using Azure Speech Services
4. Upload subtitle file (.vtt) back to Azure
5. Display in PacificTube with CC button

---

## 📁 Project Structure

```
PacificTube/
├── app.py                    # Main Flask application
├── generate_subtitles.py     # 🆕 Subtitle generation engine
├── quick_subtitle.py         # 🆕 Quick test script
├── test_setup.py            # 🆕 Configuration validator
├── setup_ffmpeg.ps1         # 🆕 FFmpeg installer
├── .env                     # ⚠️ Credentials (not in git)
├── .gitignore               # Excludes .env, ffmpeg/, temp files
├── requirements.txt         # Python dependencies
├── ffmpeg/                  # 🆕 Portable FFmpeg (auto-created)
│   └── ffmpeg-8.1-essentials_build/
│       └── bin/
│           └── ffmpeg.exe
└── static/
    ├── script.js           # CC button logic
    └── style.css           # CC button styling
```

---

## 🤝 How FFmpeg Auto-Detection Works

The subtitle generator automatically finds FFmpeg in this order:

1. **Environment Variable**: `FFMPEG_PATH` in `.env` file
2. **Project Folder**: `./ffmpeg/ffmpeg-8.1-essentials_build/bin/ffmpeg.exe`
3. **System PATH**: Globally installed `ffmpeg` command

This means:
- ✅ If you run `setup_ffmpeg.ps1`, it just works (no configuration)
- ✅ If you install FFmpeg globally, it just works
- ✅ If you set custom path in `.env`, that takes priority

---

## 🐛 Troubleshooting

### Issue: "FFmpeg not found"

**Solution:**
```powershell
# Check if FFmpeg exists in project
Get-ChildItem -Path .\ffmpeg -Recurse -Filter ffmpeg.exe

# Test FFmpeg manually
.\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe -version

# Or install globally
choco install ffmpeg -y
```

### Issue: "Azure authentication failed"

**Solution:**
- Check `.env` file exists in project root
- Verify SAS tokens haven't expired (check `se=` parameter)
- Ask team lead for updated credentials

### Issue: "Python package not found"

**Solution:**
```powershell
# Reinstall all dependencies
pip install -r requirements.txt

# Or install individually
pip install azure-cognitiveservices-speech
pip install azure-storage-blob
```

---

## 💰 Cost Information

**Azure Speech Services (Free Tier):**
- 5 hours/month FREE transcription
- After 5 hours: ¥1.08/hour (~$0.01 USD)

**Current Usage (7 videos):**
- Total duration: ~5 hours
- Cost: ¥0 (within free tier)

---

## 📞 Support

If you encounter issues:
1. Run `python test_setup.py` to diagnose
2. Check this guide's troubleshooting section
3. Contact team lead for `.env` credentials
4. Check Azure Portal for service health

---

## 🎉 You're Ready!

Once setup is complete, you can:
- ✅ Generate subtitles for videos
- ✅ Run the Flask app locally
- ✅ Deploy to Azure Container Apps
- ✅ Collaborate with the team

Happy coding! 🚀
