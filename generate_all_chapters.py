"""Batch process all remaining videos to generate chapters"""
import subprocess
import time

# All videos except the one we already processed
videos = [
    "土木技術基礎講座動画（構造力学）/構造力学（第2回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第3回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第4回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第5回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（イントロ）.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20260116_145605-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20260220_145636-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250516_150120-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251219_144752-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI連携会議-20251121_145723-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250612_105717-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250822_150009-会議の録音.mp4",
]

print(f"🚀 Starting batch chapter generation for {len(videos)} videos")
print(f"⏱️  Estimated time: {len(videos) * 20} minutes (~{len(videos) * 20 // 60} hours)\n")

start_time = time.time()
successful = []
failed = []

for i, video in enumerate(videos, 1):
    print(f"\n{'='*70}")
    print(f"📹 Processing {i}/{len(videos)}: {video}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(
            ["python", "generate_chapters_auto.py", video],
            capture_output=False,
            text=True,
            check=True
        )
        successful.append(video)
        print(f"\n✅ Successfully generated chapters for: {video}")
    except subprocess.CalledProcessError as e:
        failed.append(video)
        print(f"\n❌ Failed to generate chapters for: {video}")
        print(f"   Error: {e}")
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Process interrupted by user!")
        print(f"✅ Completed: {len(successful)} videos")
        print(f"❌ Failed: {len(failed)} videos")
        print(f"⏸️  Remaining: {len(videos) - i} videos")
        break

elapsed = time.time() - start_time

print(f"\n{'='*70}")
print(f"🎉 Batch processing complete!")
print(f"{'='*70}")
print(f"✅ Successful: {len(successful)} videos")
print(f"❌ Failed: {len(failed)} videos")
print(f"⏱️  Total time: {elapsed/60:.1f} minutes")

if failed:
    print(f"\n❌ Failed videos:")
    for video in failed:
        print(f"   - {video}")

print(f"\n📤 Next step: Run 'python upload_chapters.py' to upload all chapter files to blob storage")
