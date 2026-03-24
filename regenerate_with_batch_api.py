"""
Regenerate Failed/Partial Subtitles Using Batch Transcription API
Only processes videos that don't have complete subtitles
"""

from generate_subtitles_batch import BatchSubtitleGenerator
import os
from dotenv import load_dotenv

load_dotenv()

print("="*70)
print("PacificTube - Batch Subtitle Regeneration")
print("Using Azure Batch Transcription API (no 20-30 min limit!)")
print("="*70)
print()

# Initialize generator
generator = BatchSubtitleGenerator(
    speech_key=os.environ.get('AZURE_SPEECH_KEY'),
    speech_region=os.environ.get('AZURE_SPEECH_REGION', 'japaneast'),
    storage_account=os.environ.get('AZURE_STORAGE_ACCOUNT_NAME'),
    blob_sas_token=os.environ.get('AZURE_STORAGE_SAS_TOKEN')
)

# All 7 videos
all_videos = [
    "03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20260116_145605-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250516_150120-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250822_150009-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251121_145723-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251219_144752-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250612_105717-会議の録音.mp4"
]

print("Checking existing subtitles...")
print()

# Check each video
videos_to_process = []
skipped_videos = []

for video in all_videos:
    video_name = video.split('/')[-1]
    exists, is_complete, file_size = generator.check_existing_subtitle(video)
    
    if exists and is_complete:
        print(f"[SKIP] {video_name}")
        print(f"       Subtitle is complete ({file_size:,} bytes)")
        skipped_videos.append(video)
    else:
        if exists:
            print(f"[REGENERATE] {video_name}")
            print(f"             Existing subtitle is incomplete ({file_size} bytes)")
        else:
            print(f"[NEW] {video_name}")
            print(f"      No subtitle found")
        videos_to_process.append(video)
    print()

print("="*70)
print(f"Summary:")
print(f"   Skipping: {len(skipped_videos)} videos (already complete)")
print(f"   Processing: {len(videos_to_process)} videos (failed/partial/missing)")
print("="*70)
print()

if len(videos_to_process) == 0:
    print("All videos already have complete subtitles!")
    print("Nothing to do.")
    exit(0)

print("Videos to process:")
for i, video in enumerate(videos_to_process, 1):
    video_name = video.split('/')[-1]
    print(f"   {i}. {video_name}")
print()

# Confirm before processing
response = input("Start batch transcription? (yes/no): ").strip().lower()
if response != 'yes':
    print("Cancelled.")
    exit(0)

print()
print("="*70)
print("Starting Batch Transcription")
print("="*70)
print()

# Process each video
success_count = 0
failed_count = 0
failed_videos = []

for i, video_id in enumerate(videos_to_process, 1):
    video_name = video_id.split('/')[-1]
    print(f"\n[{i}/{len(videos_to_process)}] Processing: {video_name}")
    print("-"*70)
    print()
    
    try:
        generator.process_video_batch(video_id, languages=['ja-JP'])
        success_count += 1
        print(f"[SUCCESS] {video_name}")
        
    except Exception as e:
        failed_count += 1
        failed_videos.append(video_name)
        print(f"[FAILED] {video_name}")
        print(f"   Error: {str(e)}")
        
        # Ask if should continue
        if i < len(videos_to_process):
            response = input("\nContinue with next video? (yes/no): ").strip().lower()
            if response != 'yes':
                print("Stopping batch processing.")
                break
    
    print()

# Final summary
print()
print("="*70)
print("BATCH TRANSCRIPTION COMPLETE!")
print("="*70)
print()
print(f"Results:")
print(f"   Successful: {success_count}/{len(videos_to_process)}")
print(f"   Failed: {failed_count}/{len(videos_to_process)}")
print(f"   Skipped (already complete): {len(skipped_videos)}")
print()

if failed_count > 0:
    print("Failed videos:")
    for video in failed_videos:
        print(f"   - {video}")
    print()

print("Next steps:")
print("   1. Check PacificTube: https://pacifictube-app.yellowbeach-f82aa75e.japaneast.azurecontainerapps.io")
print("   2. Hard refresh (Ctrl + Shift + R)")
print("   3. Test CC button on processed videos")
print("   4. Verify full duration subtitles")
print()
