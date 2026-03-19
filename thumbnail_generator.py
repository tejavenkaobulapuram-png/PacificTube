"""
Thumbnail generation service for Pacific Tube
Extracts video frames and generates thumbnail images
"""

import cv2
import os
import io
import tempfile
import requests
from PIL import Image
from urllib.parse import quote

THUMBNAIL_DIR = 'thumbnails'
THUMBNAIL_SIZE = (320, 180)  # 16:9 ratio


class ThumbnailGenerator:
    """Generate and cache video thumbnails"""
    
    def __init__(self):
        # Create thumbnails directory if it doesn't exist
        if not os.path.exists(THUMBNAIL_DIR):
            os.makedirs(THUMBNAIL_DIR)
    
    def get_thumbnail_path(self, video_id):
        """Get cached thumbnail path for video"""
        # Create safe filename from video_id
        safe_name = video_id.replace('/', '_').replace('\\', '_')
        return os.path.join(THUMBNAIL_DIR, f"{safe_name}.jpg")
    
    def thumbnail_exists(self, video_id):
        """Check if thumbnail already exists"""
        return os.path.exists(self.get_thumbnail_path(video_id))
    
    def generate_from_url(self, video_url, video_id):
        """Generate thumbnail from video URL"""
        thumbnail_path = self.get_thumbnail_path(video_id)
        
        # Return cached thumbnail if exists
        if self.thumbnail_exists(video_id):
            return thumbnail_path
        
        temp_video = None
        try:
            # Download video to temporary file
            print(f"Downloading video for thumbnail: {video_id}")
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Create temporary file for video
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_video = temp_file.name
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
            
            # Extract frame using OpenCV
            print(f"Extracting frame from: {video_id}")
            cap = cv2.VideoCapture(temp_video)
            
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Seek to 2 seconds or 10% of video
            if fps > 0:
                frame_pos = min(int(fps * 2), int(total_frames * 0.1))
            else:
                frame_pos = min(60, int(total_frames * 0.1))
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            
            # Read frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                raise Exception("Could not read frame from video")
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            image = Image.fromarray(frame_rgb)
            
            # Resize to thumbnail size maintaining aspect ratio
            image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Create final thumbnail with black background
            thumbnail = Image.new('RGB', THUMBNAIL_SIZE, (0, 0, 0))
            
            # Center the image
            offset = ((THUMBNAIL_SIZE[0] - image.width) // 2,
                     (THUMBNAIL_SIZE[1] - image.height) // 2)
            thumbnail.paste(image, offset)
            
            # Save thumbnail
            thumbnail.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            print(f"Thumbnail saved: {thumbnail_path}")
            
            return thumbnail_path
            
        except Exception as e:
            print(f"Error generating thumbnail for {video_id}: {e}")
            # Return None if thumbnail generation fails
            return None
            
        finally:
            # Clean up temporary video file
            if temp_video and os.path.exists(temp_video):
                try:
                    os.remove(temp_video)
                except Exception as e:
                    print(f"Could not delete temp file: {e}")
    
    def get_thumbnail_bytes(self, video_id):
        """Get thumbnail as bytes for serving"""
        thumbnail_path = self.get_thumbnail_path(video_id)
        
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as f:
                return f.read()
        
        return None
