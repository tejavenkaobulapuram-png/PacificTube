# 🤖 Automatic Subtitle Generation Guide

## Overview

PacificTube can now **automatically generate subtitles** from your video audio using **Azure Speech-to-Text AI**!

Just like YouTube's auto-captions, the system will:
1. **Listen to the video audio** 
2. **Convert speech to text** using AI
3. **Generate subtitle files** with perfect timing
4. **Display subtitles** when CC button is clicked

## 🎯 What You Need

### 1. Azure Speech Services (Required)

**Cost:** ~¥1.08 per hour of audio (Standard tier)
- First 5 hours/month = FREE!
- After that: ¥1.08 per hour

**How to Get:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "Speech Services" or "Cognitive Services"
3. Click "Create"
4. Fill in:
   - Resource Group: `rg-pacifictube`
   - Region: **Japan East** (same as your storage)
   - Name: `pacifictube-speech`
   - Pricing Tier: **Standard S0** (or Free F0 for testing)
5. Click "Review + Create"
6. Wait for deployment (~2 minutes)
7. Go to resource → **Keys and Endpoint**
8. Copy **KEY 1** and **Location/Region**

### 2. FFmpeg (Audio Extraction Tool)

**Windows Installation:**

**Option A: Chocolatey (Recommended)**
```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg -y
```

**Option B: Manual Download**
1. Go to https://www.gyan.dev/ffmpeg/builds/
2. Download "ffmpeg-release-essentials.zip"
3. Extract to `C:\ffmpeg`
4. Add `C:\ffmpeg\bin` to PATH:
   - Search "Environment Variables" in Windows
   - Edit "Path" → Add `C:\ffmpeg\bin`
   - Restart PowerShell

**Verify Installation:**
```powershell
ffmpeg -version
```

## 📝 Setup Instructions

### Step 1: Add Azure Speech Key to .env

Add these lines to your `.env` file:

```env
# Azure Speech Services for Auto-Subtitles
AZURE_SPEECH_KEY=your_speech_key_here
AZURE_SPEECH_REGION=japaneast
```

### Step 2: Install Python Dependencies

```powershell
pip install azure-cognitiveservices-speech
```

### Step 3: Run Subtitle Generator

```powershell
python generate_subtitles.py
```

## 🎬 Generating Subtitles for Your Videos

### Interactive Mode

Run the script:
```powershell
python generate_subtitles.py
```

It will ask you:
1. **Video ID**: Enter the blob path (e.g., `03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4`)
2. **Languages**: Enter language codes (e.g., `ja-JP` or `ja-JP,en-US`)

The script will:
- ✅ Download video from Azure
- ✅ Extract audio using FFmpeg
- ✅ Send to Azure Speech AI for transcription
- ✅ Generate `.vtt` subtitle file with timestamps
- ✅ Upload subtitle file to Azure Blob Storage
- ✅ **CC button will appear automatically!**

### Processing Time

- 1 hour video = ~5-10 minutes processing time
- Depends on video length and speech clarity

## 🌍 Supported Languages

| Language Code | Language | Example |
|---------------|----------|---------|
| `ja-JP` | Japanese | 日本語の会議 |
| `en-US` | English (US) | English meeting |
| `en-GB` | English (UK) | British English |
| `zh-CN` | Chinese (Simplified) | 简体中文 |
| `zh-TW` | Chinese (Traditional) | 繁體中文 |
| `ko-KR` | Korean | 한국어 |
| `es-ES` | Spanish | Español |
| `fr-FR` | French | Français |
| `de-DE` | German | Deutsch |
| `pt-BR` | Portuguese  | Português |

## 💰 Cost Calculation

### Speech Services Pricing (Japan East)

**Free Tier (F0):**
- 5 hours of audio/month = FREE
- Perfect for testing!

**Standard Tier (S0):**
- ¥1.08 per hour of audio
- Pay only for what you use

### Example Costs

| Video Length | Cost (Standard) | Cost (Free Tier) |
|--------------|-----------------|------------------|
| 30 minutes | ¥0.54 | FREE (if <5 hours/month) |
| 1 hour | ¥1.08 | FREE (if <5 hours/month) |
| 2 hours | ¥2.16 | FREE (if <5 hours/month) |
| 10 hours | ¥10.80 | ¥5.40 (5 hours free + 5 hours paid) |

### Your 7 Videos (~7 hours total)

**First Month:**
- Free tier: 5 hours FREE
- Paid: 2 hours × ¥1.08 = **¥2.16**
- **Total: ¥2.16** for all 7 videos! 🎉

**After That:**
- Re-generation not needed (subtitles are saved)
- Only generate subtitles for NEW videos

## 🚀 Quick Start Example

Let's generate subtitles for one video:

```powershell
# Step 1: Add Speech key to .env file
# AZURE_SPEECH_KEY=abc123your_key_here
# AZURE_SPEECH_REGION=japaneast

# Step 2: Install dependencies
pip install azure-cognitiveservices-speech

# Step 3: Run generator
python generate_subtitles.py

# Step 4: When prompted, enter:
# Video ID: 03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4
# Languages: ja-JP

# Step 5: Wait for processing (5-10 minutes)
# Step 6: Open video in PacificTube - CC button appears! ✅
```

## 📊 What the Output Looks Like

### Console Output:
```
============================================================
🎬 Processing: 03_定例会議/Recordings/video.mp4
============================================================

📥 Downloading video from URL...
🎵 Extracting audio with ffmpeg...
✅ Audio extracted to C:\Temp\audio.wav

--- Generating ja-JP subtitles ---

🎙️  Starting speech recognition (ja-JP)...
⏳ Transcribing... (this may take a few minutes)
✓ Recognized: 皆さん、こんにちは。本日の生成AI連携会議を始めます...
✓ Recognized: まず、議題の確認からお願いします...
✓ Recognized: 今月のAIモデル開発の進捗状況について報告いたします...
✅ Transcription complete! Generated 47 subtitle segments

📝 Generating VTT file: C:\Temp\subtitle_ja.vtt
✅ VTT file created successfully!

📤 Uploading subtitle to Azure Blob Storage...
✅ Uploaded: 03_定例会議/Recordings/video.ja.vtt

============================================================
🎉 SUCCESS! Generated 1 subtitle file(s):
   ✓ 03_定例会議/Recordings/video.ja.vtt
============================================================
```

### Generated VTT File:
```vtt
WEBVTT

00:00:00.000 --> 00:00:05.430
皆さん、こんにちは。本日の生成AI連携会議を始めます。

00:00:05.680 --> 00:00:10.210
まず、議題の確認からお願いします。

00:00:10.450 --> 00:00:15.890
今月のAIモデル開発の進捗状況について報告いたします。
```

## 🎯 Testing the Result

1. **Refresh PacificTube:**
   - https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io

2. **Open the video**

3. **Look for CC button** (bottom-right corner)
   - ✅ Should appear automatically!

4. **Click CC → Select "日本語"**

5. **Watch video**
   - Subtitles should appear showing the spoken words! 🎉
   - Synchronized perfectly with audio timing

## ⚙️ Batch Processing All Videos

Want to generate subtitles for ALL 7 videos at once?

Create `batch_generate.py`:

```python
from generate_subtitles import AutoSubtitleGenerator
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize generator
generator = AutoSubtitleGenerator(
    speech_key=os.environ.get('AZURE_SPEECH_KEY'),
    speech_region=os.environ.get('AZURE_SPEECH_REGION', 'japaneast'),
    storage_account=os.environ.get('AZURE_STORAGE_ACCOUNT_NAME'),
    blob_sas_token=os.environ.get('AZURE_STORAGE_SAS_TOKEN')
)

# List of your videos
videos = [
    "03_定例会議/Recordings/生成AI連携会議-20260116_145605-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250516_150120-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250612_105717-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250822_150009-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251121_145723-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251219_144752-会議の録音.mp4"
]

# Generate subtitles for each video
for video_id in videos:
    try:
        # Construct video URL
        storage_account = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
        blob_sas = os.environ.get('AZURE_STORAGE_SAS_TOKEN')
        video_url = f"https://{storage_account}.blob.core.windows.net/videos/{video_id}?{blob_sas}"
        
        # Generate Japanese and English subtitles
        generator.process_video(video_id, video_url, languages=['ja-JP', 'en-US'])
        
    except Exception as e:
        print(f"❌ Failed to process {video_id}: {e}")
        continue

print("\n🎉 Batch processing complete!")
```

Run it:
```powershell
python batch_generate.py
```

This will generate subtitles for all 7 videos (will take ~1-2 hours total).

## ❓ Troubleshooting

### Error: "FFmpeg not found"
**Solution:** Install FFmpeg using Chocolatey or manual download (see above)

### Error: "Speech key is invalid"
**Solution:** Check your `.env` file has the correct `AZURE_SPEECH_KEY`

### Error: "Quota exceeded"
**Solution:** 
- You've used more than 5 hours on Free tier
- Upgrade to Standard S0 tier (¥1.08/hour)
- Or wait until next month for free tier reset

### Error: "Audio extraction failed"
**Solution:**
- Video might be corrupted
- Try downloading video manually and check if it plays
- Check FFmpeg is installed correctly

### Subtitles are not accurate
**Solution:**
- Speech recognition works best with clear audio
- Background noise reduces accuracy
- For important videos, consider manual subtitle editing

## 🎬 Final Result

After generating subtitles, when you watch a video in PacificTube:

1. **CC button appears** (bottom-right)
2. **Click CC** → Shows "日本語", "English", "Off"
3. **Select language** → Button turns blue
4. **Watch video** → Subtitles appear automatically!
5. **Subtitles show exactly what is being said** in the video audio

**The spoken words will appear as text on the screen synchronized with the audio! Just like YouTube!** 🎉

---

**Setup Time:** 15-30 minutes (one-time setup)  
**Cost:** ¥2-10 (for processing 7 meeting videos)  
**Result:** All future videos can have automatic subtitles with one command!
