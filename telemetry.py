"""
PacificTube Telemetry Tracking Module
Dual-write architecture: Application Insights + Table Storage
- Application Insights: Fast analytics queries for dashboard (90-day retention)
- Table Storage: Permanent backup/archive (unlimited retention)
"""

import os
import uuid
from datetime import datetime, timezone
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module
from azure.data.tables import TableServiceClient, TableEntity
from flask import session, request
import logging

# Initialize logging to Application Insights
insights_connection = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
logger = logging.getLogger(__name__)

if insights_connection:
    logger.addHandler(AzureLogHandler(connection_string=insights_connection))
    logger.setLevel(logging.INFO)

# Initialize Table Storage client
storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
table_service = None
if storage_connection:
    table_service = TableServiceClient.from_connection_string(storage_connection)

# Create tables for permanent storage
TABLE_NAMES = {
    'watch_history': 'WatchHistory',
    'video_analytics': 'VideoAnalytics',
    'user_sessions': 'UserSessions',
    'search_logs': 'SearchLogs',
    'comments': 'Comments',
    'ratings': 'Ratings',
    'user_feedback': 'UserFeedback'
}

def initialize_tables():
    """Create tables if they don't exist"""
    if not table_service:
        return
    
    for table_name in TABLE_NAMES.values():
        try:
            table_service.create_table_if_not_exists(table_name)
        except Exception as e:
            print(f"Error creating table {table_name}: {e}")

# Initialize tables on module import
initialize_tables()


class TelemetryTracker:
    """Main telemetry tracking class - dual-write to App Insights + Table Storage"""
    
    @staticmethod
    def get_user_id():
        """Get user ID from session (Entra ID) or anonymous cookie"""
        if 'user' in session:
            return session['user'].get('oid', 'anonymous')
        
        # Anonymous user - use cookie ID
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        return session['user_id']
    
    @staticmethod
    def get_user_name():
        """Get user name from Entra ID session"""
        if 'user' in session:
            return session['user'].get('name', 'Anonymous')
        return 'Anonymous'
    
    @staticmethod
    def track_video_view(video_path, duration_watched=0, video_duration=0):
        """
        Track video view event
        Writes to: Application Insights (customEvents) + Table Storage (WatchHistory)
        """
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        # Extract folder and video name
        parts = video_path.split('/')
        folder = parts[0] if len(parts) > 1 else 'Root'
        video_name = parts[-1] if parts else video_path
        
        # Get user agent and IP from request context
        try:
            user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'
            ip_address = request.remote_addr if request else 'unknown'
        except RuntimeError:
            # Outside of request context
            user_agent = 'unknown'
            ip_address = 'unknown'
        
        # Log to Application Insights
        properties = {
            'eventType': 'VideoView',
            'userId': user_id,
            'userName': user_name,
            'videoPath': video_path,
            'videoName': video_name,
            'folder': folder,
            'durationWatched': duration_watched,
            'videoDuration': video_duration,
            'completionRate': (duration_watched / video_duration * 100) if video_duration > 0 else 0,
            'ipAddress': ip_address,
            'userAgent': user_agent
        }
        
        # Try to log to Application Insights (optional - don't crash if it fails)
        if insights_connection:
            try:
                logger.info('VideoView', extra={'custom_dimensions': properties})
            except Exception as insights_error:
                # Silent fail - Application Insights is optional
                print(f"Warning: Application Insights logging failed: {insights_error}")
        
        # Write to Table Storage (permanent backup)
        # YouTube-style: Same video on same day = same history entry (update duration, preserve original watch time)
        if table_service:
            try:
                import hashlib
                table_client = table_service.get_table_client(TABLE_NAMES['watch_history'])
                current_time = datetime.now(timezone.utc)
                
                # RowKey: videoId + date (YYYYMMDD) - so same video on same day updates the same row
                # This prevents creating duplicate entries every 10 seconds
                date_str = current_time.strftime('%Y%m%d')
                # Use hash of video_path to keep RowKey short (max 1KB)
                video_hash = hashlib.md5(video_path.encode()).hexdigest()[:16]
                row_key = f"{video_hash}_{date_str}"
                
                # Try to get existing entity first (to preserve original WatchedAt)
                original_watch_time = current_time
                try:
                    existing = table_client.get_entity(partition_key=user_id, row_key=row_key)
                    original_watch_time = existing.get('WatchedAt', current_time)
                except Exception as get_error:
                    # Entity doesn't exist yet - use current time as original watch time
                    pass
                
                entity = {
                    'PartitionKey': user_id,
                    'RowKey': row_key,
                    'WatchedAt': original_watch_time,  # PRESERVE original watch time (like YouTube)
                    'UserId': user_id,
                    'UserName': user_name,
                    'VideoPath': video_path,
                    'VideoId': video_path,  # Add VideoId for history queries
                    'VideoName': video_name,
                    'Folder': folder,
                    'DurationWatched': duration_watched,  # UPDATE duration (latest value)
                    'VideoDuration': video_duration,
                    'CompletionRate': (duration_watched / video_duration * 100) if video_duration > 0 else 0,
                    'IpAddress': ip_address,
                    'UserAgent': user_agent
                }
                
                # Upsert (update if exists, create if not) - like YouTube
                table_client.upsert_entity(entity)
            except Exception as e:
                import traceback
                print(f"Error writing to Table Storage: {e}")
                print(f"Traceback: {traceback.format_exc()}")
    
    @staticmethod
    def track_user_login(login_method='EntraID'):
        """Track user login event"""
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        properties = {
            'eventType': 'UserLogin',
            'userId': user_id,
            'userName': user_name,
            'loginMethod': login_method,
            'ipAddress': request.remote_addr if request else 'unknown'
        }
        
        if insights_connection:
            try:
                logger.info('UserLogin', extra={'custom_dimensions': properties})
            except Exception:
                pass  # Silent fail
        
        if table_service:
            try:
                table_client = table_service.get_table_client(TABLE_NAMES['user_sessions'])
                entity = {
                    'PartitionKey': user_id,
                    'RowKey': str(uuid.uuid4()),
                    'Timestamp': datetime.now(timezone.utc),
                    'UserId': user_id,
                    'UserName': user_name,
                    'LoginMethod': login_method,
                    'IpAddress': request.remote_addr if request else 'unknown',
                    'EventType': 'Login'
                }
                table_client.create_entity(entity)
            except Exception as e:
                print(f"Error writing to Table Storage: {e}")
    
    @staticmethod
    def track_user_logout():
        """Track user logout event"""
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        properties = {
            'eventType': 'UserLogout',
            'userId': user_id,
            'userName': user_name
        }
        
        if insights_connection:
            try:
                logger.info('UserLogout', extra={'custom_dimensions': properties})
            except Exception:
                pass  # Silent fail
        
        if table_service:
            try:
                table_client = table_service.get_table_client(TABLE_NAMES['user_sessions'])
                entity = {
                    'PartitionKey': user_id,
                    'RowKey': str(uuid.uuid4()),
                    'Timestamp': datetime.now(timezone.utc),
                    'UserId': user_id,
                    'UserName': user_name,
                    'EventType': 'Logout'
                }
                table_client.create_entity(entity)
            except Exception as e:
                print(f"Error writing to Table Storage: {e}")
    
    @staticmethod
    def track_search(search_query, results_count=0):
        """Track search query"""
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        properties = {
            'eventType': 'Search',
            'userId': user_id,
            'userName': user_name,
            'searchQuery': search_query,
            'resultsCount': results_count
        }
        
        if insights_connection:
            try:
                logger.info('Search', extra={'custom_dimensions': properties})
            except Exception:
                pass  # Silent fail
        
        if table_service:
            try:
                table_client = table_service.get_table_client(TABLE_NAMES['search_logs'])
                entity = {
                    'PartitionKey': datetime.now(timezone.utc).strftime('%Y%m%d'),
                    'RowKey': str(uuid.uuid4()),
                    'Timestamp': datetime.now(timezone.utc),
                    'UserId': user_id,
                    'UserName': user_name,
                    'SearchQuery': search_query,
                    'ResultsCount': results_count
                }
                table_client.create_entity(entity)
            except Exception as e:
                print(f"Error writing to Table Storage: {e}")
    
    @staticmethod
    def track_comment(video_path, comment_text):
        """Track video comment"""
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        properties = {
            'eventType': 'Comment',
            'userId': user_id,
            'userName': user_name,
            'videoPath': video_path,
            'commentLength': len(comment_text)
        }
        
        if insights_connection:
            try:
                logger.info('Comment', extra={'custom_dimensions': properties})
            except Exception:
                pass  # Silent fail
        
        if table_service:
            try:
                table_client = table_service.get_table_client(TABLE_NAMES['comments'])
                entity = {
                    'PartitionKey': video_path,
                    'RowKey': str(uuid.uuid4()),
                    'Timestamp': datetime.now(timezone.utc),
                    'UserId': user_id,
                    'UserName': user_name,
                    'VideoPath': video_path,
                    'CommentText': comment_text
                }
                table_client.create_entity(entity)
            except Exception as e:
                print(f"Error writing to Table Storage: {e}")
    
    @staticmethod
    def track_rating(video_path, rating_type):
        """Track video like/dislike"""
        user_id = TelemetryTracker.get_user_id()
        user_name = TelemetryTracker.get_user_name()
        
        properties = {
            'eventType': 'Rating',
            'userId': user_id,
            'userName': user_name,
            'videoPath': video_path,
            'ratingType': rating_type  # 'like' or 'dislike'
        }
        
        if insights_connection:
            try:
                logger.info('Rating', extra={'custom_dimensions': properties})
            except Exception:
                pass  # Silent fail
        
        if table_service:
            try:
                table_client = table_service.get_table_client(TABLE_NAMES['ratings'])
                entity = {
                    'PartitionKey': video_path,
                    'RowKey': f"{user_id}_{rating_type}",
                    'Timestamp': datetime.now(timezone.utc),
                    'UserId': user_id,
                    'UserName': user_name,
                    'VideoPath': video_path,
                    'RatingType': rating_type
                }
                table_client.upsert_entity(entity)  # Upsert to allow changing rating
            except Exception as e:
                print(f"Error writing to Table Storage: {e}")
