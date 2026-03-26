"""
Upload Chapters Files to Azure Blob Storage
============================================

This script uploads .chapters.json files for videos to Azure Blob Storage.

Chapter File Format:
{
    "chapters": [
        {"timestamp": "0:00", "title": "イントロダクション"},
        {"timestamp": "5:30", "title": "曲げ剛性の影響"},
        {"timestamp": "15:00", "title": "演習問題"},
        ...
    ]
}

Timestamp formats supported:
- "0:00" (MM:SS)
- "5:30" (MM:SS) 
- "1:25:00" (HH:MM:SS)

Usage:
    python upload_chapters.py                    # Upload all chapters in ./chapters/
    python upload_chapters.py file.chapters.json # Upload specific file
"""

import os
import sys
import json
from azure.storage.blob import ContainerClient
from dotenv import load_dotenv
import config

load_dotenv()

print("="*70)
print("Chapter File Uploader")
print("="*70)
print()

# Initialize blob storage
container_url = f"https://{config.STORAGE_ACCOUNT_NAME}.blob.core.windows.net/videos?{config.SAS_TOKEN}"
container_client = ContainerClient.from_container_url(container_url)

def validate_chapters_file(file_path):
    """Validate chapters JSON file format"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'chapters' not in data:
            return False, "Missing 'chapters' key"
        
        if not isinstance(data['chapters'], list):
            return False, "'chapters' must be a list"
        
        if len(data['chapters']) == 0:
            return False, "'chapters' list is empty"
        
        for i, chapter in enumerate(data['chapters']):
            if 'timestamp' not in chapter:
                return False, f"Chapter {i+1} missing 'timestamp'"
            if 'title' not in chapter:
                return False, f"Chapter {i+1} missing 'title'"
        
        return True, None
        
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, str(e)


def upload_chapters_file(local_path, video_id=None):
    """Upload a chapters file to blob storage"""
    
    # Read the file
    with open(local_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Determine video_id from file or 'video' key in JSON
    if video_id is None:
        if 'video' in data:
            video_id = data['video']
        else:
            # Use filename
            filename = os.path.basename(local_path)
            # Remove .chapters.json extension
            video_name = filename.replace('.chapters.json', '')
            # Assume it's in root if no path specified
            video_id = f"{video_name}.mp4"
    
    # Generate blob name (video path without .mp4 + .chapters.json)
    video_base = video_id.rsplit('.', 1)[0] if '.' in video_id else video_id
    blob_name = f"{video_base}.chapters.json"
    
    print(f"   Video: {video_id}")
    print(f"   Blob: {blob_name}")
    print(f"   Chapters: {len(data['chapters'])}")
    
    # Upload to blob
    blob_client = container_client.get_blob_client(blob_name)
    
    # Only include the chapters array (not the video metadata)
    upload_data = json.dumps({"chapters": data['chapters']}, ensure_ascii=False, indent=2)
    
    blob_client.upload_blob(upload_data.encode('utf-8'), overwrite=True)
    
    print(f"   ✅ Uploaded successfully!")
    return True


def list_existing_chapters():
    """List all chapters files in blob storage"""
    print("Existing chapters files in blob storage:")
    count = 0
    for blob in container_client.list_blobs():
        if blob.name.endswith('.chapters.json'):
            print(f"   📋 {blob.name}")
            count += 1
    
    if count == 0:
        print("   (none found)")
    print()
    return count


def main():
    # If specific file provided as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"Uploading: {file_path}")
        
        # Validate
        valid, error = validate_chapters_file(file_path)
        if not valid:
            print(f"❌ Invalid file: {error}")
            return
        
        upload_chapters_file(file_path)
        return
    
    # Otherwise, upload all files from ./chapters/ directory
    chapters_dir = os.path.join(os.path.dirname(__file__), 'chapters')
    
    if not os.path.exists(chapters_dir):
        print(f"Creating chapters directory: {chapters_dir}")
        os.makedirs(chapters_dir)
        print()
        print("Please create .chapters.json files in this directory.")
        print()
        print("Example file format:")
        print('''
{
    "video": "土木技術基礎講座動画（構造力学）/構造力学（第1回）.mp4",
    "chapters": [
        {"timestamp": "0:00", "title": "イントロダクション"},
        {"timestamp": "5:30", "title": "曲げ剛性の影響"},
        {"timestamp": "15:00", "title": "演習問題"}
    ]
}
''')
        return
    
    # List existing chapters in blob
    list_existing_chapters()
    
    # Find all chapters files
    chapters_files = []
    for filename in os.listdir(chapters_dir):
        if filename.endswith('.chapters.json'):
            chapters_files.append(os.path.join(chapters_dir, filename))
    
    if not chapters_files:
        print(f"No .chapters.json files found in {chapters_dir}")
        return
    
    print(f"Found {len(chapters_files)} chapters file(s) to upload:")
    print()
    
    success = 0
    failed = 0
    
    for file_path in chapters_files:
        filename = os.path.basename(file_path)
        print(f"[{success + failed + 1}/{len(chapters_files)}] {filename}")
        
        # Validate
        valid, error = validate_chapters_file(file_path)
        if not valid:
            print(f"   ❌ Invalid: {error}")
            failed += 1
            continue
        
        try:
            upload_chapters_file(file_path)
            success += 1
        except Exception as e:
            print(f"   ❌ Upload failed: {e}")
            failed += 1
        
        print()
    
    print("="*70)
    print(f"Summary: {success} uploaded, {failed} failed")
    print("="*70)


if __name__ == '__main__':
    main()
