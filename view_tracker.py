"""
View tracking service for Pacific Tube
Stores video view counts in JSON file
"""

import json
import os
from datetime import datetime
from threading import Lock

VIEWS_FILE = 'views.json'
lock = Lock()


class ViewTracker:
    """Track and manage video view counts"""
    
    def __init__(self):
        self.views_data = self._load_views()
    
    def _load_views(self):
        """Load views data from JSON file"""
        if os.path.exists(VIEWS_FILE):
            try:
                with open(VIEWS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading views: {e}")
                return {}
        return {}
    
    def _save_views(self):
        """Save views data to JSON file"""
        try:
            with open(VIEWS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.views_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving views: {e}")
    
    def get_view_count(self, video_id):
        """Get view count for a video"""
        return self.views_data.get(video_id, {}).get('count', 0)
    
    def increment_view(self, video_id, video_name):
        """Increment view count for a video"""
        with lock:
            if video_id not in self.views_data:
                self.views_data[video_id] = {
                    'count': 0,
                    'name': video_name,
                    'first_viewed': datetime.now().isoformat(),
                    'last_viewed': datetime.now().isoformat()
                }
            
            self.views_data[video_id]['count'] += 1
            self.views_data[video_id]['last_viewed'] = datetime.now().isoformat()
            self._save_views()
            
            return self.views_data[video_id]['count']
    
    def get_all_views(self):
        """Get all view counts"""
        return {video_id: data['count'] for video_id, data in self.views_data.items()}
