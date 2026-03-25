"""
Generate thumbnails for new videos and upload to blob storage
Handles videos with moov atom at end of file (requires full download)
"""

import os
import sys
import cv2
import tempfile
import requests
from PIL import Image
import numpy as np
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContainerClient
from urllib.parse import quote
import config

load_dotenv()

THUMBNAIL_SIZE = (320, 180)

print("="*70)
print("Generating Thumbnails for New Videos")
print("="*70)
print()

# Initialize blob storage client
container_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/videos?{config.SAS_TOKEN}"
container_client = ContainerClient.from_container_url(container_url)

# List of videos that need thumbnails (moov atom at end)
new_videos = [
    "土木技術基礎講座動画（構造力学）/構造力学（イントロ）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第1回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第2回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第3回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第4回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第5回）.mp4"
]

def check_thumbnail_exists(video_id):
    """Check if thumbnail already exists in blob storage"""
    thumbnail_name = video_id.rsplit('.', 1)[0] + '.thumb.jpg'
    try:
        blob_client = container_client.get_blob_client(thumbnail_name)
        properties = blob_client.get_blob_properties()
        return properties.size > 0
    except:
        return False

def generate_thumbnail(video_id):
    """Download full video, extract frame, generate thumbnail"""
    video_name = video_id.split('/')[-1]
    print(f"   [INFO] Downloading full video (this may take a while)...")
    
    # Download full video
    blob_client = container_client.get_blob_client(video_id)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        download_stream = blob_client.download_blob()
        total_size = download_stream.properties.size
        downloaded = 0
        
        for chunk in download_stream.chunks():
            tmp_file.write(chunk)
            downloaded += len(chunk)
            progress = (downloaded / total_size) * 100
            print(f"\r   [INFO] Downloading: {progress:.1f}% ({downloaded:,} / {total_size:,} bytes)", end='')
        
        tmp_path = tmp_file.name
    
    print()
    print(f"   [INFO] Extracting frame with OpenCV...")
    
    try:
        # Open video with OpenCV
        video = cv2.VideoCapture(tmp_path)
        
        if not video.isOpened():
            raise Exception("Could not open video file")
        
        # Get video properties
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = video.get(cv2.CAP_PROP_FPS)
        
        # Seek to 5 seconds or 5% of video (skip intro)
        if fps > 0 and total_frames > 0:
            target_frame = min(int(fps * 5), int(total_frames * 0.05))
            target_frame = max(target_frame, 30)  # At least 30 frames in
        else:
            target_frame = 30
        
        video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # Read frame
        success, frame = video.read()
        video.release()
        
        if not success or frame is None:
            raise Exception("Could not extract frame from video")
        
        print(f"   [INFO] Frame extracted! Shape: {frame.shape}")
        
        # Resize to thumbnail size
        height, width = frame.shape[:2]
        aspect = width / height
        
        if aspect > 16/9:
            new_width = 320
            new_height = int(320 / aspect)
        else:
            new_height = 180
            new_width = int(180 * aspect)
        
        frame_resized = cv2.resize(frame, (new_width, new_height))
        
        # Create 320x180 thumbnail with black bars if needed
        thumbnail = np.zeros((180, 320, 3), dtype=np.uint8)
        y_offset = (180 - new_height) // 2
        x_offset = (320 - new_width) // 2
        thumbnail[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = frame_resized
        
        # Convert BGR to RGB
        thumbnail_rgb = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(thumbnail_rgb)
        
        # Save to temporary file
        thumb_path = tmp_path.replace('.mp4', '.jpg')
        pil_image.save(thumb_path, 'JPEG', quality=85)
        
        print(f"   [INFO] Thumbnail created: {thumb_path}")
        
        # Upload to blob storage
        thumbnail_blob_name = video_id.rsplit('.', 1)[0] + '.thumb.jpg'
        print(f"   [INFO] Uploading to blob storage...")
        
        thumb_blob_client = container_client.get_blob_client(thumbnail_blob_name)
        with open(thumb_path, 'rb') as thumb_file:
            thumb_blob_client.upload_blob(thumb_file, overwrite=True)
        
        print(f"   [DONE] Uploaded: {thumbnail_blob_name}")
        
        # Cleanup
        os.unlink(tmp_path)
        os.unlink(thumb_path)
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False

print(f"Videos to process: {len(new_videos)}")
print()

success_count = 0
failed_count = 0

for i, video_id in enumerate(new_videos, 1):
    video_name = video_id.split('/')[-1]
    print(f"[{i}/{len(new_videos)}] {video_name}")
    
    # Check if thumbnail already exists
    if check_thumbnail_exists(video_id):
        print(f"   [SKIP] Thumbnail already exists in blob storage")
        success_count += 1
        continue
    
    # Generate thumbnail
    if generate_thumbnail(video_id):
        success_count += 1
    else:
        failed_count += 1
    
    print()

print("="*70)
print(f"Results:")
print(f"   Successful: {success_count}/{len(new_videos)}")
print(f"   Failed: {failed_count}/{len(new_videos)}")
print("="*70)
print()

if success_count > 0:
    print("Thumbnails uploaded to blob storage.")
    print("Update app.py to check for pre-generated thumbnails.")
    print()
