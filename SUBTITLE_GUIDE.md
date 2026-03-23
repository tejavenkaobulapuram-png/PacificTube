# 📝 Subtitle Support Documentation

## Overview

PacificTube now supports **multi-language subtitles** just like YouTube! Users can:
- Turn subtitles on/off using the video player controls
- Choose from multiple languages
- See subtitles synchronized with the video

## 🎬 Subtitle File Format

Subtitle files use **WebVTT (Web Video Text Tracks)** format - the standard for HTML5 video.

### Naming Convention

For each video, create subtitle files with language codes:

```
Video file:          生成AI連携会議-20260220_145636-会議の録音.mp4
Japanese subtitles:  生成AI連携会議-20260220_145636-会議の録音.ja.vtt
English subtitles:   生成AI連携会議-20260220_145636-会議の録音.en.vtt
Chinese subtitles:   生成AI連携会議-20260220_145636-会議の録音.zh.vtt
```

**Pattern:** `{video_name_without_extension}.{language_code}.vtt`

### Supported Language Codes

| Code | Language | Display Name |
|------|----------|--------------|
| `ja` | Japanese | 日本語 |
| `en` | English  | English |
| `zh` | Chinese  | 中文 |
| `ko` | Korean   | 한국어 |
| `es` | Spanish  | Español |
| `fr` | French   | Français |
| `de` | German   | Deutsch |
| `pt` | Portuguese | Português |
| `ru` | Russian  | Русский |
| `ar` | Arabic   | العربية |

## 📄 WebVTT File Format

### Basic Structure

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.000
Welcome to the meeting. Today we will discuss AI development.

00:00:05.500 --> 00:00:10.000
First, let's review the progress from last month.

00:00:10.500 --> 00:00:15.000
The AI model performance has improved by 15%.
```

### Timestamp Format

- `HH:MM:SS.milliseconds` (e.g., `00:01:23.456`)
- Always starts with `WEBVTT` header
- Blank line between subtitle blocks

### Sample Japanese Subtitle (.ja.vtt)

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.000
会議へようこそ。本日はAI開発について議論します。

00:00:05.500 --> 00:00:10.000
まず、先月の進捗状況を確認しましょう。

00:00:10.500 --> 00:00:15.000
AIモデルのパフォーマンスが15%向上しました。

00:00:15.500 --> 00:00:20.000
次のステップは、データセットの拡張です。
```

### Sample English Subtitle (.en.vtt)

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.000
Welcome to the meeting. Today we will discuss AI development.

00:00:05.500 --> 00:00:10.000
First, let's review the progress from last month.

00:00:10.500 --> 00:00:15.000
The AI model performance has improved by 15%.

00:00:15.500 --> 00:00:20.000
The next step is to expand the dataset.
```

## 🔧 How to Create Subtitle Files

### Method 1: Manual Creation

1. Create a text file with `.vtt` extension
2. Add `WEBVTT` as the first line
3. Add timestamps and text
4. Save with UTF-8 encoding

### Method 2: Transcription Services

**Automatic Transcription (Recommended):**

1. **Azure Speech Services:**
   ```python
   # Use Azure Speech-to-Text API
   # Automatically generates timestamps
   ```

2. **YouTube Auto-Captions:**
   - Upload video to YouTube (private)
   - Wait for auto-captions
   - Download as .vtt file
   - Rename to match your video

3. **Online Tools:**
   - [Subtitle Edit](https://www.nikse.dk/subtitleedit) (Free, Windows)
   - [Aegisub](http://www.aegisub.org/) (Free, Cross-platform)
   - [Subtitle Workshop](http://subworkshop.sourceforge.net/) (Free)

### Method 3: Speech-to-Text (Python)

```python
# Example using Azure Speech Services
import azure.cognitiveservices.speech as speechsdk

def transcribe_video_to_vtt(video_file, output_vtt):
    speech_config = speechsdk.SpeechConfig(
        subscription="YOUR_KEY",
        region="japaneast"
    )
    speech_config.speech_recognition_language = "ja-JP"
    
    audio_config = speechsdk.audio.AudioConfig(filename=video_file)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    # Continuous recognition with timestamps
    # Generate WebVTT file
    # (Full implementation available on request)
```

## 📤 How to Upload Subtitle Files

### Option 1: Azure Portal

1. Go to Azure Portal → Storage Accounts
2. Navigate to `pacifictubestorage` → `videos` container
3. Find your video folder (e.g., `03_定例会議/Recordings/`)
4. Click **Upload**
5. Select your `.vtt` file(s)
6. Upload

### Option 2: Azure CLI

```powershell
# Upload Japanese subtitle
az storage blob upload \
  --account-name pacifictubestorage \
  --container-name videos \
  --name "03_定例会議/Recordings/video.ja.vtt" \
  --file "path/to/local/video.ja.vtt"

# Upload English subtitle
az storage blob upload \
  --account-name pacifictubestorage \
  --container-name videos \
  --name "03_定例会議/Recordings/video.en.vtt" \
  --file "path/to/local/video.en.vtt"
```

### Option 3: Python Script

```python
from azure.storage.blob import BlobServiceClient

# Connection string
connection_string = "YOUR_CONNECTION_STRING"
blob_service = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service.get_container_client("videos")

# Upload subtitle
with open("video.ja.vtt", "rb") as data:
    blob_client = container_client.upload_blob(
        name="03_定例会議/Recordings/video.ja.vtt",
        data=data,
        overwrite=True
    )
```

## 🎥 How It Works

1. **User opens video** → PacificTube calls `/api/subtitles/{video_id}`
2. **Backend scans** Azure Blob Storage for `.vtt` files matching the video name
3. **Returns available subtitles** with language codes and URLs
4. **Frontend adds `<track>` elements** to the video player
5. **User can toggle** subtitles using the video player CC button

## 🔍 Testing

### Create a Test Subtitle

1. Create `test-subtitle.ja.vtt`:
   ```vtt
   WEBVTT

   00:00:00.000 --> 00:00:03.000
   これはテスト字幕です。

   00:00:03.000 --> 00:00:06.000
   字幕が正しく表示されていますか？
   ```

2. Upload to same folder as your video

3. Refresh the application and open the video

4. Look for CC button in video controls

5. Toggle subtitles on/off

## ❓ FAQ

### Q: Do subtitle files need to be in the same folder as the video?
**A:** Yes, subtitle files must be in the same Azure Blob Storage folder as the video file.

### Q: Can I have multiple languages for one video?
**A:** Yes! Just create multiple `.vtt` files with different language codes (e.g., `video.ja.vtt`, `video.en.vtt`, `video.zh.vtt`).

### Q: Which subtitle shows by default?
**A:** The first subtitle found (alphabetically by language code) is set as default. Usually `en` (English) if available, otherwise `ja` (Japanese).

### Q: How do I turn subtitles off?
**A:** Click the CC  (closed captions) button in the video player controls, then select "Off".

### Q: Can I edit subtitles after uploading?
**A:** Yes, download the `.vtt` file from Azure, edit it, and re-upload with the same name.

### Q: What if my subtitle timing is off?
**A:** Edit the timestamp values in the `.vtt` file. Each timestamp uses the format `HH:MM:SS.milliseconds`.

### Q: Do subtitles work on mobile devices?
**A:** Yes! WebVTT is supported by all modern browsers on desktop and mobile.

## 🚀 Next Steps

1. **Create subtitle files** for your important videos
2. **Upload to Azure Blob Storage** in the same folder as the videos
3. **Test in the application** - subtitles should appear automatically
4. **Gather feedback** from users about subtitle quality
5. **Consider auto-transcription** using Azure Speech Services for future videos

## 💡 Pro Tips

- **Keep lines short** - Max 2 lines per subtitle, ~40 characters per line
- **Sync carefully** - Subtitles should appear slightly before the speech
- **Use proper encoding** - Save .vtt files as UTF-8 (important for Japanese)
- **Test on multiple devices** - Check subtitles on desktop, tablet, and mobile
- **Backup subtitle files** - Keep local copies in case you need to re-upload

## 📊 Cost Impact

- Subtitle files are very small (~5-50 KB)
- Minimal storage cost impact (<¥1/month for 100 subtitle files)
- No additional egress cost (served with same SAS token as videos)

---

**Documentation Version:** 1.0  
**Last Updated:** March 23, 2026  
**Supported Languages:** 10 (ja, en, zh, ko, es, fr, de, pt, ru, ar)
