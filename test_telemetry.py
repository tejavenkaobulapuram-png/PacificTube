"""
Generate sample telemetry data for dashboard testing
This script creates realistic test data in Application Insights using direct HTTP API
"""
import os
import random
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample data
USERS = [
    "user001", "user002", "user003", "user004", "user005",
    "user006", "user007", "user008", "user009", "user010"
]

USER_NAMES = [
    "田中太郎", "佐藤花子", "鈴木一郎", "高橋美咲", "渡辺健太",
    "伊藤さくら", "山本大輔", "中村優子", "小林光", "加藤真理"
]

VIDEOS = [
    "構造力学（イントロ）", "構造力学（第1回）", "構造力学（第2回）",
    "構造力学（第3回）", "構造力学（第4回）", "構造力学（第5回）"
]

FOLDERS = ["土木技術基礎講座動画（構造力学）", "建設管理", "測量技術", "材料力学"]

SEARCH_QUERIES = ["構造力学", "力学", "イントロ", "第1回", "基礎", "講座", "土木"]

ACTIONS = ["video_view", "video_complete", "login", "search", "like", "comment"]

def send_custom_event(ingestion_endpoint, ikey, event_name, properties, timestamp=None):
    """Send a custom event to Application Insights using REST API"""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    url = f"{ingestion_endpoint}/v2/track"
    
    payload = {
        "name": f"Microsoft.ApplicationInsights.{ikey}.Event",
        "time": timestamp,
        "iKey": ikey,
        "data": {
            "baseType": "EventData",
            "baseData": {
                "ver": 2,
                "name": event_name,
                "properties": properties
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except Exception as e:
        return False

def generate_sample_data():
    """Generate realistic telemetry data for the past 30 days"""
    
    print("🔄 Generating sample telemetry data...")
    
    # Parse connection string
    connection_string = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    if not connection_string:
        print("❌ Error: APPLICATIONINSIGHTS_CONNECTION_STRING not found in .env")
        return
    
    # Extract InstrumentationKey and IngestionEndpoint
    parts = dict(part.split('=', 1) for part in connection_string.split(';') if '=' in part)
    ikey = parts.get('InstrumentationKey')
    ingestion_endpoint = parts.get('IngestionEndpoint', 'https://japaneast-1.in.applicationinsights.azure.com')
    
    print(f"📊 Instrumentation Key: {ikey[:20]}...")
    print(f"🌐 Ingestion Endpoint: {ingestion_endpoint}")
    
    # Generate data for the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    events_generated = 0
    success_count = 0
    
    # Simulate daily activity
    current_date = start_date
    while current_date <= end_date:
        # Number of events decreases on weekends
        is_weekend = current_date.weekday() >= 5
        daily_events = random.randint(10, 30) if not is_weekend else random.randint(3, 10)
        
        for _ in range(daily_events):
            user_idx = random.randint(0, len(USERS) - 1)
            user = USERS[user_idx]
            user_name = USER_NAMES[user_idx]
            action = random.choice(ACTIONS)
            
            # Generate timestamp for this event
            event_time = current_date + timedelta(
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            timestamp = event_time.isoformat() + "Z"
            
            properties = {
                "user_id": user,
                "user_name": user_name,
                "action": action
            }
            
            if action == "video_view":
                video = random.choice(VIDEOS)
                folder = random.choice(FOLDERS)
                duration = random.randint(30, 600)  # 30s to 10min
                completion = min(100, int((duration / 600) * 100 + random.randint(-10, 20)))
                
                properties.update({
                    "video_title": video,
                    "folder": folder,
                    "duration_seconds": duration,
                    "completion_percent": completion
                })
                
            elif action == "video_complete":
                video = random.choice(VIDEOS)
                properties.update({
                    "video_title": video,
                    "completion_percent": 100
                })
                
            elif action == "search":
                query = random.choice(SEARCH_QUERIES)
                properties.update({"search_query": query})
            
            # Send event
            if send_custom_event(ingestion_endpoint, ikey, action, properties, timestamp):
                success_count += 1
            
            events_generated += 1
            
            # Show progress every 100 events
            if events_generated % 100 == 0:
                print(f"  📝 Generated {events_generated} events ({success_count} sent successfully)...")
        
        current_date += timedelta(days=1)
    
    print(f"\n✅ Generated {events_generated} telemetry events")
    print(f"📤 Successfully sent {success_count} events to Application Insights")
    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"👥 Users: {len(USERS)}")
    print(f"🎬 Videos: {len(VIDEOS)}")
    print("\n⏳ Data takes 2-3 minutes to appear in Application Insights...")
    print("\n✅ Next steps:")
    print("   1. Run: python app.py")
    print("   2. Visit: http://localhost:5000/dashboard")
    print("   3. Select time period: 7d, 30d, or 90d")

if __name__ == "__main__":
    generate_sample_data()
