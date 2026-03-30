# PacificTube Architecture with Entra ID Authentication

## Visual Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Microsoft Azure Cloud                       │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Microsoft  │                                               │
│  │    Azure     │                                               │
│  │   (Entra ID) │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         │                    ┌──────────────────┐              │
│         │                    │ Container Registry│              │
│         ↓                    │      (ACR)       │              │
│  ┌──────────────┐            │ ┌──────────────┐│              │
│  │   Browser    │───HTTPS───→│ │Backend Image ││              │
│  │              │            │ │Frontend Image││              │
│  │(User Access) │            │ └──────────────┘│              │
│  └──────────────┘            └────────┬─────────┘              │
│         │                             │                         │
│         │                             ↓                         │
│         │              ┌──────────────────────────────┐        │
│         │              │  Azure Container Apps        │        │
│         │              │                              │        │
│         │              │  ┌────────────────────────┐ │        │
│         │              │  │  Container (Backend)   │ │        │
│         └─────────────→│  │                        │ │        │
│                        │  │  ┌──────────────────┐ │ │        │
│                        │  │  │  Flask App       │ │ │        │
│                        │  │  │  • app.py        │ │ │        │
│                        │  │  │  • MSAL Auth     │ │ │        │
│                        │  │  │  • REST API      │ │ │        │
│                        │  │  │  • Video Service │ │ │        │
│                        │  │  └──────────────────┘ │ │        │
│                        │  └───────┬────────────────┘ │        │
│                        │          │                  │        │
│                        │  ┌───────┴──────────────┐   │        │
│                        │  │  Container (Frontend)│   │        │
│                        │  │                      │   │        │
│                        │  │  ┌────────────────┐ │   │        │
│                        │  │  │  HTML5         │ │   │        │
│                        │  │  │  CSS3          │ │   │        │
│                        │  │  │  JavaScript    │ │   │        │
│                        │  │  └────────────────┘ │   │        │
│                        │  └──────────────────────┘   │        │
│                        └──────┬────┬────┬────────────┘        │
│                               │    │    │                      │
│  ┌────────────────────────────┘    │    └────────────────┐    │
│  │                                 │                     │    │
│  ↓                                 ↓                     ↓    │
│ ┌──────────────────┐   ┌──────────────────┐   ┌──────────┐  │
│ │ Azure Blob       │   │ Azure Computer   │   │  Azure   │  │
│ │ Storage          │   │ Vision (OCR)     │   │  Speech  │  │
│ │ (pacifictubesa)  │   │                  │   │ Service  │  │
│ │                  │   │ • Slide change   │   │          │  │
│ │ • Videos (.mp4)  │   │ • Text extract   │   │ • Audio→ │  │
│ │ • Subtitles(.vtt)│   │ • FREE TIER ¥0   │   │   Text   │  │
│ │ • Chapters(.json)│   │                  │   │ • ¥150/h │  │
│ └──────────────────┘   └──────────────────┘   └──────────┘  │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Resource Group: rg-pacifictube                │  │
│  │           Region: Japan East                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           ↕ ↕ CI/CD
                    ┌──────────────┐
                    │    GitHub    │
                    │  Repository  │
                    │ PacificTube  │
                    └──────────────┘
```

## Detailed Component Description

### External Layer
**User** → **Browser** → **Azure AD (Entra ID)** → **Authenticated Access**

### Container Registry (ACR)
- **Backend Image**: Flask application container
- **Frontend Image**: Static files (HTML/CSS/JS) container

### Azure Container Apps (Main Application)

#### Container (Backend)
```
Flask Application
├── app.py (Web Server)
├── MSAL Authentication (Entra ID integration)
├── REST API endpoints
│   ├── /api/videos (List videos)
│   ├── /api/subtitles/<video_id> (Get subtitles)
│   ├── /api/chapters/<video_id> (Get chapters)
│   ├── /api/like/<video_id> (Like video)
│   ├── /api/comment/<video_id> (Post comment)
│   └── /api/download/<video_id> (Download video)
├── Video Service (Blob Storage integration)
├── Engagement Tracker (likes/dislikes)
└── View Tracker (view counts)
```

#### Container (Frontend)
```
Static Web Files
├── HTML5 (index.html)
│   └── Video player, UI templates
├── CSS3 (style.css)
│   └── YouTube-style design
└── JavaScript (script.js)
    ├── Video player controls
    ├── Subtitle management
    ├── Chapter navigation
    ├── Search functionality
    └── Engagement interactions
```

### Azure Services (Backend Integration)

#### 1. Azure Blob Storage (pacifictubesa)
- **Videos container**: .mp4 files (14 videos, ~4.7GB)
- **Subtitles**: .vtt files (Japanese/English)
- **Chapters**: .json files (169 chapters total)
- **Thumbnails**: Auto-generated preview images
- **Cost**: ~¥20/month for storage

#### 2. Azure Computer Vision (OCR)
- **Purpose**: Automatic chapter generation
- **Function**: 
  - Detect slide changes in video
  - Extract text from slides (Japanese)
  - Generate chapter titles
- **Cost**: FREE TIER (5,000 calls/month) = **¥0**

#### 3. Azure Speech Service
- **Purpose**: Automatic subtitle generation
- **Function**:
  - Audio extraction from video
  - Speech-to-text transcription
  - Multi-language support (Japanese/English)
- **Cost**: ~¥150 per hour of audio

### Resource Group
- **Name**: rg-pacifictube
- **Region**: Japan East
- **Subscription**: Tejya_Test_PCKK先端センター_AI開発

### GitHub Repository
- **URL**: github.com/tejavenkaobulapuram-png/PacificTube
- **Contains**:
  - Source code (Python/Flask/HTML/CSS/JS)
  - Dockerfile
  - Deployment scripts
  - Utility scripts (chapter/subtitle generators)
- **CI/CD**: Git push → Azure deployment trigger

---

## Authentication Flow (Entra ID)

```
1. User opens browser
   ↓
2. Navigate to PacificTube URL
   ↓
3. Check if authenticated
   ├─ NO → Redirect to Azure AD login
   │        ↓
   │     Enter company credentials
   │        ↓
   │     Azure AD validates
   │        ↓
   │     Generate OAuth token (JWT)
   │        ↓
   │     Redirect back with token
   │
   └─ YES → Access granted
              ↓
4. Browse videos, play, interact
   ↓
5. All API calls include JWT token for authorization
```

---

## Data Flow Example: Video Playback

```
[User clicks video]
       ↓
[Frontend sends request with JWT token]
       ↓
[Backend validates JWT with Azure AD]
       ↓
[Backend fetches video metadata]
       ↓
┌──────┴──────┬─────────────┬────────────┐
│             │             │            │
↓             ↓             ↓            ↓
Video URL    Subtitle URL  Chapters    Related Videos
(Blob)       (Blob)        (Blob)      (Blob list)
       │             │             │            │
       └──────┬──────┴─────────────┴────────────┘
              ↓
[Return JSON response to frontend]
              ↓
[Frontend renders video player with all features]
              ↓
[User watches video with subtitles + chapters]
```

---

## Deployment Architecture

```
Developer (Local)
    ↓
[Git commit & push]
    ↓
GitHub Repository
    ↓
[Trigger: push to main branch]
    ↓
Azure Container Registry
    ↓
[Build Docker images]
    ↓
Azure Container Apps
    ↓
[Deploy new revision]
    ↓
Live Application (HTTPS)
```

---

## Cost Breakdown (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| Container Apps | Always-on hosting | ~¥85 |
| Blob Storage | 4.7GB + bandwidth | ~¥20 |
| Computer Vision | OCR (free tier) | ¥0 |
| Speech Service | Per video generation | ¥150/hour |
| Container Registry | Image storage | ~¥100 |
| **Total (base)** | Without new videos | **~¥205/month** |

**Note**: Speech Service cost is only incurred when generating new subtitles (¥150 per hour of video).

---

## Key Components Summary

### Backend Container Components:
1. **Flask** - Python web framework
2. **MSAL** - Microsoft Authentication Library (Entra ID)
3. **SharePoint REST API** - (if needed for future integration)
4. **Azure SDK** - Blob Storage, Computer Vision, Speech Service clients

### Frontend Container Components:
1. **HTML5** - Video player, responsive layout
2. **CSS3** - YouTube-style design, animations
3. **JavaScript** - Interactive features, API calls

### Security Features:
- **Entra ID Authentication** - Company SSO login
- **JWT Tokens** - Secure API authorization
- **SAS Tokens** - Time-limited blob access
- **HTTPS** - Encrypted communication
