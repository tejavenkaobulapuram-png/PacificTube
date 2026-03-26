"""
Automatic Chapter Generator - Slide Detection & OCR
====================================================

This script automatically detects slide changes in lecture videos and extracts
slide headings to create chapter files.

How it works:
1. Extract frames from video at regular intervals (every 3 seconds)
2. Compare consecutive frames to detect significant changes (slide transitions)
3. When a slide change is detected, use Azure OCR to extract text from the frame
4. Identify the heading text (usually at the top of the slide)
5. Generate a chapters.json file

Requirements:
- opencv-python (cv2)
- azure-cognitiveservices-vision-computervision
- Pillow (PIL)

Usage:
    python generate_chapters_auto.py "video_path_in_blob"
    
Example:
    python generate_chapters_auto.py "土木技術基礎講座動画（構造力学）/構造力学（第1回）.mp4"
"""

import os
import sys
import cv2
import json
import tempfile
import numpy as np
from datetime import timedelta
from PIL import Image
from azure.storage.blob import ContainerClient
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv
import config
import time
import io

load_dotenv()

# Azure Computer Vision for OCR
COMPUTER_VISION_KEY = os.environ.get('AZURE_COMPUTER_VISION_KEY', '')
COMPUTER_VISION_ENDPOINT = os.environ.get('AZURE_COMPUTER_VISION_ENDPOINT', '')

# Frame sampling settings
FRAME_INTERVAL_SECONDS = 3  # Check every 3 seconds
SLIDE_CHANGE_THRESHOLD = 0.15  # 15% difference = slide change
MIN_CHAPTER_GAP_SECONDS = 30  # Minimum 30 seconds between chapters

print("="*70)
print("Automatic Chapter Generator - Slide Detection & OCR")
print("="*70)
print()

# Initialize blob storage
container_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/videos?{config.SAS_TOKEN}"
container_client = ContainerClient.from_container_url(container_url)


def download_video(video_id, output_path):
    """Download video from blob storage"""
    print(f"📥 Downloading video: {video_id}")
    print(f"   This may take a while for large videos...")
    
    blob_client = container_client.get_blob_client(video_id)
    
    with open(output_path, 'wb') as f:
        download_stream = blob_client.download_blob()
        total_size = download_stream.properties.size
        downloaded = 0
        
        for chunk in download_stream.chunks():
            f.write(chunk)
            downloaded += len(chunk)
            progress = (downloaded / total_size) * 100
            print(f"\r   Progress: {progress:.1f}% ({downloaded:,} / {total_size:,} bytes)", end='')
    
    print()
    print(f"   ✅ Download complete!")
    return output_path


def extract_frames(video_path, interval_seconds=FRAME_INTERVAL_SECONDS):
    """Extract frames at regular intervals"""
    print(f"🎬 Extracting frames every {interval_seconds} seconds...")
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise Exception("Could not open video file")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    frame_interval = int(fps * interval_seconds)
    
    print(f"   Video: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"   FPS: {fps:.1f}")
    print(f"   Sampling every {frame_interval} frames")
    
    frames = []
    frame_number = 0
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            break
        
        timestamp = frame_number / fps
        frames.append({
            'frame': frame,
            'timestamp': timestamp,
            'frame_number': frame_number
        })
        
        frame_number += frame_interval
        
        # Progress
        progress = (frame_number / total_frames) * 100
        print(f"\r   Extracting: {progress:.1f}%", end='')
    
    cap.release()
    print()
    print(f"   ✅ Extracted {len(frames)} frames")
    
    return frames, duration


def calculate_frame_difference(frame1, frame2):
    """Calculate the difference between two frames (0-1 scale)"""
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Resize for faster comparison
    gray1 = cv2.resize(gray1, (320, 180))
    gray2 = cv2.resize(gray2, (320, 180))
    
    # Calculate absolute difference
    diff = cv2.absdiff(gray1, gray2)
    
    # Calculate percentage of changed pixels
    changed_pixels = np.sum(diff > 30) / diff.size
    
    return changed_pixels


def detect_slide_changes(frames, threshold=SLIDE_CHANGE_THRESHOLD, min_gap=MIN_CHAPTER_GAP_SECONDS):
    """Detect frames where slides change"""
    print(f"🔍 Detecting slide changes (threshold: {threshold*100:.0f}%)...")
    
    slide_changes = []
    
    # Always add first frame as first chapter
    if frames:
        slide_changes.append({
            'frame': frames[0]['frame'],
            'timestamp': 0,
            'frame_number': 0
        })
    
    last_change_timestamp = 0
    
    for i in range(1, len(frames)):
        prev_frame = frames[i-1]['frame']
        curr_frame = frames[i]['frame']
        timestamp = frames[i]['timestamp']
        
        # Check minimum gap
        if timestamp - last_change_timestamp < min_gap:
            continue
        
        # Calculate difference
        diff = calculate_frame_difference(prev_frame, curr_frame)
        
        if diff > threshold:
            slide_changes.append({
                'frame': curr_frame,
                'timestamp': timestamp,
                'frame_number': frames[i]['frame_number'],
                'difference': diff
            })
            last_change_timestamp = timestamp
            print(f"   📋 Slide change detected at {format_timestamp(timestamp)} (diff: {diff*100:.1f}%)")
    
    print(f"   ✅ Found {len(slide_changes)} slide changes")
    return slide_changes


def format_timestamp(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def extract_text_from_frame_azure(frame, cv_client):
    """Extract text from frame using Azure Computer Vision OCR"""
    # Convert OpenCV frame to bytes
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    image_bytes = io.BytesIO(buffer.tobytes())
    
    # Call Azure Computer Vision
    read_response = cv_client.read_in_stream(image_bytes, language='ja', raw=True)
    
    # Get operation ID
    operation_location = read_response.headers["Operation-Location"]
    operation_id = operation_location.split("/")[-1]
    
    # Wait for result
    while True:
        result = cv_client.get_read_result(operation_id)
        if result.status not in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
            break
        time.sleep(0.5)
    
    # Extract text
    text_lines = []
    if result.status == OperationStatusCodes.succeeded:
        for page in result.analyze_result.read_results:
            for line in page.lines:
                text_lines.append({
                    'text': line.text,
                    'bbox': line.bounding_box,
                    'y': min(line.bounding_box[1], line.bounding_box[3], line.bounding_box[5], line.bounding_box[7])
                })
    
    return text_lines


def extract_text_from_frame_simple(frame):
    """Simple text extraction without Azure (uses edge detection for titles)"""
    # This is a fallback - returns a generic title based on timestamp
    # For proper OCR, Azure Computer Vision or Tesseract is needed
    return []


def identify_heading(text_lines):
    """Identify the heading from extracted text lines
    
    Slide titles are typically:
    - SHORT (5-30 characters)
    - At the TOP of the slide
    - Larger font size (taller bounding box)
    - Not full sentences with punctuation
    """
    if not text_lines:
        return None
    
    # Sort by Y position (top of frame first)
    sorted_lines = sorted(text_lines, key=lambda x: x['y'])
    
    # Common watermarks/logos to skip
    watermarks = ['pacific', 'prod', '©', 'copyright', 'http', 'www', '@', 
                  'pacificworks', 'tk.pacific', 'consultants']
    
    candidates = []
    
    for line in sorted_lines[:10]:  # Check top 10 text lines
        text = line['text'].strip()
        text_lower = text.lower()
        
        # Skip very short text (single characters, numbers)
        if len(text) < 3:
            continue
        
        # Skip watermarks
        if any(wm in text_lower for wm in watermarks):
            continue
        
        # Skip dates (2024, 2024/03/26, etc)
        if text.replace('/', '').replace('-', '').replace('.', '').isdigit():
            continue
        
        # Calculate bounding box height (taller = larger font = likely heading)
        bbox = line['bbox']
        box_height = abs(bbox[5] - bbox[1])  # Y difference
        
        # Prefer titles that are:
        # 1. Short (5-40 chars) - headings are concise
        # 2. At top of slide (low Y value)
        # 3. Not ending with punctuation like 。(full sentences are body text)
        
        is_short = 5 <= len(text) <= 40
        is_body_text = text.endswith('。') or text.endswith('、') or len(text) > 50
        
        if is_short and not is_body_text:
            # Score: prefer short text at top with large font
            score = (1000 - line['y']) + (box_height * 10) - (len(text) * 2)
            candidates.append((text, score))
    
    if candidates:
        # Return highest scoring candidate (top, large font, short)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return None


def generate_chapters(video_id, use_azure_ocr=True):
    """Main function to generate chapters for a video"""
    
    # Temporary file for video
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, "video.mp4")
        
        # Step 1: Download video
        download_video(video_id, video_path)
        print()
        
        # Step 2: Extract frames
        frames, duration = extract_frames(video_path)
        print()
        
        # Step 3: Detect slide changes
        slide_changes = detect_slide_changes(frames)
        print()
        
        # Step 4: Extract text from slide changes
        print("📝 Extracting text from slides...")
        
        # Initialize Azure Computer Vision if available
        cv_client = None
        if use_azure_ocr and COMPUTER_VISION_KEY and COMPUTER_VISION_ENDPOINT:
            try:
                cv_client = ComputerVisionClient(
                    COMPUTER_VISION_ENDPOINT,
                    CognitiveServicesCredentials(COMPUTER_VISION_KEY)
                )
                print("   Using Azure Computer Vision OCR")
                print("   ⚠️ Free tier limit: 20 calls/minute - adding delays...")
            except Exception as e:
                print(f"   ⚠️ Azure OCR not available: {e}")
                cv_client = None
        
        chapters = []
        
        for i, slide in enumerate(slide_changes):
            timestamp = slide['timestamp']
            frame = slide['frame']
            
            print(f"   [{i+1}/{len(slide_changes)}] Processing slide at {format_timestamp(timestamp)}...")
            
            # Try to extract heading text
            heading = None
            
            if cv_client:
                try:
                    # Add delay to avoid rate limit (Free tier: 20 calls/minute)
                    # Wait 3.5 seconds between calls (17 calls/minute max)
                    if i > 0:
                        time.sleep(3.5)
                    
                    text_lines = extract_text_from_frame_azure(frame, cv_client)
                    heading = identify_heading(text_lines)
                except Exception as e:
                    print(f"      ⚠️ OCR failed: {e}")
                    # If rate limit hit, wait 60 seconds and try again
                    if "Too Many Requests" in str(e):
                        print(f"      ⏳ Rate limit hit, waiting 60 seconds...")
                        time.sleep(60)
                        try:
                            text_lines = extract_text_from_frame_azure(frame, cv_client)
                            heading = identify_heading(text_lines)
                        except:
                            pass  # Give up on this one
            
            # Fallback title if no heading found
            if not heading:
                heading = f"チャプター {i+1}"
            
            chapters.append({
                'timestamp': format_timestamp(timestamp),
                'title': heading
            })
            
            print(f"      → {heading}")
        
        print()
        print(f"✅ Generated {len(chapters)} chapters")
        
        return chapters, duration


def save_chapters(video_id, chapters, output_dir='chapters'):
    """Save chapters to JSON file"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename from video
    video_name = video_id.split('/')[-1].rsplit('.', 1)[0]
    output_file = os.path.join(output_dir, f"{video_name}.chapters.json")
    
    data = {
        'video': video_id,
        'chapters': chapters
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved to: {output_file}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_chapters_auto.py <video_path>")
        print()
        print("Example:")
        print('  python generate_chapters_auto.py "土木技術基礎講座動画（構造力学）/構造力学（第1回）.mp4"')
        print()
        
        # List available videos
        print("Available videos:")
        for blob in container_client.list_blobs():
            if blob.name.endswith('.mp4'):
                size_mb = blob.size / (1024 * 1024)
                print(f"  - {blob.name} ({size_mb:.1f} MB)")
        return
    
    video_id = sys.argv[1]
    
    print(f"Video: {video_id}")
    print()
    
    # Check if Azure Computer Vision is configured
    if not COMPUTER_VISION_KEY or not COMPUTER_VISION_ENDPOINT:
        print("⚠️  Azure Computer Vision not configured!")
        print("   For best results, set these environment variables:")
        print("   - AZURE_COMPUTER_VISION_KEY")
        print("   - AZURE_COMPUTER_VISION_ENDPOINT")
        print()
        print("   Without OCR, chapters will have generic titles.")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Generate chapters
    chapters, duration = generate_chapters(video_id)
    
    if chapters:
        # Save to file
        output_file = save_chapters(video_id, chapters)
        
        print()
        print("="*70)
        print("Generated Chapters:")
        print("="*70)
        for chapter in chapters:
            print(f"  {chapter['timestamp']} - {chapter['title']}")
        
        print()
        print("Next steps:")
        print(f"  1. Review and edit: {output_file}")
        print("  2. Upload to blob: python upload_chapters.py")
    else:
        print("❌ No chapters generated")


if __name__ == '__main__':
    main()
