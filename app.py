"""
Pacific Tube - Flask Application
YouTube-style video gallery for Azure Blob Storage
"""

# Load environment variables FIRST (before other imports)
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request, send_file, session, Response
from azure.storage.blob import BlobServiceClient, ContainerClient
import config
from datetime import datetime
from urllib.parse import quote
from view_tracker import ViewTracker
from cloud_view_tracker import CloudViewTracker
from engagement_tracker import EngagementTracker
from thumbnail_generator import ThumbnailGenerator
import os
import io
import requests
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))


class VideoService:
    """Service to interact with Azure Blob Storage"""
    
    def __init__(self, view_tracker):
        # Create blob service client with SAS token
        sas_url = f"{config.BLOB_SERVICE_URL}?{config.SAS_TOKEN}"
        self.blob_service_client = BlobServiceClient(account_url=sas_url)
        self.container_client = self.blob_service_client.get_container_client(config.CONTAINER_NAME)
        self.view_tracker = view_tracker
    
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
                    
                    # Construct video URL with SAS token
                    video_url = f"{config.CONTAINER_URL}/{quote(blob.name)}?{config.SAS_TOKEN}"
                    
                    video_data = {
                        'id': blob.name,
                        'name': display_name,
                        'url': video_url,
                        'size': blob.size,
                        'lastModified': blob.last_modified.isoformat() if blob.last_modified else None,
                        'contentType': blob.content_settings.content_type if blob.content_settings else 'video/mp4',
                        'folder': blob.name.rsplit('/', 1)[0] if '/' in blob.name else '',
                        'views': self.view_tracker.get_view_count(blob.name)
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
    print("🌐 Using Cloud Storage (Azure Table Storage + Blob)")
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
    print("💾 Using Local Storage (JSON file + local thumbnails)")
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
        print("⚠️  Engagement tracker not available in local mode")
        engagement_tracker = None

thumbnail_generator = ThumbnailGenerator()
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


@app.route('/api/view/<path:video_id>', methods=['POST'])
def increment_view(video_id):
    """API endpoint to increment view count"""
    try:
        video_name = request.json.get('name', 'Unknown') if request.json else 'Unknown'
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
        
        # Always generate fresh thumbnail (caching will be added later)
        print(f"🎬 Generating thumbnail for: {video_id}")
        
        # Get video URL with SAS token
        video_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{config.CONTAINER_NAME}/{video_id}?{config.SAS_TOKEN}"
        
        # Download first 10MB of video (enough to get first frame)
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
            
            # Return image
            return send_file(img_bytes, mimetype='image/jpeg')
            
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


@app.route('/api/like/<path:video_id>', methods=['POST'])
def toggle_like(video_id):
    """Toggle like for a video"""
    try:
        if engagement_tracker is None:
            return jsonify({'success': False, 'error': 'Engagement tracking not available'}), 503
        
        user_id = get_session_id()
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
        
        user_id = get_session_id()
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


@app.route('/api/download/<path:video_id>')
def download_video(video_id):
    """Get download URL for a video file with proper download disposition"""
    try:
        # Extract filename from video_id
        filename = video_id.split('/')[-1] if '/' in video_id else video_id
        
        # Construct Azure Blob Storage URL with SAS token
        # Add response-content-disposition parameter to force download
        base_url = f"{config.CONTAINER_URL}/{quote(video_id)}"
        download_disposition = f"attachment; filename=\"{filename}\""
        
        # Append the response-content-disposition parameter to the URL
        # This tells Azure Blob Storage to send the Content-Disposition header
        download_url = f"{base_url}?{config.SAS_TOKEN}&response-content-disposition={quote(download_disposition)}"
        
        # Return the URL as JSON
        return jsonify({
            'success': True,
            'download_url': download_url,
            'filename': filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Pacific Tube'})


if __name__ == '__main__':
    print("=" * 60)
    print("🎬 Pacific Tube - Starting...")
    print(f"📦 Storage: {config.STORAGE_ACCOUNT_NAME}/{config.CONTAINER_NAME}")
    print(f"🌐 Server: http://localhost:{config.PORT}")
    print("=" * 60)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
