"""
PacificTube Dashboard Routes
Queries Application Insights using KQL (Kusto Query Language)
Similar to colleague's dashboard design with 7/30/90 day time periods
"""

import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, jsonify, request, session
from dashboard_auth import require_dashboard_access

dashboard_bp = Blueprint('dashboard', __name__)

WORKSPACE_ID = 'a0aec3ef-ac1b-4a6a-92ef-9ea18974fd60'  # Log Analytics Workspace ID


@dashboard_bp.route('/dashboard')
@require_dashboard_access
def dashboard_select():
    """
    Dashboard landing page - show time period selection
    User selects 7d, 30d, or 90d
    """
    return render_template('dashboard_select.html')


@dashboard_bp.route('/dashboard/<period>')
@require_dashboard_access
def dashboard(period):
    """
    Main dashboard route - displays analytics for specified time period
    Periods: 7d, 30d, 90d
    Restricted to authorized users only
    """
    valid_periods = ['7d', '30d', '90d']
    if period not in valid_periods:
        period = '7d'
    
    return render_template('dashboard.html', period=period)


@dashboard_bp.route('/api/dashboard/metrics/<period>')
@require_dashboard_access
def get_dashboard_metrics(period):
    """
    API endpoint to fetch dashboard metrics
    Returns JSON with all metrics cards data
    Restricted to authorized users only
    """
    from azure.data.tables import TableServiceClient
    from telemetry import TABLE_NAMES
    
    valid_periods = {'7d': 7, '30d': 30, '90d': 90}
    days = valid_periods.get(period, 7)
    
    try:
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Get storage connection
        storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not storage_connection:
            # Return empty data if no storage configured
            return jsonify({
                'totalEvents': 0,
                'userLogins': 0,
                'videoViews': 0,
                'searches': 0,
                'comments': 0,
                'likes': 0,
                'dislikes': 0,
                'uniqueUsers': 0,
                'uniqueVideos': 0
            })
        
        table_service = TableServiceClient.from_connection_string(storage_connection)
        
        # Query each table for counts
        metrics = {
            'totalEvents': 0,
            'userLogins': 0,
            'videoViews': 0,
            'searches': 0,
            'comments': 0,
            'likes': 0,
            'dislikes': 0,
            'uniqueUsers': set(),
            'uniqueVideos': set(),
            'minDate': None,
            'maxDate': None
        }
        
        # Helper function to track actual date range
        def update_date_range(timestamp):
            if metrics['minDate'] is None or timestamp < metrics['minDate']:
                metrics['minDate'] = timestamp
            if metrics['maxDate'] is None or timestamp > metrics['maxDate']:
                metrics['maxDate'] = timestamp
        
        # Count watch history (video views)
        try:
            watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = watch_table.query_entities(filter_query)
            for entity in entities:
                metrics['videoViews'] += 1
                metrics['totalEvents'] += 1
                metrics['uniqueUsers'].add(entity.get('UserId', 'unknown'))
                metrics['uniqueVideos'].add(entity.get('VideoPath', 'unknown'))
                update_date_range(entity.get('Timestamp'))
        except Exception as e:
            print(f"Error querying watch_history: {e}")
        
        # Count user sessions (logins)
        try:
            session_table = table_service.get_table_client(TABLE_NAMES['user_sessions'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}' and EventType eq 'Login'"
            entities = session_table.query_entities(filter_query)
            for entity in entities:
                metrics['userLogins'] += 1
                metrics['totalEvents'] += 1
                metrics['uniqueUsers'].add(entity.get('UserId', 'unknown'))
                update_date_range(entity.get('Timestamp'))
        except Exception as e:
            print(f"Error querying user_sessions: {e}")
        
        # Count searches
        try:
            search_table = table_service.get_table_client(TABLE_NAMES['search_logs'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = search_table.query_entities(filter_query)
            for entity in entities:
                metrics['searches'] += 1
                metrics['totalEvents'] += 1
                metrics['uniqueUsers'].add(entity.get('UserId', 'unknown'))
                update_date_range(entity.get('Timestamp'))
        except Exception as e:
            print(f"Error querying search_logs: {e}")
        
        # Count comments
        try:
            comment_table = table_service.get_table_client(TABLE_NAMES['comments'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = comment_table.query_entities(filter_query)
            for entity in entities:
                metrics['comments'] += 1
                metrics['totalEvents'] += 1
                metrics['uniqueUsers'].add(entity.get('UserId', 'unknown'))
                update_date_range(entity.get('Timestamp'))
        except Exception as e:
            print(f"Error querying comments: {e}")
        
        # Count ratings (likes/dislikes)
        try:
            rating_table = table_service.get_table_client(TABLE_NAMES['ratings'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = rating_table.query_entities(filter_query)
            for entity in entities:
                rating_type = entity.get('RatingType', '')
                if rating_type == 'like':
                    metrics['likes'] += 1
                elif rating_type == 'dislike':
                    metrics['dislikes'] += 1
                metrics['totalEvents'] += 1
                metrics['uniqueUsers'].add(entity.get('UserId', 'unknown'))
                update_date_range(entity.get('Timestamp'))
        except Exception as e:
            print(f"Error querying ratings: {e}")
        
        # Format actual date range from data
        if metrics['minDate'] and metrics['maxDate']:
            date_range_start = metrics['minDate'].strftime('%Y-%m-%d')
            date_range_end = metrics['maxDate'].strftime('%Y-%m-%d')
        else:
            # Fallback to calculated range if no data
            date_range_start = start_time.strftime('%Y-%m-%d')
            date_range_end = end_time.strftime('%Y-%m-%d')
        
        return jsonify({
            'totalEvents': metrics['totalEvents'],
            'userLogins': metrics['userLogins'],
            'videoViews': metrics['videoViews'],
            'searches': metrics['searches'],
            'comments': metrics['comments'],
            'likes': metrics['likes'],
            'dislikes': metrics['dislikes'],
            'uniqueUsers': len(metrics['uniqueUsers']),
            'uniqueVideos': len(metrics['uniqueVideos']),
            'dateRangeStart': date_range_start,
            'dateRangeEnd': date_range_end
        })
        
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/trend/<period>')
@require_dashboard_access
def get_trend_data(period):
    """
    Get daily activity trend for line chart
    Restricted to authorized users only
    """
    from azure.data.tables import TableServiceClient
    from telemetry import TABLE_NAMES
    from collections import defaultdict
    
    valid_periods = {'7d': 7, '30d': 30, '90d': 90}
    days = valid_periods.get(period, 7)
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not storage_connection:
            return jsonify([])
        
        table_service = TableServiceClient.from_connection_string(storage_connection)
        
        # Get all events and group by date
        daily_counts = defaultdict(int)
        
        # Query all event tables
        for table_name in [TABLE_NAMES['watch_history'], TABLE_NAMES['user_sessions'], 
                           TABLE_NAMES['search_logs'], TABLE_NAMES['comments'], TABLE_NAMES['ratings']]:
            try:
                table_client = table_service.get_table_client(table_name)
                filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
                entities = table_client.query_entities(filter_query)
                
                for entity in entities:
                    # For watch_history, try WatchedAt first, then Timestamp
                    if table_name == TABLE_NAMES['watch_history']:
                        timestamp = entity.get('WatchedAt') or entity.get('Timestamp')
                    else:
                        timestamp = entity.get('Timestamp')
                    
                    if timestamp:
                        # Ensure timestamp is a datetime object
                        if isinstance(timestamp, str):
                            from dateutil import parser
                            timestamp = parser.parse(timestamp)
                        
                        date_key = timestamp.strftime('%Y-%m-%d')
                        daily_counts[date_key] += 1
            except Exception as e:
                print(f"Error querying {table_name}: {e}")
        
        # Convert to sorted list
        data = [{'date': date, 'count': count} for date, count in sorted(daily_counts.items())]
        return jsonify(data)
        
    except Exception as e:
        print(f"Error fetching trend data: {e}")
        return jsonify([])


@dashboard_bp.route('/api/dashboard/folders/<period>')
@require_dashboard_access
def get_folder_distribution(period):
    """
    Get video views by folder for pie chart
    Restricted to authorized users only
    """
    from azure.data.tables import TableServiceClient
    from telemetry import TABLE_NAMES
    from collections import defaultdict
    
    valid_periods = {'7d': 7, '30d': 30, '90d': 90}
    days = valid_periods.get(period, 7)
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not storage_connection:
            return jsonify([])
        
        table_service = TableServiceClient.from_connection_string(storage_connection)
        folder_counts = defaultdict(int)
        
        try:
            watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = watch_table.query_entities(filter_query)
            
            for entity in entities:
                folder = entity.get('Folder', 'Unknown')
                folder_counts[folder] += 1
        except Exception as e:
            print(f"Error querying folders: {e}")
        
        # Convert to list and sort by count
        data = [{'folder': folder, 'count': count} for folder, count in folder_counts.items()]
        data.sort(key=lambda x: x['count'], reverse=True)
        return jsonify(data[:10])  # Top 10
        
    except Exception as e:
        print(f"Error fetching folder distribution: {e}")
        return jsonify([])


@dashboard_bp.route('/api/dashboard/videos/<period>')
@require_dashboard_access
def get_top_videos(period):
    """
    Get top 10 videos for pie chart
    Restricted to authorized users only
    """
    from azure.data.tables import TableServiceClient
    from telemetry import TABLE_NAMES
    from collections import defaultdict
    
    valid_periods = {'7d': 7, '30d': 30, '90d': 90}
    days = valid_periods.get(period, 7)
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not storage_connection:
            return jsonify([])
        
        table_service = TableServiceClient.from_connection_string(storage_connection)
        video_counts = defaultdict(int)
        
        try:
            watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = watch_table.query_entities(filter_query)
            
            for entity in entities:
                video = entity.get('VideoName', 'Unknown')
                video_counts[video] += 1
        except Exception as e:
            print(f"Error querying videos: {e}")
        
        # Convert to list and sort by count
        data = [{'video': video, 'count': count} for video, count in video_counts.items()]
        data.sort(key=lambda x: x['count'], reverse=True)
        return jsonify(data[:10])  # Top 10
        
    except Exception as e:
        print(f"Error fetching top videos: {e}")
        return jsonify([])


@dashboard_bp.route('/api/dashboard/active-users/<period>')
@require_dashboard_access
def get_active_users(period):
    """
    Get list of active users with their activity metrics
    Restricted to authorized users only
    """
    from azure.data.tables import TableServiceClient
    from telemetry import TABLE_NAMES
    from collections import defaultdict
    
    valid_periods = {'7d': 7, '30d': 30, '90d': 90}
    days = valid_periods.get(period, 7)
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not storage_connection:
            return jsonify([])
        
        table_service = TableServiceClient.from_connection_string(storage_connection)
        user_stats = defaultdict(lambda: {
            'userName': 'Anonymous', 
            'userEmail': '', 
            'logins': 0, 
            'videoViews': 0, 
            'searches': 0, 
            'comments': 0, 
            'downloads': 0,
            'totalEvents': 0,
            'activeDays': set(),
            'lastSeen': None
        })
        
        # Count logins and capture email
        try:
            session_table = table_service.get_table_client(TABLE_NAMES['user_sessions'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}' and EventType eq 'Login'"
            entities = session_table.query_entities(filter_query)
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                user_stats[user_id]['userEmail'] = entity.get('UserEmail', '')
                user_stats[user_id]['logins'] += 1
                user_stats[user_id]['totalEvents'] += 1
                
                # Track active days
                timestamp = entity.get('Timestamp')
                if timestamp:
                    # Ensure timestamp is a datetime object
                    if isinstance(timestamp, str):
                        from dateutil import parser
                        timestamp = parser.parse(timestamp)
                    
                    date_key = timestamp.strftime('%Y-%m-%d')
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None or timestamp > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = timestamp
        except Exception as e:
            print(f"Error querying logins: {e}")
        
        # Count video views
        try:
            watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = watch_table.query_entities(filter_query)
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                user_stats[user_id]['videoViews'] += 1
                user_stats[user_id]['totalEvents'] += 1
                
                # Track active days
                timestamp = entity.get('Timestamp') or entity.get('WatchedAt')
                if timestamp:
                    # Ensure timestamp is a datetime object
                    if isinstance(timestamp, str):
                        from dateutil import parser
                        timestamp = parser.parse(timestamp)
                    
                    date_key = timestamp.strftime('%Y-%m-%d')
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None or timestamp > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = timestamp
        except Exception as e:
            print(f"Error querying video views: {e}")
        
        # Count searches
        try:
            search_table = table_service.get_table_client(TABLE_NAMES['search_logs'])
            filter_query = f"Timestamp ge datetime'{start_time.isoformat()}'"
            entities = search_table.query_entities(filter_query)
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                user_stats[user_id]['searches'] += 1
                user_stats[user_id]['totalEvents'] += 1
                
                # Track active days
                timestamp = entity.get('Timestamp')
                if timestamp:
                    # Ensure timestamp is a datetime object
                    if isinstance(timestamp, str):
                        from dateutil import parser
                        timestamp = parser.parse(timestamp)
                    
                    date_key = timestamp.strftime('%Y-%m-%d')
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None or timestamp > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = timestamp
        except Exception as e:
            print(f"Error querying searches: {e}")
        
        # Count comments
        try:
            comment_table = table_service.get_table_client(TABLE_NAMES['comments'])
            filter_query = f"Timestamp >= datetime'{start_time.isoformat()}'"
            entities = comment_table.query_entities(filter_query)
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                user_stats[user_id]['comments'] += 1
                user_stats[user_id]['totalEvents'] += 1
                
                # Track active days
                timestamp = entity.get('Timestamp')
                if timestamp:
                    # Ensure timestamp is a datetime object
                    if isinstance(timestamp, str):
                        from dateutil import parser
                        timestamp = parser.parse(timestamp)
                    
                    date_key = timestamp.strftime('%Y-%m-%d')
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None or timestamp > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = timestamp
        except Exception as e:
            print(f"Error querying comments: {e}")
        
        # Convert to list
        data = []
        for user_id, stats in user_stats.items():
            last_seen_str = stats['lastSeen'].strftime('%Y-%m-%d %H:%M:%S') if stats['lastSeen'] else 'Unknown'
            
            data.append({
                'userId': user_id,
                'userName': stats['userName'],
                'userEmail': stats['userEmail'] or stats['userName'],
                'logins': stats['logins'],
                'videoViews': stats['videoViews'],
                'searches': stats['searches'],
                'comments': stats['comments'],
                'downloads': stats['downloads'],
                'activeDays': len(stats['activeDays']),
                'totalEvents': stats['totalEvents'],
                'lastSeen': last_seen_str
            })
        
        # Sort by total events
        data.sort(key=lambda x: x['totalEvents'], reverse=True)
        return jsonify(data)  # Return all users (frontend will slice for top users)
        
    except Exception as e:
        print(f"Error fetching active users: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])


@dashboard_bp.route('/api/dashboard/export/<period>')
@require_dashboard_access
def export_dashboard_data(period):
    """
    Export dashboard data to Excel format
    Restricted to authorized users only
    """
    # TODO: Implement Excel export using openpyxl or pandas
    return jsonify({'message': 'Export feature coming soon'}), 501
