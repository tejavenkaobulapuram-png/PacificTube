"""List all video files in blob storage"""
from app import VideoService, ViewTracker

vt = ViewTracker()
vs = VideoService(vt)
videos = vs.get_videos()

print("\n📹 All videos in blob storage:\n")
mp4_count = 0
for i, video in enumerate(videos, 1):
    video_id = video.get('id', '')
    if video_id.endswith('.mp4'):
        mp4_count += 1
        print(f"{mp4_count}. {video_id}")

print(f"\n✅ Total: {mp4_count} videos")
