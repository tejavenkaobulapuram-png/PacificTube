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
            # Query all logins
            entities = list(session_table.query_entities("EventType eq 'Login'"))
            print(f"DEBUG: Found {len(entities)} login entities, period={period}, start_time={start_time}")
            
            counted_logins = 0
            skipped_logins = 0
            
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                
                # Always capture user basic info
                user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                user_stats[user_id]['userEmail'] = entity.get('UserEmail', '')
                
                # Get timestamp
                timestamp = entity.get('Timestamp')
                if not timestamp:
                    print(f"DEBUG: Login entity has no timestamp")
                    continue
                
                # Ensure timestamp is a datetime object
                if isinstance(timestamp, str):
                    from dateutil import parser
                    timestamp = parser.parse(timestamp)
                
                print(f"DEBUG: Login timestamp type: {type(timestamp)}, value: {timestamp}")
                
                # VERY simple comparison - if after 90 days ago, count it
                # For 90d period, we're very generous
                try:
                    # Count everything for now to debug
                    user_stats[user_id]['logins'] += 1
                    user_stats[user_id]['totalEvents'] += 1
                    counted_logins += 1
                    
                    # Track active days
                    date_key = str(timestamp)[:10]  # Simple YYYY-MM-DD extraction
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None:
                        user_stats[user_id]['lastSeen'] = timestamp
                    elif timestamp > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = timestamp
                        
                except Exception as e:
                    print(f"DEBUG: Error counting login: {e}")
                    import traceback
                    traceback.print_exc()
                    
            print(f"DEBUG: Counted {counted_logins} logins, skipped {skipped_logins}")
            
        except Exception as e:
            print(f"Error querying logins: {e}")
            import traceback
            traceback.print_exc()
        
        # Count video views
        try:
            watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
            # Query all watch history
            entities = list(watch_table.query_entities(""))
            print(f"DEBUG: Found {len(entities)} watch_history entities")
            
            counted_views = 0
            
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                
                # Always capture user basic info
                if user_stats[user_id]['userName'] == 'Anonymous':
                    user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                
                # Get timestamp
                watched_at = entity.get('WatchedAt') or entity.get('Timestamp')
                if not watched_at:
                    print(f"DEBUG: Watch entity has no timestamp")
                    continue
                
                # Ensure timestamp is a datetime object
                if isinstance(watched_at, str):
                    from dateutil import parser
                    watched_at = parser.parse(watched_at)
                
                print(f"DEBUG: Video view timestamp type: {type(watched_at)}, value: {watched_at}")
                
                # Count everything for now to debug
                try:
                    user_stats[user_id]['videoViews'] += 1
                    user_stats[user_id]['totalEvents'] += 1
                    counted_views += 1
                    
                    # Track active days
                    date_key = str(watched_at)[:10]
                    user_stats[user_id]['activeDays'].add(date_key)
                    
                    # Update last seen
                    if user_stats[user_id]['lastSeen'] is None:
                        user_stats[user_id]['lastSeen'] = watched_at
                    elif watched_at > user_stats[user_id]['lastSeen']:
                        user_stats[user_id]['lastSeen'] = watched_at
                        
                except Exception as e:
                    print(f"DEBUG: Error counting video view: {e}")
                    import traceback
                    traceback.print_exc()
                    
            print(f"DEBUG: Counted {counted_views} video views")
            
        except Exception as e:
            print(f"Error querying video views: {e}")
            import traceback
            traceback.print_exc()
        
        # Count searches
        try:
            search_table = table_service.get_table_client(TABLE_NAMES['search_logs'])
            entities = list(search_table.query_entities(""))
            print(f"DEBUG: Found {len(entities)} search_logs entities")
            
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                
                # Always capture user basic info
                if user_stats[user_id]['userName'] == 'Anonymous':
                    user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                
                timestamp = entity.get('Timestamp')
                if not timestamp:
                    continue
                
                # Ensure timestamp is a datetime object
                if isinstance(timestamp, str):
                    from dateutil import parser
                    timestamp = parser.parse(timestamp)
                
                # Simple datetime comparison
                try:
                    ts_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
                    start_naive = start_time.replace(tzinfo=None)
                    
                    if ts_naive >= start_naive:
                        user_stats[user_id]['searches'] += 1
                        user_stats[user_id]['totalEvents'] += 1
                        
                        # Track active days
                        date_key = timestamp.strftime('%Y-%m-%d')
                        user_stats[user_id]['activeDays'].add(date_key)
                except Exception as e:
                    print(f"DEBUG: Error in date comparison for search: {e}, counting anyway")
                    user_stats[user_id]['searches'] += 1
                    user_stats[user_id]['totalEvents'] += 1
                
                # Update last seen regardless of period
                current_last_seen = user_stats[user_id]['lastSeen']
                if current_last_seen is None:
                    user_stats[user_id]['lastSeen'] = timestamp
                else:
                    try:
                        ts_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
                        current_naive = current_last_seen.replace(tzinfo=None) if current_last_seen.tzinfo else current_last_seen
                        if ts_naive > current_naive:
                            user_stats[user_id]['lastSeen'] = timestamp
                    except:
                        pass
        except Exception as e:
            print(f"Error querying searches: {e}")
            import traceback
            traceback.print_exc()
        
        # Count comments
        try:
            comment_table = table_service.get_table_client(TABLE_NAMES['comments'])
            entities = list(comment_table.query_entities(""))
            print(f"DEBUG: Found {len(entities)} comments entities")
            
            for entity in entities:
                user_id = entity.get('UserId', 'unknown')
                
                # Always capture user basic info
                if user_stats[user_id]['userName'] == 'Anonymous':
                    user_stats[user_id]['userName'] = entity.get('UserName', 'Anonymous')
                
                timestamp = entity.get('Timestamp')
                if not timestamp:
                    continue
                
                # Ensure timestamp is a datetime object
                if isinstance(timestamp, str):
                    from dateutil import parser
                    timestamp = parser.parse(timestamp)
                
                # Simple datetime comparison
                try:
                    ts_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
                    start_naive = start_time.replace(tzinfo=None)
                    
                    if ts_naive >= start_naive:
                        user_stats[user_id]['comments'] += 1
                        user_stats[user_id]['totalEvents'] += 1
                        
                        # Track active days
                        date_key = timestamp.strftime('%Y-%m-%d')
                        user_stats[user_id]['activeDays'].add(date_key)
                except Exception as e:
                    print(f"DEBUG: Error in date comparison for comment: {e}, counting anyway")
                    user_stats[user_id]['comments'] += 1
                    user_stats[user_id]['totalEvents'] += 1
                
                # Update last seen regardless of period
                current_last_seen = user_stats[user_id]['lastSeen']
                if current_last_seen is None:
                    user_stats[user_id]['lastSeen'] = timestamp
                else:
                    try:
                        ts_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
                        current_naive = current_last_seen.replace(tzinfo=None) if current_last_seen.tzinfo else current_last_seen
                        if ts_naive > current_naive:
                            user_stats[user_id]['lastSeen'] = timestamp
                    except:
                        pass
        except Exception as e:
            print(f"Error querying comments: {e}")
            import traceback
            traceback.print_exc()
        
        # Convert to list
        data = []
        for user_id, stats in user_stats.items():
            # Get the actual last seen by querying most recent activity across all tables (without time filter)
            last_seen_timestamp = None
            
            def compare_and_update_timestamp(ts, current_last):
                """Helper to safely compare timestamps with timezone handling"""
                if ts is None:
                    return current_last
                if isinstance(ts, str):
                    from dateutil import parser
                    ts = parser.parse(ts)
                
                if current_last is None:
                    return ts
                
                # Make both timezone-naive for comparison
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                current_naive = current_last.replace(tzinfo=None) if current_last.tzinfo else current_last
                
                return ts if ts_naive > current_naive else current_last
            
            # Check user_sessions for latest login
            try:
                session_table = table_service.get_table_client(TABLE_NAMES['user_sessions'])
                filter_query = f"PartitionKey eq '{user_id}'"
                entities = list(session_table.query_entities(filter_query, select=['Timestamp']))
                for entity in entities:
                    ts = entity.get('Timestamp')
                    last_seen_timestamp = compare_and_update_timestamp(ts, last_seen_timestamp)
            except Exception as e:
                print(f"Error getting last seen from sessions for {user_id}: {e}")
            
            # Check watch_history for latest video view
            try:
                watch_table = table_service.get_table_client(TABLE_NAMES['watch_history'])
                filter_query = f"PartitionKey eq '{user_id}'"
                entities = list(watch_table.query_entities(filter_query, select=['Timestamp', 'WatchedAt']))
                for entity in entities:
                    ts = entity.get('WatchedAt') or entity.get('Timestamp')
                    last_seen_timestamp = compare_and_update_timestamp(ts, last_seen_timestamp)
            except Exception as e:
                print(f"Error getting last seen from watch_history for {user_id}: {e}")
            
            # Check search_logs for latest search
            try:
                search_table = table_service.get_table_client(TABLE_NAMES['search_logs'])
                filter_query = f"PartitionKey eq '{user_id}'"
                entities = list(search_table.query_entities(filter_query, select=['Timestamp']))
                for entity in entities:
                    ts = entity.get('Timestamp')
                    last_seen_timestamp = compare_and_update_timestamp(ts, last_seen_timestamp)
            except Exception as e:
                print(f"Error getting last seen from search_logs for {user_id}: {e}")
            
            # Format lastSeen - use the timestamp we found or fallback to stats
            final_last_seen = last_seen_timestamp if last_seen_timestamp else stats['lastSeen']
            
            if final_last_seen:
                if isinstance(final_last_seen, str):
                    from dateutil import parser
                    final_last_seen = parser.parse(final_last_seen)
                last_seen_str = final_last_seen.strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_seen_str = 'Unknown'
            
            # Always include the user in the results
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
        
        print(f"DEBUG: Returning {len(data)} users")
        if data:
            print(f"DEBUG: Sample user data: {data[0]}")
        
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
