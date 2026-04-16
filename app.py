"""
Pacific Tube - Flask Application
YouTube-style video gallery for Azure Blob Storage
"""

# Load environment variables FIRST (before other imports)
from dotenv import load_dotenv
load_dotenv()

import logging
import sys

# Configure logging for Azure Container Apps
# Logs go to stdout which Azure captures automatically
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [PacificTube] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('PacificTube')

# Suppress verbose Azure SDK logging (reduces noise in logs)
logging.getLogger('azure').setLevel(logging.WARNING)
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

from flask import Flask, render_template, jsonify, request, send_file, session, Response
from flask_caching import Cache
from flask_session import Session
from azure.storage.blob import BlobServiceClient, ContainerClient
import config
from datetime import datetime
from urllib.parse import quote
from view_tracker import ViewTracker
from cloud_view_tracker import CloudViewTracker
from engagement_tracker import EngagementTracker
from entra_auth import EntraIDAuth, setup_auth_routes
from telemetry import TelemetryTracker, initialize_tables
from dashboard import dashboard_bp
import os
import io
import requests
import secrets
import time
from collections import defaultdict

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Initialize caching for cost optimization (also used for sessions)
# Simple memory cache - reduces Azure Blob Storage API calls by 70-80%
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',  # In-memory cache
    'CACHE_DEFAULT_TIMEOUT': 86400  # 24 hours default
})

# Configure session to use in-memory cache (faster & safer than filesystem)
app.config['SESSION_TYPE'] = 'cachelib'
app.config['SESSION_CACHELIB'] = cache.cache  # Reuse Flask-Caching instance
app.config['SESSION_PERMANENT'] = os.getenv('SESSION_PERMANENT', 'False').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600'))

# Initialize Flask-Session for Entra ID authentication
Session(app)

# Initialize Entra ID authentication
entra_auth = EntraIDAuth(app)
setup_auth_routes(app, entra_auth)

# Register dashboard blueprint for analytics
app.register_blueprint(dashboard_bp)

# Initialize telemetry tables in Table Storage
initialize_tables()

# Rate limiting for like/dislike to prevent double-clicks
# Store last request time per user+video+action
rate_limit_store = defaultdict(float)


class VideoService:
    """Service to interact with Azure Blob Storage"""
    
    def __init__(self, view_tracker):
        # Create blob service client with SAS token
        sas_url = f"{config.BLOB_SERVICE_URL}?{config.SAS_TOKEN}"
        self.blob_service_client = BlobServiceClient(account_url=sas_url)
        self.container_client = self.blob_service_client.get_container_client(config.CONTAINER_NAME)
        self.view_tracker = view_tracker
        
        # Load video metadata (uploader information)
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load video metadata from JSON file"""
        import json
        metadata_file = 'video_metadata.json'
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading metadata: {e}")
                return {}
        return {}
    
    def get_videos(self):
        """Fetch all video files from blob storage"""
        videos = []
        video_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.mkv']
        
        try:
            # List blobs with optional folder prefix
            prefix = f"{config.FOLDER_PATH}/" if config.FOLDER_PATH else ""
            
            for blob in self.container_client.list_blobs(name_starts_with=prefix):
                # Check if it's a video file
                if any(blob.name.lower().endswith(ext) for ext in video_extensions):
                    # Get display name (remove folder prefix if exists)
                    display_name = blob.name[len(prefix):] if prefix else blob.name
                    
                    # SECURITY: Do NOT include SAS token in video list
                    # Frontend must request URL from /api/video-url endpoint
                    # This prevents URL sharing and enables audit logging
                    
                    # Get uploader and description from metadata
                    metadata = self.metadata.get(blob.name, {})
                    uploader = metadata.get('uploader', '不明')
                    description = metadata.get('description', '')
                    
                    video_data = {
                        'id': blob.name,
                        'name': display_name,
                        'url': None,  # URL fetched on-demand from /api/video-url
                        'size': blob.size,
                        'lastModified': blob.last_modified.isoformat() if blob.last_modified else None,
                        'contentType': blob.content_settings.content_type if blob.content_settings else 'video/mp4',
                        'folder': blob.name.rsplit('/', 1)[0] if '/' in blob.name else '',
                        'views': self.view_tracker.get_view_count(blob.name),
                        'uploader': uploader,
                        'description': description
                    }
                    videos.append(video_data)
            
            # Sort by last modified date (newest first)
            videos.sort(key=lambda x: x['lastModified'] if x['lastModified'] else '', reverse=True)
            
        except Exception as e:
            print(f"Error fetching videos: {e}")
            raise
        
        return videos

    def get_folder_structure(self):
        """Build folder structure from blob names"""
        folders = {}
        video_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.mkv']
        
        try:
            for blob in self.container_client.list_blobs():
                # Only process video files
                if any(blob.name.lower().endswith(ext) for ext in video_extensions):
                    # Split path into parts
                    parts = blob.name.split('/')
                    
                    # Build folder tree
                    if len(parts) > 1:
                        current = folders
                        for i, part in enumerate(parts[:-1]):  # Exclude filename
                            if part not in current:
                                current[part] = {
                                    'name': part,
                                    'path': '/'.join(parts[:i+1]),
                                    'children': {},
                                    'video_count': 0
                                }
                            current = current[part]['children']
                        
                        # Count videos in parent folder
                        parent_path = '/'.join(parts[:-1])
                        self._increment_video_count(folders, parent_path)
            
            # Convert to list format
            return self._folders_to_list(folders)
            
        except Exception as e:
            print(f"Error building folder structure: {e}")
            raise
    
    def _increment_video_count(self, folders, path):
        """Increment video count for a folder path"""
        parts = path.split('/')
        current = folders
        for part in parts:
            if part in current:
                current[part]['video_count'] += 1
                current = current[part]['children']
    
    def get_subtitles(self, video_id):
        """Get available subtitle files for a video
        
        Subtitle naming convention:
        - video.mp4 → video.ja.vtt (Japanese)
        - video.mp4 → video.en.vtt (English)
        - video.mp4 → video.zh.vtt (Chinese)
        """
        subtitles = []
        
        # Language mapping (ISO 639-1 code → display name)
        language_names = {
            'ja': '日本語',
            'en': 'English',
            'zh': '中文',
            'ko': '한국어',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
            'pt': 'Português',
            'ru': 'Русский',
            'ar': 'العربية'
        }
        
        try:
            # Remove file extension from video_id
            video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
            
            # List all blobs with the same base name
            folder_path = video_id.rsplit('/', 1)[0] if '/' in video_id else ''
            prefix = f"{folder_path}/" if folder_path else ""
            
            for blob in self.container_client.list_blobs(name_starts_with=prefix):
                # Check if it's a subtitle file for this video
                if blob.name.lower().endswith('.vtt') and blob.name.startswith(video_base):
                    # Extract language code from filename
                    # Format: video.ja.vtt, video.en.vtt
                    parts = blob.name.rsplit('.', 2)
                    if len(parts) == 3 and parts[1] in language_names:
                        lang_code = parts[1]
                        subtitle_url = f"{config.CONTAINER_URL}/{quote(blob.name)}?{config.SAS_TOKEN}"
                        
                        subtitles.append({
                            'lang': lang_code,
                            'label': language_names[lang_code],
                            'url': subtitle_url,
                            'file': blob.name
                        })
            
            # Sort by language code
            subtitles.sort(key=lambda x: x['lang'])
            
        except Exception as e:
            print(f"Error fetching subtitles for {video_id}: {e}")
        
        return subtitles
    
    def get_chapters(self, video_id, interval_minutes=5):
        """Get chapters/timestamps for a video.
        
        Priority:
        1. Manual chapters file (.chapters.json) - Best quality, user-defined titles
        2. Auto-generated from subtitles - Fallback with transcription text
        
        Manual chapters file format (video.chapters.json):
        {
            "chapters": [
                {"timestamp": "0:00", "title": "イントロダクション"},
                {"timestamp": "5:30", "title": "曲げ剛性の影響（ボックスカルバート）"},
                {"timestamp": "12:15", "title": "演習−曲げ剛性の影響"}
            ]
        }
        
        Args:
            video_id: Video file path (e.g., folder/video.mp4)
            interval_minutes: Minutes between auto-generated markers (default: 5)
        
        Returns:
            List of chapter objects: [{timestamp: seconds, title: text}, ...]
        """
        import json
        import re
        
        chapters = []
        video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
        
        # ============================================
        # PRIORITY 1: Check for manual chapters file
        # ============================================
        chapters_blob_name = f"{video_base}.chapters.json"
        
        try:
            blob_client = self.container_client.get_blob_client(chapters_blob_name)
            chapters_content = blob_client.download_blob().readall().decode('utf-8')
            chapters_data = json.loads(chapters_content)
            
            if 'chapters' in chapters_data and len(chapters_data['chapters']) > 0:
                print(f"📋 Found manual chapters file: {chapters_blob_name}")
                
                for chapter in chapters_data['chapters']:
                    # Parse timestamp (supports "0:00", "5:30", "1:25:00" formats)
                    timestamp_str = chapter.get('timestamp', '0:00')
                    timestamp_seconds = self._parse_timestamp_string(timestamp_str)
                    
                    chapters.append({
                        'timestamp': timestamp_seconds,
                        'title': chapter.get('title', f'Chapter at {timestamp_str}'),
                        'description': chapter.get('description', '')
                    })
                
                # Sort by timestamp
                chapters.sort(key=lambda x: x['timestamp'])
                return chapters
                
        except Exception as e:
            # No manual chapters file, continue to auto-generation
            print(f"ℹ️ No manual chapters file, will auto-generate from subtitles")
        
        # ============================================
        # PRIORITY 2: Auto-generate from subtitles
        # ============================================
        try:
            subtitle_blob_name = f"{video_base}.ja.vtt"  # Try Japanese subtitle first
            
            # Check if subtitle exists
            try:
                blob_client = self.container_client.get_blob_client(subtitle_blob_name)
                subtitle_content = blob_client.download_blob().readall().decode('utf-8')
            except Exception:
                # Try other languages if Japanese not found
                folder_path = video_id.rsplit('/', 1)[0] if '/' in video_id else ''
                prefix = video_base
                
                subtitle_content = None
                for blob in self.container_client.list_blobs(name_starts_with=prefix):
                    if blob.name.lower().endswith('.vtt'):
                        try:
                            blob_client = self.container_client.get_blob_client(blob.name)
                            subtitle_content = blob_client.download_blob().readall().decode('utf-8')
                            break
                        except:
                            continue
                
                if not subtitle_content:
                    return []
            
            # Parse VTT file to extract timestamps and text
            # VTT timestamp pattern: 00:00:00.000 --> 00:00:05.000
            timestamp_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})'
            
            # Split into cues
            lines = subtitle_content.split('\n')
            cues = []
            current_cue = None
            
            for line in lines:
                line = line.strip()
                
                # Check for timestamp line
                match = re.match(timestamp_pattern, line)
                if match:
                    start_time = match.group(1)
                    # Convert HH:MM:SS.mmm to seconds
                    parts = start_time.split(':')
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    timestamp_seconds = hours * 3600 + minutes * 60 + seconds
                    
                    current_cue = {
                        'timestamp': timestamp_seconds,
                        'text': ''
                    }
                elif current_cue and line and not line.startswith('WEBVTT') and not line.isdigit():
                    # This is subtitle text
                    if current_cue['text']:
                        current_cue['text'] += ' '
                    current_cue['text'] += line
                    
                    # Save cue when we've collected text
                    if current_cue['text']:
                        cues.append(current_cue)
                        current_cue = None
            
            if not cues:
                return []
            
            # Generate chapters at regular intervals
            interval_seconds = interval_minutes * 60
            last_timestamp = cues[-1]['timestamp'] if cues else 0
            
            # Always add first chapter at 0:00
            chapter_timestamps = [0]
            
            # Add chapters at intervals
            current_time = interval_seconds
            while current_time < last_timestamp:
                chapter_timestamps.append(current_time)
                current_time += interval_seconds
            
            # Create chapters with text from nearest subtitle
            for chapter_time in chapter_timestamps:
                # Find the subtitle closest to (but after) this timestamp
                nearest_cue = None
                for cue in cues:
                    if cue['timestamp'] >= chapter_time:
                        nearest_cue = cue
                        break
                
                if nearest_cue:
                    # Clean up the text (first 50 chars for title)
                    text = nearest_cue['text'].strip()
                    # Remove common artifacts
                    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                    text = text.replace('\n', ' ').strip()
                    
                    # Create a readable title
                    if len(text) > 60:
                        # Find a natural break point
                        title = text[:60]
                        last_space = title.rfind(' ')
                        if last_space > 30:
                            title = title[:last_space]
                        title += '...'
                    else:
                        title = text
                    
                    chapters.append({
                        'timestamp': chapter_time,
                        'title': title if title else f"チャプター {len(chapters) + 1}"
                    })
            
        except Exception as e:
            print(f"Error generating chapters for {video_id}: {e}")
        
        return chapters
    
    def _parse_timestamp_string(self, timestamp_str):
        """Parse timestamp string to seconds.
        
        Supports formats:
        - "0:00" -> 0 seconds
        - "5:30" -> 330 seconds  
        - "1:25:00" -> 5100 seconds
        """
        parts = timestamp_str.strip().split(':')
        
        if len(parts) == 2:
            # MM:SS format
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # HH:MM:SS format
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    
    def search_subtitles(self, query):
        """Search for videos by subtitle content
        
        Args:
            query: Search string to find in subtitles
            
        Returns:
            List of video IDs that contain the query in their subtitles
        """
        if not query or len(query.strip()) == 0:
            return []
        
        query = query.lower().strip()
        matching_videos = []
        
        try:
            # Get all video files
            videos = self.get_videos()
            print(f"🔍 Searching subtitles for '{query}' across {len(videos)} videos...")
            
            for video in videos:
                video_id = video['id']
                video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
                
                # Check all possible subtitle files (ja, en, etc.)
                subtitle_patterns = [
                    f"{video_base}.ja.vtt",      # Japanese subtitles
                    f"{video_base}.en.vtt",      # English subtitles
                    f"{video_base}.ja-JP.vtt",   # Alternative Japanese format
                    f"{video_base}.en-US.vtt",   # Alternative English format
                    f"{video_base}.vtt"          # Default subtitles
                ]
                
                found_match = False
                for subtitle_blob_name in subtitle_patterns:
                    if found_match:
                        break
                        
                    try:
                        blob_client = self.container_client.get_blob_client(subtitle_blob_name)
                        subtitle_content = blob_client.download_blob().readall().decode('utf-8')
                        
                        # Remove spaces from subtitle content (Japanese transcription often has spaces between characters)
                        subtitle_content_normalized = subtitle_content.replace(' ', '').replace('　', '')  # Remove both space and full-width space
                        query_normalized = query.replace(' ', '').replace('　', '')
                        
                        # Search in subtitle content (case-insensitive, space-insensitive)
                        if query_normalized in subtitle_content_normalized.lower():
                            print(f"✅ Found '{query}' in {subtitle_blob_name}")
                            matching_videos.append({
                                'video_id': video_id,
                                'video_name': video['name'],
                                'uploader': video.get('uploader', '不明')
                            })
                            found_match = True
                        else:
                            print(f"❌ Not found in {subtitle_blob_name} (checked {len(subtitle_content)} chars)")
                    except Exception as e:
                        # Subtitle file doesn't exist, try next pattern
                        print(f"⚠️  No subtitle file: {subtitle_blob_name} ({str(e)[:50]})")
                        continue
            
            print(f"📊 Total matches found: {len(matching_videos)}")
        
        except Exception as e:
            print(f"Error searching subtitles: {e}")
        
        return matching_videos
    
    def _folders_to_list(self, folders_dict):
        """Convert folder dict to list format"""
        result = []
        for key, value in folders_dict.items():
            folder = {
                'name': value['name'],
                'path': value['path'],
                'video_count': value['video_count'],
                'children': self._folders_to_list(value['children'])
            }
            result.append(folder)
        return result


# Initialize services
if config.USE_CLOUD_STORAGE:
    logger.info("STARTUP | mode=cloud | storage=Azure Table Storage + Blob")
    # Use cloud-based trackers
    if config.TABLE_CONNECTION_STRING:
        view_tracker = CloudViewTracker(connection_string=config.TABLE_CONNECTION_STRING)
        engagement_tracker = EngagementTracker(connection_string=config.TABLE_CONNECTION_STRING)
    else:
        view_tracker = CloudViewTracker(
            storage_account=config.STORAGE_ACCOUNT_NAME,
            sas_token=config.TABLE_SAS_TOKEN
        )
        engagement_tracker = EngagementTracker(
            storage_account=config.STORAGE_ACCOUNT_NAME,
            sas_token=config.TABLE_SAS_TOKEN
        )
else:
    logger.info("STARTUP | mode=local | storage=JSON file + local thumbnails")
    # Use local file-based trackers
    view_tracker = ViewTracker()
    # For local development, still use cloud engagement tracker if available
    try:
        if config.TABLE_CONNECTION_STRING:
            engagement_tracker = EngagementTracker(connection_string=config.TABLE_CONNECTION_STRING)
        else:
            engagement_tracker = EngagementTracker(
                storage_account=config.STORAGE_ACCOUNT_NAME,
                sas_token=config.TABLE_SAS_TOKEN
            )
    except:
        logger.warning("STARTUP | engagement_tracker=unavailable | mode=local")
        engagement_tracker = None

video_service = VideoService(view_tracker)


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html', 
                         storage_account=config.STORAGE_ACCOUNT_NAME,
                         container=config.CONTAINER_NAME)


@app.route('/api/videos')
def get_videos():
    """API endpoint to get all videos"""
    try:
        videos = video_service.get_videos()
        return jsonify({
            'success': True,
            'videos': videos,
            'count': len(videos)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/folders')
def get_folders():
    """API endpoint to get folder structure"""
    try:
        folders = video_service.get_folder_structure()
        return jsonify({
            'success': True,
            'folders': folders
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/subtitles/<path:video_id>')
@cache.cached(timeout=86400, query_string=True)  # Cache for 24 hours
def get_subtitles(video_id):
    """API endpoint to get available subtitles for a video"""
    try:
        subtitles = video_service.get_subtitles(video_id)
        response = jsonify({
            'success': True,
            'subtitles': subtitles,
            'count': len(subtitles)
        })
        # HTTP cache header - browser caches for 7 days
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chapters/<path:video_id>')
@cache.cached(timeout=86400, query_string=True)  # Cache for 24 hours
def get_chapters(video_id):
    """API endpoint to get chapters/timestamps for a video.
    Auto-generates chapters from subtitles at regular intervals."""
    try:
        chapters = video_service.get_chapters(video_id)
        response = jsonify({
            'success': True,
            'chapters': chapters,
            'count': len(chapters)
        })
        # HTTP cache header - browser caches for 7 days
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transcript/<path:video_id>')
@cache.cached(timeout=86400, query_string=True)  # Cache for 24 hours
def get_transcript(video_id):
    """API endpoint to get transcript (parsed VTT) for YouTube-style display.
    Returns all subtitle lines with timestamps for scrolling transcript panel."""
    try:
        import re
        from azure.storage.blob import BlobServiceClient
        
        # Get language parameter (default: ja)
        lang = request.args.get('lang', 'ja')
        
        # Get subtitle filename
        video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
        subtitle_blob = f"{video_base}.{lang}.vtt"
        
        # Download VTT file from blob storage
        blob_service_client = BlobServiceClient(
            account_url=f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=config.STORAGE_ACCOUNT_KEY
        )
        blob_client = blob_service_client.get_blob_client(
            container=config.CONTAINER_NAME,
            blob=subtitle_blob
        )
        
        vtt_content = blob_client.download_blob().readall().decode('utf-8')
        
        # Parse VTT format
        lines = []
        current_line = {}
        
        for line in vtt_content.split('\n'):
            line = line.strip()
            
            # Skip WEBVTT header
            if line.startswith('WEBVTT') or line.startswith('NOTE'):
                continue
            
            # Empty line indicates end of current cue
            if not line:
                if current_line.get('text'):
                    # Remove VTT formatting tags
                    text = re.sub(r'<[^>]+>', '', current_line['text'])
                    if text.strip():
                        lines.append({
                            'start': current_line['start'],
                            'end': current_line['end'],
                            'start_display': current_line['start_display'],
                            'text': text.strip()
                        })
                current_line = {}
                continue
            
            # Timestamp line (e.g., "00:00:01.000 --> 00:00:05.000")
            if '-->' in line:
                # Save previous cue if exists
                if current_line.get('text'):
                    text = re.sub(r'<[^>]+>', '', current_line['text'])
                    if text.strip():
                        lines.append({
                            'start': current_line['start'],
                            'end': current_line['end'],
                            'start_display': current_line['start_display'],
                            'text': text.strip()
                        })
                
                times = line.split('-->') 
                start_time = times[0].strip()
                end_time = times[1].strip() if len(times) > 1 else start_time
                
                # Convert to seconds for easier seeking
                def vtt_to_seconds(vtt_time):
                    parts = vtt_time.replace(',', '.').split(':')
                    if len(parts) == 3:  # HH:MM:SS.mmm
                        hours, minutes, seconds = parts
                        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    elif len(parts) == 2:  # MM:SS.mmm
                        minutes, seconds = parts
                        return int(minutes) * 60 + float(seconds)
                    return 0
                
                current_line = {
                    'start': vtt_to_seconds(start_time),
                    'end': vtt_to_seconds(end_time),
                    'start_display': start_time.split('.')[0],  # For display (no milliseconds)
                    'text': ''
                }
            # Text line (skip cue numbers which are just digits)
            elif current_line and not line.isdigit():
                if current_line.get('text'):
                    current_line['text'] += ' '  # Add space between multiple text lines
                current_line['text'] += line
        
        # Don't forget last cue if file doesn't end with empty line
        if current_line.get('text'):
            text = re.sub(r'<[^>]+>', '', current_line['text'])
            if text.strip():
                lines.append({
                    'start': current_line['start'],
                    'end': current_line['end'],
                    'start_display': current_line['start_display'],
                    'text': text.strip()
                })
        
        response = jsonify({
            'success': True,
            'language': lang,
            'lines': lines,
            'count': len(lines)
        })
        # HTTP cache header - browser caches for 1 day
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/video-url/<path:video_id>')
def get_video_url(video_id):
    """Generate TRUE short-lived SAS token for video (2 minutes expiration)
    
    Security improvement: Instead of exposing long-lived SAS tokens,
    generate fresh tokens on-demand with 2-minute expiration.
    This prevents URL sharing and improves content security.
    """
    try:
        from datetime import datetime, timedelta, timezone
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        
        # Get user_id for audit logging
        user_id = request.args.get('user_id', 'unknown')
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Generate TRUE 2-minute SAS token using account key
        sas_token = generate_blob_sas(
            account_name=config.STORAGE_ACCOUNT_NAME,
            container_name=config.CONTAINER_NAME,
            blob_name=video_id,
            account_key=config.STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=2)
        )
        
        # Construct video URL with fresh 2-minute SAS token
        video_url = f"{config.CONTAINER_URL}/{quote(video_id)}?{sas_token}"
        
        # Server-side logging (visible in Azure Container App logs)
        logger.info(f"SAS_TOKEN_GENERATED | user={user_id} | ip={client_ip} | video={video_id[:80]}")
        
        # Audit log: Track who accessed which video
        try:
            engagement_tracker.log_video_access(video_id, user_id, client_ip)
        except Exception as log_error:
            logger.warning(f"AUDIT_LOG_FAILED | error={log_error}")
        
        return jsonify({
            'success': True,
            'url': video_url,
            'expires_in': 120  # 2 minutes in seconds
        })
        
    except Exception as e:
        logger.error(f"SAS_TOKEN_ERROR | video={video_id[:50]} | error={str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/view/<path:video_id>', methods=['POST'])
def increment_view(video_id):
    """API endpoint to increment view count"""
    try:
        video_name = request.json.get('name', 'Unknown') if request.json else 'Unknown'
        duration_watched = request.json.get('duration_watched', 0) if request.json else 0
        video_duration = request.json.get('video_duration', 0) if request.json else 0
        
        # Track to Application Insights + Table Storage
        TelemetryTracker.track_video_view(video_id, duration_watched, video_duration)
        
        # Also track in local view counter
        new_count = view_tracker.increment_view(video_id, video_name)
        return jsonify({
            'success': True,
            'video_id': video_id,
            'views': new_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search/subtitles')
def search_subtitles():
    """API endpoint to search videos by subtitle content"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': True,
                'results': [],
                'count': 0
            })
        
        results = video_service.search_subtitles(query)
        
        # Track search to Application Insights + Table Storage
        TelemetryTracker.track_search(query, len(results))
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/thumbnail/<path:video_id>')
def get_thumbnail(video_id):
    """API endpoint to get or generate video thumbnail from first frame"""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        import io
        import tempfile
        import os
        import requests
        
        print(f"🎬 Generating thumbnail for: {video_id}")
        
        # First, check if pre-generated thumbnail exists in blob storage
        # (for videos with moov atom at end that require full download)
        thumbnail_blob_name = video_id.rsplit('.', 1)[0] + '.thumb.jpg'
        thumbnail_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{config.CONTAINER_NAME}/{thumbnail_blob_name}?{config.SAS_TOKEN}"
        
        try:
            print(f"🔍 Checking for pre-generated thumbnail...")
            thumb_response = requests.head(thumbnail_url, timeout=5)
            if thumb_response.status_code == 200:
                print(f"✅ Found pre-generated thumbnail, redirecting...")
                # Serve the pre-generated thumbnail with caching
                thumb_data = requests.get(thumbnail_url, timeout=30).content
                response = send_file(io.BytesIO(thumb_data), mimetype='image/jpeg')
                response.headers['Cache-Control'] = 'public, max-age=2592000'  # 30 days
                return response
        except Exception as check_error:
            print(f"ℹ️  No pre-generated thumbnail found: {check_error}")
        
        # Get video URL with SAS token
        video_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{config.CONTAINER_NAME}/{video_id}?{config.SAS_TOKEN}"
        
        # Download first 10MB of video (enough to get first frame for most videos)
        headers = {'Range': 'bytes=0-10485760'}  # 10MB
        print(f"📥 Downloading video chunk...")
        response = requests.get(video_url, headers=headers, stream=True, timeout=45)
        
        if response.status_code not in [200, 206]:
            raise Exception(f"Failed to download video chunk: {response.status_code}")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        print(f"💾 Saved temp file: {tmp_path}")
        
        try:
            # Extract first frame with OpenCV
            print(f"🎞️  Extracting first frame with OpenCV...")
            video = cv2.VideoCapture(tmp_path)
            
            # Try to read first frame
            success, frame = video.read()
            video.release()
            
            if not success or frame is None:
                raise Exception("Could not extract frame from video")
            
            print(f"✅ Frame extracted successfully! Shape: {frame.shape}")
            
            # Resize to thumbnail size (320x180)
            height, width = frame.shape[:2]
            aspect = width / height
            
            if aspect > 16/9:
                new_width = 320
                new_height = int(320 / aspect)
            else:
                new_height = 180
                new_width = int(180 * aspect)
            
            frame_resized = cv2.resize(frame, (new_width, new_height))
            
            # Create 320x180 image with black bars if needed
            thumbnail = np.zeros((180, 320, 3), dtype=np.uint8)
            y_offset = (180 - new_height) // 2
            x_offset = (320 - new_width) // 2
            thumbnail[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = frame_resized
            
            # Convert BGR to RGB
            thumbnail_rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(thumbnail_rgb)
            
            print(f"🖼️  Thumbnail created: 320x180")
            
            # Save to bytes
            img_bytes = io.BytesIO()
            pil_image.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)
            
            print(f"✅ Thumbnail generated successfully!")
            
            # Return image with aggressive caching (30 days)
            response = send_file(img_bytes, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'public, max-age=2592000'  # 30 days
            return response
            
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
                print(f"🗑️  Cleaned up temporary file")
            except Exception as cleanup_error:
                print(f"⚠️  Could not delete temp file: {cleanup_error}")
                
    except Exception as e:
        print(f"❌ Error generating thumbnail for {video_id}: {e}")
        print(f"   Falling back to gradient placeholder...")
        
        # Fallback to placeholder gradient
        try:
            from PIL import Image, ImageDraw
            import io
            import hashlib
            
            video_name = video_id.split('/')[-1].replace('.mp4', '').replace('.MP4', '')
            hash_val = int(hashlib.md5(video_id.encode()).hexdigest()[:6], 16)
            base_color = (
                (hash_val >> 16) % 100 + 50,
                (hash_val >> 8) % 100 + 50,
                hash_val % 100 + 50
            )
            
            img = Image.new('RGB', (320, 180), color=base_color)
            draw = ImageDraw.Draw(img)
            
            for y in range(180):
                alpha = int(255 * (y / 180) * 0.3)
                overlay_color = tuple(max(0, c - alpha) for c in base_color)
                draw.line([(0, y), (320, y)], fill=overlay_color)
            
            center_x, center_y = 160, 90
            play_size = 40
            play_icon = [
                (center_x - play_size//2, center_y - play_size),
                (center_x - play_size//2, center_y + play_size),
                (center_x + play_size, center_y)
            ]
            shadow_icon = [(x+2, y+2) for x, y in play_icon]
            draw.polygon(shadow_icon, fill=(0, 0, 0, 128))
            # Draw icon
            draw.polygon(play_icon, fill=(255, 255, 255, 230))
            
            # Add video name at bottom with shadow
            text = video_name[:35] + '...' if len(video_name) > 35 else video_name
            # Text shadow
            draw.text((12, 152), text, fill=(0, 0, 0))
            # Text
            draw.text((10, 150), text, fill=(255, 255, 255))
            
            # Save to bytes
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=90)
            img_io.seek(0)
            
            return send_file(
                img_io,
                mimetype='image/jpeg',
                as_attachment=False,
                download_name=f'{video_name}_thumb.jpg'
            )
        except Exception as fallback_error:
            print(f"Error creating fallback thumbnail: {fallback_error}")
            return jsonify({'error': 'Could not generate thumbnail'}), 500


# ===== ENGAGEMENT ENDPOINTS =====

def get_session_id():
    """Get or create session ID for tracking user actions"""
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(16)
    return session['user_id']


@app.route('/api/engagement/<path:video_id>')
def get_engagement(video_id):
    """Get engagement data (likes, dislikes, comments) for a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        engagement = engagement_tracker.get_engagement(video_id)
        user_id = get_session_id()
        user_action = engagement_tracker.get_user_action(video_id, user_id)
        
        return jsonify({
            'success': True,
            'likes': engagement['likes'],
            'dislikes': engagement['dislikes'],
            'comments_count': engagement['comments'],
            'user_action': user_action
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def check_rate_limit(user_id, video_id, action_type, min_seconds=2):
    """
    Check if user is rate limited for this action.
    Returns True if allowed, False if too soon.
    """
    key = f"{user_id}_{video_id}_{action_type}"
    current_time = time.time()
    last_time = rate_limit_store.get(key, 0)
    
    if current_time - last_time < min_seconds:
        print(f"⚠️ Rate limit: {action_type} rejected (too soon: {current_time - last_time:.2f}s)")
        return False
    
    rate_limit_store[key] = current_time
    return True


@app.route('/api/like/<path:video_id>', methods=['POST'])
def toggle_like(video_id):
    """Toggle like for a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        # Use client-provided user_id (from localStorage) for consistency across Azure instances
        data = request.get_json() or {}
        user_id = data.get('user_id') or get_session_id()
        print(f"🔑 Like request - User ID: {user_id[:20]}...")
        
        # Server-side rate limiting: prevent clicks within 2 seconds
        if not check_rate_limit(user_id, video_id, 'like', min_seconds=2):
            return jsonify({
                'success': False, 
                'error': 'Too many requests. Please wait a moment.'
            }), 429
        
        likes, dislikes, action = engagement_tracker.toggle_like(video_id, user_id)
        
        return jsonify({
            'success': True,
            'likes': likes,
            'dislikes': dislikes,
            'action': action
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dislike/<path:video_id>', methods=['POST'])
def toggle_dislike(video_id):
    """Toggle dislike for a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        # Use client-provided user_id (from localStorage) for consistency across Azure instances
        data = request.get_json() or {}
        user_id = data.get('user_id') or get_session_id()
        print(f"🔑 Dislike request - User ID: {user_id[:20]}...")
        
        # Server-side rate limiting: prevent clicks within 2 seconds
        if not check_rate_limit(user_id, video_id, 'dislike', min_seconds=2):
            return jsonify({
                'success': False,
                'error': 'Too many requests. Please wait a moment.'
            }), 429
        
        likes, dislikes, action = engagement_tracker.toggle_dislike(video_id, user_id)
        
        return jsonify({
            'success': True,
            'likes': likes,
            'dislikes': dislikes,
            'action': action
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/comments/<path:video_id>')
def get_comments(video_id):
    """Get comments for a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        comments = engagement_tracker.get_comments(video_id)
        
        return jsonify({
            'success': True,
            'comments': comments
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/comment/<path:video_id>', methods=['POST'])
def add_comment(video_id):
    """Add a comment to a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        data = request.json
        text = data.get('text', '').strip()
        author = data.get('author_name', 'Anonymous').strip() or 'Anonymous'
        
        if not text:
            return jsonify({'success': False, 'error': 'Comment text is required'}), 400
        
        if len(text) > 1000:
            return jsonify({'success': False, 'error': 'Comment too long (max 1000 characters)'}), 400
        
        comment = engagement_tracker.add_comment(video_id, text, author)
        
        return jsonify({
            'success': True,
            'comment': comment
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/watchposition/<path:video_id>', methods=['GET'])
def get_watch_position(video_id):
    """Get user's saved watch position for resume feature"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        # Use client-provided user_id (from localStorage)
        user_id = request.args.get('user_id') or get_session_id()
        
        position = engagement_tracker.get_watch_position(video_id, user_id)
        
        return jsonify({
            'success': True,
            'position': position
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/watchposition/<path:video_id>', methods=['POST'])
def save_watch_position(video_id):
    """Save user's watch position for resume feature"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        data = request.get_json() or {}
        user_id = data.get('user_id') or get_session_id()
        position = data.get('position', 0)
        duration = data.get('duration', 0)
        
        success = engagement_tracker.save_watch_position(video_id, user_id, position, duration)
        
        return jsonify({
            'success': success
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Download feature temporarily disabled (can be restored by uncommenting)
# @app.route('/api/download/<path:video_id>')
# def download_video(video_id):
#     """Stream video file from blob storage for download (no SAS token exposed)"""
#     try:
#         # Extract filename from video_id
#         filename = video_id.split('/')[-1] if '/' in video_id else video_id
#         
#         # Get blob client for the video
#         blob_client = video_service.container_client.get_blob_client(video_id)
#         
#         # Get blob properties to check if it exists and get size
#         try:
#             blob_props = blob_client.get_blob_properties()
#             file_size = blob_props.size
#         except Exception as e:
#             return jsonify({'success': False, 'error': f'Video not found: {str(e)}'}), 404
#         
#         # Stream the blob content
#         def generate():
#             """Generator function to stream blob data in chunks"""
#             try:
#                 # Download blob in chunks (10 MB at a time)
#                 chunk_size = 10 * 1024 * 1024  # 10 MB
#                 stream = blob_client.download_blob()
#                 
#                 for chunk in stream.chunks():
#                     yield chunk
#                     
#             except Exception as e:
#                 print(f"❌ Error streaming blob: {str(e)}")
#                 raise
#         
#         # Encode filename for Content-Disposition header (RFC 5987)
#         # This handles Japanese characters and other non-ASCII characters
#         from urllib.parse import quote
#         
#         # ASCII fallback filename (for old browsers)
#         ascii_filename = filename.encode('ascii', 'ignore').decode('ascii') or 'video.mp4'
#         
#         # RFC 5987 encoded filename (for modern browsers with UTF-8 support)
#         encoded_filename = quote(filename)
#         
#         # Create Content-Disposition header with both ASCII and UTF-8 versions
#         content_disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
#         
#         # Create streaming response with proper headers
#         response = Response(
#             generate(),
#             mimetype='video/mp4',
#             headers={
#                 'Content-Disposition': content_disposition,
#                 'Content-Length': str(file_size),
#                 'Content-Type': 'video/mp4',
#                 'Cache-Control': 'no-cache',
#                 'X-Content-Type-Options': 'nosniff'
#             }
#         )
#         
#         return response
#         
#     except Exception as e:
#         print(f"❌ Download error: {str(e)}")
#         return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/log', methods=['POST'])
def client_log():
    """API endpoint for frontend to send logs to backend
    
    This allows viewing frontend events in Azure Container logs
    instead of only in browser console.
    """
    try:
        data = request.json or {}
        event = data.get('event', 'UNKNOWN')
        message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        video_id = data.get('video_id', '')
        
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Log to server (visible in Azure Container logs)
        logger.info(f"CLIENT_EVENT | event={event} | user={user_id} | ip={client_ip} | video={video_id[:50] if video_id else 'N/A'} | {message}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"CLIENT_LOG_ERROR | error={str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Pacific Tube'})


@app.route('/api/cache-stats')
def cache_stats():
    """Show cache statistics - useful for verifying caching is working"""
    try:
        # Get cache object statistics
        cache_dict = cache.cache._cache if hasattr(cache.cache, '_cache') else {}
        
        return jsonify({
            'success': True,
            'cache_enabled': True,
            'cache_type': 'SimpleCache (Memory)',
            'cached_items_count': len(cache_dict),
            'cached_keys': list(cache_dict.keys())[:10] if cache_dict else [],  # First 10 keys
            'info': {
                'server_cache': '24 hours (86400 seconds)',
                'browser_cache_chapters': '7 days (604800 seconds)',
                'browser_cache_subtitles': '7 days (604800 seconds)',
                'browser_cache_transcript': '1 day (86400 seconds)',
                'browser_cache_thumbnails': '30 days (2592000 seconds)'
            },
            'savings_estimate': '70-80% bandwidth reduction'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("STARTUP | Pacific Tube Starting...")
    logger.info(f"STARTUP | storage={config.STORAGE_ACCOUNT_NAME}/{config.CONTAINER_NAME}")
    logger.info(f"STARTUP | server=http://localhost:{config.PORT}")
    logger.info(f"STARTUP | sas_token_feature=2min_expiry")
    logger.info("=" * 60)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
