#!/usr/bin/env python3
"""
Process final 2 meeting videos with OCR
"""
import subprocess
import sys

VIDEOS = [
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250612_105717-会議の録音.mp4",
    "03_定例会議/Recordings/生成AI関連情報連携会議-20250822_150009-会議の録音.mp4",
]

def main():
    print("="*70)
    print("Processing Final 2 Meeting Videos")
    print("="*70)
    
    for i, video in enumerate(VIDEOS, 3):  # Starting from #3
        print(f"\n📹 Processing {i}/4: {video.split('/')[-1]}")
        print("="*70)
        
        result = subprocess.run([sys.executable, "generate_chapters_auto.py", video])
        
        if result.returncode == 0:
            print(f"\n✅ Video {i}/4 complete!")
        else:
            print(f"\n❌ Video {i}/4 failed!")
    
    print("\n" + "="*70)
    print("🎉 All meeting videos processed!")
    print("="*70)

if __name__ == "__main__":
    main()
