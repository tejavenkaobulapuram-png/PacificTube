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
        
        # Retry logic for race condition handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Check if user already liked/disliked
                entity = self.likes_table.get_entity(partition_key="likes", row_key=row_key)
                
                if entity.get('like_type') == 'like':
                    # Already liked, remove like (use ETag for concurrency)
                    self.likes_table.delete_entity(
                        partition_key="likes", 
                        row_key=row_key,
                        etag=entity.metadata['etag'],
                        match_condition=MatchConditions.IfNotModified
                    )
                    action = 'removed_like'
                else:
                    # Was dislike, change to like (use ETag for concurrency)
                    entity['like_type'] = 'like'
                    entity['timestamp'] = datetime.now(timezone.utc).isoformat()
                    self.likes_table.update_entity(
                        entity,
                        mode=UpdateMode.REPLACE,
                        etag=entity.metadata['etag'],
                        match_condition=MatchConditions.IfNotModified
                    )
                    action = 'liked'
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a "not found" error (entity doesn't exist yet)
                if 'ResourceNotFound' in error_msg or 'NotFound' in error_msg:
                    # No existing entity, create new like
                    try:
                        entity = {
                            'PartitionKey': 'likes',
                            'RowKey': row_key,
                            'video_id': video_id,
                            'user_id': user_id,
                            'like_type': 'like',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        self.likes_table.create_entity(entity)
                        action = 'liked'
                        break  # Success
                    except Exception as create_error:
                        # Another request created it, retry
                        if attempt < max_retries - 1:
                            time.sleep(0.05 * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            raise
                # Check if it's a precondition failed (ETag mismatch - race condition)
                elif 'PreconditionFailed' in error_msg or attempt < max_retries - 1:
                    # Retry with backoff
                    time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, 150ms
                    continue
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
        
        # Retry logic for race condition handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Check if user already liked/disliked
                entity = self.likes_table.get_entity(partition_key="likes", row_key=row_key)
                
                if entity.get('like_type') == 'dislike':
                    # Already disliked, remove dislike (use ETag for concurrency)
                    self.likes_table.delete_entity(
                        partition_key="likes", 
                        row_key=row_key,
                        etag=entity.metadata['etag'],
                        match_condition=MatchConditions.IfNotModified
                    )
                    action = 'removed_dislike'
                else:
                    # Was like, change to dislike (use ETag for concurrency)
                    entity['like_type'] = 'dislike'
                    entity['timestamp'] = datetime.now(timezone.utc).isoformat()
                    self.likes_table.update_entity(
                        entity,
                        mode=UpdateMode.REPLACE,
                        etag=entity.metadata['etag'],
                        match_condition=MatchConditions.IfNotModified
                    )
                    action = 'disliked'
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a "not found" error (entity doesn't exist yet)
                if 'ResourceNotFound' in error_msg or 'NotFound' in error_msg:
                    # No existing entity, create new dislike
                    try:
                        entity = {
                            'PartitionKey': 'likes',
                            'RowKey': row_key,
                            'video_id': video_id,
                            'user_id': user_id,
                            'like_type': 'dislike',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        self.likes_table.create_entity(entity)
                        action = 'disliked'
                        break  # Success
                    except Exception as create_error:
                        # Another request created it, retry
                        if attempt < max_retries - 1:
                            time.sleep(0.05 * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            raise
                # Check if it's a precondition failed (ETag mismatch - race condition)
                elif 'PreconditionFailed' in error_msg or attempt < max_retries - 1:
                    # Retry with backoff
                    time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, 150ms
                    continue
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
