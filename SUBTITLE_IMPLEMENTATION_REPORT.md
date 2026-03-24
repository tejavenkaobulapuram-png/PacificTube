# PacificTube Subtitle Feature - Implementation Report
## Date: March 24, 2026

---

## 1. OBJECTIVE

Implement automatic Japanese subtitle generation for meeting recording videos in PacificTube application.

---

## 2. PROBLEM STATEMENT

- 7 meeting videos stored in Azure Blob Storage
- Users requested CC (Closed Caption) functionality for video playback
- Subtitles needed to be generated automatically from video audio
- Videos range from 40-90 minutes in duration

---

## 3. INITIAL APPROACH (Failed)

### What We Tried First:
- Used Azure Speech Services **Continuous Recognition API** (Real-time SDK)
- Free F0 tier in Japan East region

### Results:
| Video | Status | Issue |
|-------|--------|-------|
| 20260220 | Complete | Worked |
| 20260116 | Complete | Worked |
| 20250516 | Complete | Worked |
| 20250822 | Partial | Stopped at 20:27 min |
| 20251121 | Failed | Only 448 bytes |
| 20251219 | Failed | Only 10 bytes |
| 20250612 | Failed | Only 10 bytes |

### Root Cause Identified:
- Continuous Recognition API has **20-30 minute session limit**
- This is a hardcoded limitation, NOT a tier restriction
- Long videos exceed this session duration limit

---

## 4. SOLUTION IMPLEMENTED

### Changed Approach:
- Switched from Continuous Recognition API to **Batch Transcription API**
- Upgraded Speech Service tier from Free F0 to **Standard S0**

### Why Batch Transcription API:
| Feature | Continuous Recognition | Batch Transcription |
|---------|------------------------|---------------------|
| Max Duration | 20-30 minutes | 10 hours |
| Session Timeout | Yes | No |
| Processing | Real-time | Asynchronous |
| Best For | Live streaming | Recorded files |

### Changes Made:

1. **Created new file:** `generate_subtitles_batch.py`
   - Implements Azure Batch Transcription API
   - Handles long audio files without timeout
   - Includes smart detection of incomplete subtitles

2. **Created new file:** `regenerate_with_batch_api.py`
   - Scans all videos for incomplete subtitles
   - Skips already completed videos (saves cost)
   - Processes only failed/partial subtitles

3. **Upgraded Azure Speech Service:**
   - Changed from: Free F0
   - Changed to: Standard S0
   - Cost: ~0.0108 JPY per minute

---

## 5. TECHNICAL IMPLEMENTATION DETAILS

### Workflow:
```
1. Check existing subtitle file size
   - If > 100KB AND last timestamp > 30min → SKIP
   - If < 100KB OR last timestamp < 30min → REGENERATE

2. Download video from Azure Blob Storage

3. Extract audio using FFmpeg
   - Format: WAV, 16kHz, mono, 16-bit PCM

4. Upload audio to Azure Blob Storage (temporary)

5. Submit to Batch Transcription API
   - Language: ja-JP (Japanese)
   - Word-level timestamps enabled

6. Poll for completion (typically 5-10 minutes)

7. Download transcription results

8. Convert to WebVTT format with timestamps

9. Upload .vtt file to Azure Blob Storage

10. Cleanup: Delete temporary files and transcription job
```

### Files Modified/Created:

| File | Action | Purpose |
|------|--------|---------|
| `generate_subtitles_batch.py` | Created | Batch Transcription API implementation |
| `regenerate_with_batch_api.py` | Created | Smart regeneration script |
| `generate_subtitles.py` | Modified | Added silence timeout settings |
| `.env` | Updated | Added Speech Service credentials |

---

## 6. FINAL RESULTS

### Subtitle Generation Status:

| Video | Before | After | Size |
|-------|--------|-------|------|
| 生成AI連携会議-20260220 | Complete | - | 152 KB |
| 生成AI連携会議-20260116 | Complete | - | 140 KB |
| 生成AI関連情報連携会議-20250516 | Complete | - | 121 KB |
| 生成AI関連情報連携会議-20250822 | Partial (51KB) | Complete | 135 KB |
| 生成AI連携会議-20251121 | Failed (448 bytes) | Complete | ~120 KB |
| 生成AI連携会議-20251219 | Failed (10 bytes) | Complete | ~130 KB |
| 生成AI関連情報連携会議-20250612 | Failed (10 bytes) | Complete | ~100 KB |

### Summary:
- **Before:** 3/7 videos working (43%)
- **After:** 7/7 videos working (100%)

---

## 7. COST ANALYSIS

### One-Time Batch Processing Cost:
| Video | Duration | Cost (JPY) |
|-------|----------|------------|
| 20250822 (partial) | ~40 min | ~0.43 |
| 20251121 | ~50 min | ~0.54 |
| 20251219 | ~70 min | ~0.76 |
| 20250612 | ~45 min | ~0.49 |
| **Total** | ~205 min | **~2.22 JPY** |

### Ongoing Monthly Cost:
- Speech Service S0: Pay-per-use only
- No monthly minimum
- Future videos: ~0.65 JPY per 60-minute video

---

## 8. SECURITY CONSIDERATIONS

### Data Protection:
- All processing in **Azure Japan East** region
- Data never leaves Japan
- Encrypted in transit (TLS 1.2) and at rest (AES-256)

### Microsoft Compliance:
- ISO 27001 certified
- SOC 2 Type 2 certified
- Does NOT use customer data for AI training
- Auto-deletes processed audio after completion

### Our Implementation:
- Temporary audio files deleted after processing
- Transcription jobs cleaned up immediately
- SAS tokens with limited permissions

---

## 9. HOW TO USE

### For End Users:
1. Open PacificTube: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io
2. Select a video
3. Click the **CC** button
4. Select **日本語** (Japanese)
5. Subtitles will display during playback

### For Administrators (New Video):
```powershell
# Run batch transcription for new videos
python regenerate_with_batch_api.py
```

---

## 10. FILES DEPLOYED

| File | Location | Purpose |
|------|----------|---------|
| `generate_subtitles_batch.py` | GitHub repo | Batch API implementation |
| `generate_subtitles.py` | GitHub repo | Base subtitle generator |
| `regenerate_with_batch_api.py` | GitHub repo | Smart regeneration script |
| Container App | Azure Japan East | Web application |
| Subtitle files (.vtt) | Azure Blob Storage | Japanese subtitles |

---

## 11. LESSONS LEARNED

1. **Continuous Recognition API** is designed for real-time streaming, not batch processing
2. **Batch Transcription API** is the correct choice for pre-recorded files
3. Free F0 tier does not support Batch API (requires S0)
4. Always check last timestamp in subtitle file, not just file size
5. Unicode characters (emojis) cause errors in Windows PowerShell

---

## 12. FUTURE RECOMMENDATIONS

1. **Automated Processing:** Set up Azure Function to auto-generate subtitles when new video is uploaded
2. **Multiple Languages:** Add English subtitle generation option
3. **Quality Review:** Implement subtitle editing interface for corrections
4. **Cost Monitoring:** Set up Azure budget alerts for Speech Service usage

---

## Report Prepared By:
GitHub Copilot Agent

## Date:
March 24, 2026
