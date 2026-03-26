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
SLIDE_CHANGE_THRESHOLD = 0.25  # 25% difference = slide change (higher for Teams meetings)
MIN_CHAPTER_GAP_SECONDS = 120  # Minimum 2 minutes between chapters (for meetings)

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


def extract_frames_and_detect_changes(video_path, interval_seconds=FRAME_INTERVAL_SECONDS, 
                                      threshold=SLIDE_CHANGE_THRESHOLD, min_gap=MIN_CHAPTER_GAP_SECONDS):
    """
    Memory-efficient: Stream frames and detect slide changes on-the-fly
    Only keeps frames where slides actually change (not all frames)
    """
    print(f"🎬 Analyzing video for slide changes (every {interval_seconds}s)...")
    
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
    print(f"   Threshold: {threshold*100:.0f}% change = slide change")
    
    slide_changes = []
    prev_frame_gray = None
    last_change_timestamp = 0
    frame_number = 0
    checked_frames = 0
    
    # Always add first frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, first_frame = cap.read()
    if ret:
        slide_changes.append({
            'frame': first_frame.copy(),
            'timestamp': 0,
            'frame_number': 0
        })
        prev_frame_gray = cv2.cvtColor(cv2.resize(first_frame, (320, 180)), cv2.COLOR_BGR2GRAY)
    
    # Stream through frames  
    frame_number = frame_interval
    while frame_number < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            break
        
        checked_frames += 1
        timestamp = frame_number / fps
        
        # Check minimum gap
        if timestamp - last_change_timestamp >= min_gap:
            # Calculate difference with previous frame
            curr_frame_gray = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(prev_frame_gray, curr_frame_gray)
            changed_pixels = np.sum(diff > 30) / diff.size
            
            # Slide change detected?
            if changed_pixels >= threshold:
                print(f"\r   📋 Slide change at {format_time(timestamp)} (diff: {changed_pixels*100:.1f}%)")
                slide_changes.append({
                    'frame': frame.copy(),
                    'timestamp': timestamp,
                    'frame_number': frame_number
                })
                last_change_timestamp = timestamp
                prev_frame_gray = curr_frame_gray
            else:
                # Update prev_frame for next comparison
                prev_frame_gray = curr_frame_gray
        
        frame_number += frame_interval
        
        # Progress
        progress = min(100.0, (frame_number / total_frames) * 100)
        print(f"\r   Progress: {progress:.1f}% ({checked_frames} frames checked, {len(slide_changes)} changes found)", end='')
    
    cap.release()
    print()
    print(f"   ✅ Found {len(slide_changes)} slide changes")
    
    return slide_changes, duration


def format_time(seconds):
    """Format seconds as MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"
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
    
    while frame_number < total_frames:  # FIX: Add proper bounds check
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
        progress = min(100.0, (frame_number / total_frames) * 100)  # FIX: Cap at 100%
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
    
    For Teams meetings with screen shares:
    - PowerPoint slides are displayed in CENTER-LEFT of screen
    - Teams UI (search bar, buttons) is on RIGHT side and TOP
    - Filter out Teams UI patterns completely
    - Look for meaningful Japanese slide titles
    """
    if not text_lines:
        return None
    
    # Teams UI patterns to ALWAYS skip (these are NOT slide content)
    teams_ui_patterns = [
        'テキストまたはツールを検索',  # Teams search bar
        'すべてのツール', 'ログイン', 'login', 
        'メニュー', 'menu', 'その他', 'チャット', 'chat',
        '参加者', 'participants', '共有', 'share',
        '作成', '編集', '変換', '電子サイン',  # Adobe/PDF tools
        'pacific', 'prod', '©', 'copyright', 'http', 'www', '@',
        'pacificworks', 'tk.pacific', 'consultants',
        '録音', 'recording', 'cc', 'キャプション',
        '退出', 'leave', '挙手', 'raise hand',
    ]
    
    candidates = []
    
    for line in text_lines:
        text = line['text'].strip()
        text_lower = text.lower()
        
        # Skip very short text (single chars, numbers, UI icons)
        if len(text) < 6:
            continue
        
        # Skip ALL Teams UI patterns
        if any(ui in text for ui in teams_ui_patterns) or any(ui in text_lower for ui in teams_ui_patterns):
            continue
        
        # Skip text with Q, icons, or random symbols (Teams search bar has "Q")
        if 'Q' in text or '|' in text or '号' in text or '骨' in text:
            continue
        
        # Skip names (presenter names in video call - usually short with spaces)
        words = text.split()
        if len(words) <= 3 and all(len(w) <= 5 for w in words):
            # Likely a name like "澁谷 宏樹" - skip unless it's clearly a title
            if not any(keyword in text for keyword in ['の', 'について', '紹介', '説明', '概要', '取り組み']):
                continue
        
        # Skip dates and numbers
        clean_text = text.replace('/', '').replace('-', '').replace('.', '').replace(' ', '').replace(':', '')
        if clean_text.isdigit():
            continue
        
        # Calculate position - slides are in LEFT-CENTER of Teams window
        bbox = line['bbox']
        x_pos = min(bbox[0], bbox[2], bbox[4], bbox[6])  # Leftmost X
        y_pos = line['y']
        box_height = abs(bbox[5] - bbox[1])
        box_width = abs(bbox[2] - bbox[0])
        
        # In Teams, slide content is typically:
        # - X position: 50-800 (left side of screen, not right where UI is)
        # - Y position: 150-550 (middle, not top toolbar or bottom)
        is_slide_area = x_pos < 800 and 100 < y_pos < 600
        
        # Count Japanese characters (slide titles have meaningful Japanese)
        japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309F' or  # Hiragana
                                                 '\u30A0' <= c <= '\u30FF' or  # Katakana
                                                 '\u4E00' <= c <= '\u9FFF')    # Kanji
        japanese_ratio = japanese_chars / len(text) if text else 0
        
        # Good slide titles: 8-60 chars, mostly Japanese, in slide area
        is_good_length = 8 <= len(text) <= 60
        has_japanese = japanese_ratio > 0.4
        
        # Not body text (full sentences)
        is_body_text = text.endswith('。') or text.endswith('、') or len(text) > 60
        
        if is_good_length and has_japanese and not is_body_text:
            # Score: prefer slide area, large font, good Japanese content
            area_score = 200 if is_slide_area else 0
            size_score = box_height * 30 + box_width
            japanese_score = japanese_ratio * 100
            
            # Bonus for title-like keywords
            title_keywords = ['の取り組み', '紹介', '概要', '説明', 'について', '活用', 
                            '構築', '開発', '設計', '結果', '報告', '提案']
            keyword_bonus = 100 if any(kw in text for kw in title_keywords) else 0
            
            score = area_score + size_score + japanese_score + keyword_bonus
            candidates.append((text, score, x_pos, y_pos))
    
    if candidates:
        # Return highest scoring candidate
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
        
        # Step 2: Extract frames AND detect slide changes (memory-efficient streaming)
        slide_changes, duration = extract_frames_and_detect_changes(video_path)
        print()
        
        # Step 3: Extract text from slide changes
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
        rate_limit_cooldown = 0  # Track when we can make next call
        
        for i, slide in enumerate(slide_changes):
            timestamp = slide['timestamp']
            frame = slide['frame']
            
            print(f"   [{i+1}/{len(slide_changes)}] Processing slide at {format_timestamp(timestamp)}...")
            
            # Try to extract heading text
            heading = None
            
            if cv_client:
                # Handle rate limiting proactively
                if rate_limit_cooldown > 0:
                    wait_time = rate_limit_cooldown
                    print(f"      ⏳ Rate limit cooldown: waiting {wait_time}s...")
                    time.sleep(wait_time)
                    rate_limit_cooldown = 0
                
                for attempt in range(3):  # Retry up to 3 times
                    try:
                        # Add delay to avoid rate limit (Free tier: 20 calls/minute)
                        if i > 0 and attempt == 0:
                            time.sleep(3.5)
                        
                        text_lines = extract_text_from_frame_azure(frame, cv_client)
                        heading = identify_heading(text_lines)
                        break  # Success - exit retry loop
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "Too Many Requests" in error_msg or "429" in error_msg:
                            wait_time = 65 if attempt == 0 else 120
                            print(f"      ⚠️ Rate limit hit (attempt {attempt+1}/3), waiting {wait_time}s...")
                            time.sleep(wait_time)
                            rate_limit_cooldown = 5  # Add small cooldown after rate limit
                        else:
                            print(f"      ⚠️ OCR error: {e}")
                            break  # Non-rate-limit error, don't retry
            
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
