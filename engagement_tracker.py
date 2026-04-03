"""
Engagement tracking service using Azure Table Storage
Handles likes, dislikes, and comments for videos
"""

from azure.data.tables import TableServiceClient, TableEntity, UpdateMode
from azure.core.credentials import AzureSasCredential
from azure.core import MatchConditions
from datetime import datetime, timezone
import uuid
import time


class EngagementTracker:
    """Track video engagement (likes, dislikes, comments)"""
    
    def __init__(self, connection_string=None, storage_account=None, sas_token=None):
        """Initialize with either connection string or storage account + SAS token"""
        
        if connection_string:
            self.table_service = TableServiceClient.from_connection_string(connection_string)
        elif storage_account and sas_token:
            account_url = f"https://{storage_account}.table.core.windows.net"
            credential = AzureSasCredential(sas_token)
            self.table_service = TableServiceClient(endpoint=account_url, credential=credential)
        else:
            raise ValueError("Must provide either connection_string or (storage_account + sas_token)")
        
        # Create tables if they don't exist
        self.likes_table = self._get_or_create_table("videolikes")
        self.comments_table = self._get_or_create_table("videocomments")
        self.watch_positions_table = self._get_or_create_table("watchpositions")
    
    def _get_or_create_table(self, table_name):
        """Get table client, creating table if it doesn't exist"""
        try:
            table_client = self.table_service.create_table_if_not_exists(table_name)
            if not table_client:
                table_client = self.table_service.get_table_client(table_name)
            return table_client
        except Exception as e:
            print(f"Error creating/getting table {table_name}: {e}")
            return self.table_service.get_table_client(table_name)
    
    def _sanitize_key(self, key):
        """Sanitize key to be valid for Azure Table Storage"""
        return key.replace('/', '_').replace('\\', '_').replace('#', '_').replace('?', '_')
    
    # ===== LIKES/DISLIKES =====
    
    def toggle_like(self, video_id, user_id):
        """Toggle like for a video. Returns (likes_count, dislikes_count, user_action)"""
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        row_key = f"{video_key}_{user_key}"
        current_timestamp = datetime.now(timezone.utc)
        
        try:
            # Try to get existing entity
            entity = self.likes_table.get_entity(partition_key="likes", row_key=row_key)
            
            # Check timestamp to prevent rapid clicks (database-level rate limit)
            if 'timestamp' in entity:
                last_time = datetime.fromisoformat(entity['timestamp'].replace('Z', '+00:00'))
                time_diff = (current_timestamp - last_time).total_seconds()
                if time_diff < 2.0:  # Ignore clicks within 2 seconds
                    print(f"⚠️ DB rate limit: Like rejected ({time_diff:.2f}s too soon)")
                    # Return current counts without modification
                    counts = self.get_engagement(video_id)
                    return counts['likes'], counts['dislikes'], entity.get('like_type', 'none')
            
            # Toggle logic
            if entity.get('like_type') == 'like':
                # Remove like
                self.likes_table.delete_entity(partition_key="likes", row_key=row_key)
                action = 'removed_like'
            else:
                # Change to like
                entity['like_type'] = 'like'
                entity['timestamp'] = current_timestamp.isoformat()
                self.likes_table.upsert_entity(entity, mode=UpdateMode.REPLACE)
                action = 'liked'
                
        except Exception as e:
            # Entity doesn't exist - create new like
            if 'ResourceNotFound' in str(e) or 'NotFound' in str(e):
                entity = {
                    'PartitionKey': 'likes',
                    'RowKey': row_key,
                    'video_id': video_id,
                    'user_id': user_id,
                    'like_type': 'like',
                    'timestamp': current_timestamp.isoformat()
                }
                self.likes_table.upsert_entity(entity, mode=UpdateMode.REPLACE)
                action = 'liked'
            else:
                raise
        
        # Return updated counts
        counts = self.get_engagement(video_id)
        return counts['likes'], counts['dislikes'], action
    
    def toggle_dislike(self, video_id, user_id):
        """Toggle dislike for a video. Returns (likes_count, dislikes_count, user_action)"""
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        row_key = f"{video_key}_{user_key}"
        current_timestamp = datetime.now(timezone.utc)
        
        try:
            # Try to get existing entity
            entity = self.likes_table.get_entity(partition_key="likes", row_key=row_key)
            
            # Check timestamp to prevent rapid clicks (database-level rate limit)
            if 'timestamp' in entity:
                last_time = datetime.fromisoformat(entity['timestamp'].replace('Z', '+00:00'))
                time_diff = (current_timestamp - last_time).total_seconds()
                if time_diff < 2.0:  # Ignore clicks within 2 seconds
                    print(f"⚠️ DB rate limit: Dislike rejected ({time_diff:.2f}s too soon)")
                    # Return current counts without modification
                    counts = self.get_engagement(video_id)
                    return counts['likes'], counts['dislikes'], entity.get('like_type', 'none')
            
            # Toggle logic
            if entity.get('like_type') == 'dislike':
                # Remove dislike
                self.likes_table.delete_entity(partition_key="likes", row_key=row_key)
                action = 'removed_dislike'
            else:
                # Change to dislike
                entity['like_type'] = 'dislike'
                entity['timestamp'] = current_timestamp.isoformat()
                self.likes_table.upsert_entity(entity, mode=UpdateMode.REPLACE)
                action = 'disliked'
                
        except Exception as e:
            # Entity doesn't exist - create new dislike
            if 'ResourceNotFound' in str(e) or 'NotFound' in str(e):
                entity = {
                    'PartitionKey': 'likes',
                    'RowKey': row_key,
                    'video_id': video_id,
                    'user_id': user_id,
                    'like_type': 'dislike',
                    'timestamp': current_timestamp.isoformat()
                }
                self.likes_table.upsert_entity(entity, mode=UpdateMode.REPLACE)
                action = 'disliked'
            else:
                raise
        
        # Return updated counts
        counts = self.get_engagement(video_id)
        return counts['likes'], counts['dislikes'], action
    
    def get_user_action(self, video_id, user_id):
        """Get user's current action (like/dislike/none) for a video"""
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        row_key = f"{video_key}_{user_key}"
        
        try:
            entity = self.likes_table.get_entity(partition_key="likes", row_key=row_key)
            return entity.get('like_type', 'none')
        except:
            return 'none'
    
    # ===== COMMENTS =====
    
    def add_comment(self, video_id, text, author_name="Anonymous"):
        """Add a comment to a video. Returns the created comment"""
        comment_id = str(uuid.uuid4())
        video_key = self._sanitize_key(video_id)
        row_key = f"{video_key}_{comment_id}"
        
        entity = {
            'PartitionKey': 'comments',
            'RowKey': row_key,
            'video_id': video_id,
            'comment_id': comment_id,
            'text': text,
            'author_name': author_name,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            self.comments_table.create_entity(entity)
            return {
                'id': comment_id,
                'text': text,
                'author': author_name,
                'timestamp': entity['timestamp']
            }
        except Exception as e:
            print(f"Error adding comment: {e}")
            raise
    
    def get_comments(self, video_id, limit=50):
        """Get comments for a video"""
        video_key = self._sanitize_key(video_id)
        
        try:
            # Query comments for this video
            filter_query = f"PartitionKey eq 'comments' and video_id eq '{video_id}'"
            entities = self.comments_table.query_entities(filter_query)
            
            comments = []
            for entity in entities:
                comments.append({
                    'id': entity.get('comment_id', ''),
                    'text': entity.get('text', ''),
                    'author': entity.get('author_name', 'Anonymous'),
                    'timestamp': entity.get('timestamp', '')
                })
            
            # Sort by timestamp (newest first)
            comments.sort(key=lambda x: x['timestamp'], reverse=True)
            return comments[:limit]
        except Exception as e:
            print(f"Error getting comments: {e}")
            return []
    
    # ===== AGGREGATE DATA =====
    
    def get_engagement(self, video_id):
        """Get all engagement data for a video (likes, dislikes, comments count)"""
        video_key = self._sanitize_key(video_id)
        
        # Count likes and dislikes
        likes_count = 0
        dislikes_count = 0
        
        try:
            filter_query = f"PartitionKey eq 'likes' and video_id eq '{video_id}'"
            entities = self.likes_table.query_entities(filter_query)
            
            for entity in entities:
                if entity.get('like_type') == 'like':
                    likes_count += 1
                elif entity.get('like_type') == 'dislike':
                    dislikes_count += 1
        except Exception as e:
            print(f"Error counting likes/dislikes: {e}")
        
        # Count comments
        comments_count = 0
        try:
            filter_query = f"PartitionKey eq 'comments' and video_id eq '{video_id}'"
            entities = self.comments_table.query_entities(filter_query)
            comments_count = len(list(entities))
        except Exception as e:
            print(f"Error counting comments: {e}")
        
        return {
            'likes': likes_count,
            'dislikes': dislikes_count,
            'comments': comments_count
        }
    
    # ===== WATCH POSITION (Resume Feature) =====
    
    def save_watch_position(self, video_id, user_id, position, duration=0):
        """Save user's watch position for resume feature (like YouTube)"""
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        row_key = f"{video_key}_{user_key}"
        
        try:
            entity = {
                'PartitionKey': 'watchpositions',
                'RowKey': row_key,
                'video_id': video_id,
                'user_id': user_id,
                'position': position,  # Current watch position in seconds
                'duration': duration,  # Total video duration
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'percentage': round((position / duration * 100) if duration > 0 else 0, 2)
            }
            # Use upsert to create or update
            self.watch_positions_table.upsert_entity(entity, mode=UpdateMode.REPLACE)
            return True
        except Exception as e:
            print(f"Error saving watch position: {e}")
            return False
    
    def get_watch_position(self, video_id, user_id):
        """Get user's last watch position for a video"""
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        row_key = f"{video_key}_{user_key}"
        
        try:
            entity = self.watch_positions_table.get_entity(
                partition_key='watchpositions',
                row_key=row_key
            )
            return {
                'position': entity.get('position', 0),
                'duration': entity.get('duration', 0),
                'percentage': entity.get('percentage', 0),
                'timestamp': entity.get('timestamp', '')
            }
        except:
            # No saved position found
            return None
    
    # ===== AUDIT LOGGING =====
    
    def log_video_access(self, video_id, user_id, ip_address):
        """Log video access for security audit trail
        
        Tracks who accessed which video, when, and from which IP.
        Used for security monitoring and compliance.
        """
        if not hasattr(self, 'access_log_table'):
            # Create access log table if it doesn't exist
            self.access_log_table = self._get_or_create_table("videoaccesslog")
        
        video_key = self._sanitize_key(video_id)
        user_key = self._sanitize_key(user_id)
        timestamp = datetime.now(timezone.utc)
        row_key = f"{video_key}_{user_key}_{int(timestamp.timestamp() * 1000)}"
        
        try:
            entity = {
                'PartitionKey': video_key,  # Partition by video for efficient queries
                'RowKey': row_key,
                'video_id': video_id,
                'user_id': user_id,
                'ip_address': ip_address,
                'timestamp': timestamp.isoformat(),
                'action': 'video_url_requested'
            }
            self.access_log_table.create_entity(entity)
            print(f"📊 Audit log: {user_id} accessed {video_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error logging access: {e}")
            return False
