# Subtitle Generation Workflow Options
## Efficient Solutions for Team Collaboration

---

## ❌ **WRONG Way (Inefficient):**

```
Team Member A generates subtitles on their PC (5-10 min) ❌
Team Member B generates subtitles on their PC (5-10 min) ❌  
Team Member C generates subtitles on their PC (5-10 min) ❌
→ Everyone wastes time doing the same work!
```

---

## ✅ **CORRECT Way (Efficient):**

### **Option 1: Centralized Generation (Recommended for Now)**

**Setup:**
1. **ONE person** (you or content manager) has FFmpeg installed
2. When new video is uploaded to Azure → Generate subtitles once
3. Subtitle (.vtt) file uploads to Azure automatically

**For Everyone Else:**
- Open PacificTube website → Click video → Click CC button
- **Subtitles load instantly from Azure** (no waiting!)
- No FFmpeg needed ✅
- No Python scripts needed ✅
- No subtitle generation needed ✅

**Workflow:**
```
Content Manager:
├── Upload video.mp4 to Azure Blob Storage
├── Run: python quick_subtitle.py
├── Script generates video.ja.vtt
└── Uploads to Azure (1 minute)

Team Members (50+ people):
├── Open: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io
├── Click video
├── Click CC button
└── Watch with subtitles (instant!) ✅
```

---

### **Option 2: Batch Generation Script (For Initial Setup)**

For your 7 existing videos, generate all subtitles at once:

```powershell
# Run on YOUR PC (one time only)
python batch_generate_all.py
```

This will:
- Process all 7 videos sequentially
- Take ~30-60 minutes total (one time)
- Upload all .vtt files to Azure
- Everyone can see subtitles immediately after ✅

**Create the script:**

```python
# batch_generate_all.py
from generate_subtitles import AutoSubtitleGenerator
import os
from dotenv import load_dotenv

load_dotenv()

generator = AutoSubtitleGenerator(
    speech_key=os.environ.get('AZURE_SPEECH_KEY'),
    speech_region=os.environ.get('AZURE_SPEECH_REGION'),
    storage_account=os.environ.get('AZURE_STORAGE_ACCOUNT_NAME'),
    blob_sas_token=os.environ.get('AZURE_STORAGE_SAS_TOKEN')
)

# List of all videos
videos = [
    "03_定例会議/Recordings/生成AI連携会議-20260116_145605-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250516_150120-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250612_105717-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250822_150009-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251121_145723-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251219_144752-会議の録音.mp4",
]

print(f"🎬 Generating subtitles for {len(videos)} videos...")
print(f"⏱️  Estimated time: {len(videos) * 7} minutes")
print(f"💰 Cost: ¥0 (within free 5 hours/month)\n")

for i, video_id in enumerate(videos, 1):
    print(f"\n{'='*70}")
    print(f"[{i}/{len(videos)}] Processing: {video_id.split('/')[-1]}")
    print(f"{'='*70}")
    
    try:
        generator.process_video(video_id=video_id, languages=['ja-JP'])
        print(f"✅ Completed: {video_id.split('/')[-1]}")
    except Exception as e:
        print(f"❌ Failed: {video_id.split('/')[-1]}")
        print(f"Error: {e}")
        continue

print("\n" + "="*70)
print("🎉 All subtitles generated!")
print("="*70)
```

---

### **Option 3: Automated Azure Function (Future Enhancement)**

**For fully automated workflow:**

```
New video uploaded to Azure Blob Storage
    ↓
Azure Blob Trigger activates
    ↓
Azure Function runs subtitle generation
    ↓
Subtitle .vtt file auto-uploaded
    ↓
Everyone sees subtitles immediately ✅
```

**Benefits:**
- Zero manual work
- Instant subtitle generation on upload
- No FFmpeg on anyone's PC
- Scales automatically

**Setup:**
1. Create Azure Function with Python runtime
2. Deploy `generate_subtitles.py` to Azure Function
3. Set Blob Storage trigger for new video uploads
4. Subtitles generate automatically

**Cost:**
- Azure Functions: ¥0 (1 million free executions/month)
- Speech Services: ¥0 first 5 hours, then ¥1.08/hour

---

### **Option 4: GitHub Actions CI/CD (Alternative)**

**Workflow:**
```yaml
# .github/workflows/generate-subtitles.yml
name: Generate Subtitles

on:
  workflow_dispatch:
    inputs:
      video_id:
        description: 'Video ID (e.g., 03_定例会議/Recordings/video.mp4)'
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install FFmpeg
        run: sudo apt-get install -y ffmpeg
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Generate subtitles
        env:
          AZURE_SPEECH_KEY: ${{ secrets.AZURE_SPEECH_KEY }}
          AZURE_SPEECH_REGION: japaneast
          AZURE_STORAGE_ACCOUNT_NAME: pacifictubestorage
          AZURE_STORAGE_SAS_TOKEN: ${{ secrets.AZURE_STORAGE_SAS_TOKEN }}
        run: |
          python -c "
          from generate_subtitles import AutoSubtitleGenerator
          import os
          
          generator = AutoSubtitleGenerator(
              speech_key=os.environ['AZURE_SPEECH_KEY'],
              speech_region=os.environ['AZURE_SPEECH_REGION'],
              storage_account=os.environ['AZURE_STORAGE_ACCOUNT_NAME'],
              blob_sas_token=os.environ['AZURE_STORAGE_SAS_TOKEN']
          )
          
          generator.process_video(
              video_id='${{ github.event.inputs.video_id }}',
              languages=['ja-JP']
          )
          "
```

**Usage:**
1. Upload video to Azure Blob Storage
2. Go to GitHub Actions tab
3. Click "Generate Subtitles"
4. Enter video ID
5. Subtitles generate in the cloud ✅

**Benefits:**
- No local FFmpeg needed
- Runs in GitHub's cloud infrastructure
- Free for public repos, 2000 minutes/month for private

---

## 📊 **Comparison Table:**

| Option | Setup Time | Recurring Work | Best For |
|--------|-----------|----------------|----------|
| **Option 1: Manual** | 5 min | 5-10 min/video | Current (7 videos) |
| **Option 2: Batch Script** | 0 min | 60 min once | Initial setup |
| **Option 3: Azure Function** | 2 hours | Fully automatic ✅ | Long-term (100+ videos) |
| **Option 4: GitHub Actions** | 30 min | Semi-automatic | Medium-term (20-50 videos) |

---

## 💡 **Recommended Path:**

### **Phase 1: NOW (This Week)**
Use **Option 2** (Batch Script):
1. You run `batch_generate_all.py` once on your PC
2. Generates all 7 videos in ~60 minutes
3. All team members see subtitles immediately
4. Done! ✅

### **Phase 2: FUTURE (If uploading 10+ new videos/month)**
Upgrade to **Option 3** (Azure Function):
1. One-time setup (2 hours)
2. Upload video → Subtitles appear automatically
3. Zero manual work forever ✅

---

## 🎯 **Key Takeaway:**

**Team members DON'T need:**
❌ FFmpeg installed  
❌ Python scripts  
❌ Subtitle generation  

**They ONLY need:**
✅ Web browser  
✅ Internet connection  
✅ Link to PacificTube  

**Why?** Because subtitles are stored in Azure Blob Storage, not on your PC!

---

## 📞 **Which Option Should You Choose?**

Answer these questions:

1. **How many videos will you upload per month?**
   - 0-3 videos → Option 1 (Manual, 5 min each)
   - 4-10 videos → Option 4 (GitHub Actions)
   - 10+ videos → Option 3 (Azure Function)

2. **Do you want to spend 2 hours setting up automation?**
   - Yes → Option 3 or 4
   - No → Option 1 or 2

3. **Is this a one-time task (7 videos) or ongoing?**
   - One-time → Option 2 (Batch script)
   - Ongoing → Option 3 (Azure Function)

---

## 🚀 **Quick Start (Recommended):**

Since you have **7 videos total** and may add more occasionally:

```powershell
# Step 1: Create batch script (I'll create this for you)
# Step 2: Run once on your PC
python batch_generate_all.py

# That's it! All 7 videos get subtitles in ~60 minutes
# Team members can watch immediately after with CC button
```

Want me to create the batch script now?
