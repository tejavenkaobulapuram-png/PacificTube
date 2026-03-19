"""
View tracking service using Azure Table Storage
Stores video view counts in cloud-based NoSQL database
"""

from azure.data.tables import TableServiceClient, TableEntity
from azure.core.credentials import AzureSasCredential
from datetime import datetime, timezone
import os


class CloudViewTracker:
    """Track and manage video view counts using Azure Table Storage"""
    
    def __init__(self, connection_string=None, storage_account=None, sas_token=None):
        """
        Initialize with either connection string or storage account + SAS token
        """
        self.table_name = "views"  # Must match the table name in SAS token
        
        if connection_string:
            # Use connection string (for local development)
            self.table_service = TableServiceClient.from_connection_string(connection_string)
        elif storage_account and sas_token:
            # Use SAS token (for production)
            account_url = f"https://{storage_account}.table.core.windows.net"
            credential = AzureSasCredential(sas_token)
            self.table_service = TableServiceClient(endpoint=account_url, credential=credential)
        else:
            raise ValueError("Must provide either connection_string or (storage_account + sas_token)")
        
        # Create table if it doesn't exist
        try:
            self.table_client = self.table_service.create_table_if_not_exists(self.table_name)
            if not self.table_client:
                self.table_client = self.table_service.get_table_client(self.table_name)
        except Exception as e:
            print(f"Error creating/getting table: {e}")
            self.table_client = self.table_service.get_table_client(self.table_name)
    
    def _sanitize_key(self, video_id):
        """
        Sanitize video ID to be valid Azure Table Storage key
        Replace invalid characters
        """
        # Azure Table Storage keys can't have: / \ # ?
        return video_id.replace('/', '_').replace('\\', '_').replace('#', '_').replace('?', '_')
    
    def get_view_count(self, video_id):
        """Get view count for a video"""
        try:
            sanitized_id = self._sanitize_key(video_id)
            entity = self.table_client.get_entity(partition_key="views", row_key=sanitized_id)
            return entity.get('count', 0)
        except Exception:
            # Entity doesn't exist yet
            return 0
    
    def increment_view(self, video_id, video_name):
        """Increment view count for a video"""
        try:
            sanitized_id = self._sanitize_key(video_id)
            
            # Try to get existing entity
            try:
                entity = self.table_client.get_entity(partition_key="views", row_key=sanitized_id)
                entity['count'] += 1
                entity['last_viewed'] = datetime.now(timezone.utc).isoformat()
                self.table_client.update_entity(entity, mode="replace")
            except Exception:
                # Entity doesn't exist, create new one
                entity = {
                    'PartitionKey': 'views',
                    'RowKey': sanitized_id,
                    'video_id': video_id,
                    'name': video_name,
                    'count': 1,
                    'first_viewed': datetime.now(timezone.utc).isoformat(),
                    'last_viewed': datetime.now(timezone.utc).isoformat()
                }
                self.table_client.create_entity(entity)
            
            return entity['count']
        except Exception as e:
            print(f"Error incrementing view for {video_id}: {e}")
            return 0
    
    def get_all_views(self):
        """Get all view counts as dictionary"""
        try:
            views = {}
            entities = self.table_client.list_entities()
            for entity in entities:
                original_id = entity.get('video_id', entity['RowKey'])
                views[original_id] = entity.get('count', 0)
            return views
        except Exception as e:
            print(f"Error getting all views: {e}")
            return {}
    
    def get_top_videos(self, limit=10):
        """Get top viewed videos"""
        try:
            entities = list(self.table_client.list_entities())
            sorted_entities = sorted(entities, key=lambda x: x.get('count', 0), reverse=True)
            return [
                {
                    'video_id': e.get('video_id', e['RowKey']),
                    'name': e.get('name', 'Unknown'),
                    'views': e.get('count', 0),
                    'last_viewed': e.get('last_viewed')
                }
                for e in sorted_entities[:limit]
            ]
        except Exception as e:
            print(f"Error getting top videos: {e}")
            return []
