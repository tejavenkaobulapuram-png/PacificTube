#!/usr/bin/env python3
"""
Generate both Japanese and English subtitles for a video
"""

import os
from dotenv import load_dotenv
from generate_subtitles import AutoSubtitleGenerator

load_dotenv()

# Azure configuration
speech_key = os.getenv('AZURE_SPEECH_KEY')
speech_region = os.getenv('AZURE_SPEECH_REGION')
storage_account = 'pacifictubesa'
blob_sas = os.getenv('AZURE_STORAGE_BLOB_SAS_TOKEN')

# Initialize generator
generator = AutoSubtitleGenerator(speech_key, speech_region, storage_account, blob_sas)

# Example: Generate Japanese + English for the new video
video_id = '03_定例会議/Recordings/生成AI連携会議-20260319_145437-会議の録音.mp4'

print("="*70)
print("Dual Language Subtitle Generator (Japanese + English)")
print("="*70)
print()
print(f"Video: {video_id}")
print("Languages: Japanese (ja-JP), English (en-US)")
print()
print("This will generate:")
print("  1. video.ja.vtt - Japanese transcription")
print("  2. video.en.vtt - English transcription")
print()
print("Cost: ~¥300 (¥150 per language)")
print()

confirmation = input("Continue? (yes/no): ").strip().lower()

if confirmation == 'yes':
    # Generate subtitles for both languages
    generator.process_video(video_id, languages=['ja-JP', 'en-US'])
    
    print()
    print("="*70)
    print("✅ Dual language subtitles generated successfully!")
    print("="*70)
    print()
    print("Users can now switch between Japanese and English")
    print("using the CC button in the video player.")
else:
    print("Cancelled")
