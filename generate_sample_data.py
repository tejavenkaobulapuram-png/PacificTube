"""
Test script to generate sample telemetry data for dashboard testing
Run this to populate Application Insights and Table Storage with sample data
"""

import os
import sys
from datetime import datetime, timedelta, timezone
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import telemetry module
from telemetry import TelemetryTracker, initialize_tables

# Initialize tables
print("📊 Initializing Table Storage tables...")
initialize_tables()
print("✅ Tables created successfully")

# Sample data
sample_videos = [
    "土木技術基礎講座動画（構造力学）/構造力学（イントロ）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第1回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第2回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第3回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第4回）.mp4",
    "土木技術基礎講座動画（構造力学）/構造力学（第5回）.mp4"
]

sample_users = [
    ("user1", "田中太郎"),
    ("user2", "佐藤花子"),
    ("user3", "鈴木一郎"),
    ("user4", "高橋美咲"),
    ("user5", "伊藤健太")
]

sample_searches = [
    "構造力学",
    "応力",
    "モーメント",
    "梁",
    "トラス",
    "せん断力"
]

print("\n📝 Generating sample telemetry data...")
print("=" * 60)

# Generate sample data for the past 7 days
events_generated = 0

for days_ago in range(7, 0, -1):
    day_events = 0
    print(f"\n📅 Day -{days_ago}: Generating events...")
    
    # Generate 10-30 video views per day
    num_views = random.randint(10, 30)
    for _ in range(num_views):
        video = random.choice(sample_videos)
        user_id, user_name = random.choice(sample_users)
        
        # Simulate video views
        from flask import session
        session['user'] = {'oid': user_id, 'name': user_name}
        
        duration = random.randint(60, 1200)  # 1-20 minutes watched
        total_duration = random.randint(duration, 1800)  # Total video length
        
        TelemetryTracker.track_video_view(video, duration, total_duration)
        day_events += 1
    
    # Generate 2-5 logins per day
    num_logins = random.randint(2, 5)
    for _ in range(num_logins):
        user_id, user_name = random.choice(sample_users)
        session['user'] = {'oid': user_id, 'name': user_name}
        
        TelemetryTracker.track_user_login('EntraID')
        day_events += 1
    
    # Generate 3-8 searches per day
    num_searches = random.randint(3, 8)
    for _ in range(num_searches):
        user_id, user_name = random.choice(sample_users)
        session['user'] = {'oid': user_id, 'name': user_name}
        
        query = random.choice(sample_searches)
        results = random.randint(1, 6)
        
        TelemetryTracker.track_search(query, results)
        day_events += 1
    
    # Generate 1-3 comments per day
    num_comments = random.randint(1, 3)
    for _ in range(num_comments):
        user_id, user_name = random.choice(sample_users)
        session['user'] = {'oid': user_id, 'name': user_name}
        
        video = random.choice(sample_videos)
        comment = "This is a test comment for the dashboard"
        
        TelemetryTracker.track_comment(video, comment)
        day_events += 1
    
    # Generate 2-6 ratings per day
    num_ratings = random.randint(2, 6)
    for _ in range(num_ratings):
        user_id, user_name = random.choice(sample_users)
        session['user'] = {'oid': user_id, 'name': user_name}
        
        video = random.choice(sample_videos)
        rating = random.choice(['like', 'dislike'])
        
        TelemetryTracker.track_rating(video, rating)
        day_events += 1
    
    print(f"   ✅ Generated {day_events} events")
    events_generated += day_events

print("\n" + "=" * 60)
print(f"✨ Successfully generated {events_generated} sample events!")
print("\n📊 Data has been written to:")
print("   1. Application Insights (for dashboard queries)")
print("   2. Table Storage (for permanent backup)")
print("\n🌐 You can now view the dashboard at:")
print("   http://localhost:5000/dashboard")
print("=" * 60)
