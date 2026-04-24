"""
Feedback Management Module
Handles user feedback submission and management
"""

from flask import Blueprint, request, jsonify, session, render_template
from datetime import datetime, timezone
import uuid
import logging
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError
import os

feedback_bp = Blueprint('feedback', __name__)
logger = logging.getLogger(__name__)

# Azure Table Storage configuration
STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
FEEDBACK_TABLE_NAME = 'UserFeedback'

@feedback_bp.route('/feedback-management')
def feedback_management_page():
    """Feedback management page"""
    return render_template('feedback_management.html')

def get_table_client():
    """Get Azure Table Storage client for feedback table"""
    try:
        table_service = TableServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
        table_client = table_service.get_table_client(FEEDBACK_TABLE_NAME)
        return table_client
    except Exception as e:
        logger.error(f"Failed to get table client: {e}")
        return None

def create_feedback_table():
    """Create feedback table if it doesn't exist"""
    try:
        table_service = TableServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
        table_service.create_table(FEEDBACK_TABLE_NAME)
        logger.info(f"Created table: {FEEDBACK_TABLE_NAME}")
    except ResourceExistsError:
        logger.info(f"Table already exists: {FEEDBACK_TABLE_NAME}")
    except Exception as e:
        logger.error(f"Error creating feedback table: {e}")

@feedback_bp.route('/api/feedback/submit', methods=['POST'])
def submit_feedback():
    """Submit new feedback"""
    try:
        data = request.json
        
        # Get user information from session (supports both Entra ID and regular session)
        user_info = session.get('user', {})
        if user_info:
            # Entra ID authenticated user
            user_id = user_info.get('oid', 'anonymous')
            user_name = user_info.get('name', 'Anonymous User')
            user_email = user_info.get('email', '')
        else:
            # Fallback to regular session keys
            user_id = session.get('user_id', 'anonymous')
            user_name = session.get('user_name', 'Anonymous User')
            user_email = session.get('user_email', '')
        
        # Generate unique ID
        feedback_id = f"{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        # Partition key: date for efficient querying
        partition_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Prepare feedback entity
        feedback_entity = {
            'PartitionKey': partition_key,
            'RowKey': feedback_id,
            'userId': user_id,
            'userName': user_name,
            'userEmail': user_email,
            'rating': int(data.get('rating', 0)),
            'category': data.get('category', 'その他'),
            'importance': data.get('importance', '中'),
            'feedbackText': data.get('feedbackText', ''),
            'overallRating': data.get('overallRating', 'neutral'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'new'
        }
        
        # Save to Table Storage
        table_client = get_table_client()
        if table_client:
            table_client.create_entity(feedback_entity)
            logger.info(f"Feedback submitted by {user_name} ({user_id})")
            
            return jsonify({
                'success': True,
                'message': 'フィードバックを送信しました',
                'feedbackId': feedback_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'テーブルストレージに接続できません'
            }), 500
            
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({
            'success': False,
            'message': f'エラーが発生しました: {str(e)}'
        }), 500

@feedback_bp.route('/api/feedback/list', methods=['GET'])
def list_feedback():
    """Get all feedback entries"""
    try:
        table_client = get_table_client()
        if not table_client:
            return jsonify({'success': False, 'message': 'Table storage unavailable'}), 500
        
        # Query all feedback, ordered by timestamp descending
        entities = table_client.query_entities("")
        
        feedback_list = []
        for entity in entities:
            feedback_list.append({
                'id': entity['RowKey'],
                'date': entity['PartitionKey'],
                'userId': entity.get('userId', 'unknown'),
                'userName': entity.get('userName', 'Unknown'),
                'userEmail': entity.get('userEmail', ''),
                'rating': entity.get('rating', 0),
                'category': entity.get('category', 'その他'),
                'importance': entity.get('importance', '中'),
                'feedbackText': entity.get('feedbackText', ''),
                'overallRating': entity.get('overallRating', 'neutral'),
                'timestamp': entity.get('timestamp', ''),
                'status': entity.get('status', 'new'),
                'adminMemo': entity.get('adminMemo', '')
            })
        
        # Sort by timestamp descending (newest first)
        feedback_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'feedback': feedback_list,
            'count': len(feedback_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing feedback: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@feedback_bp.route('/api/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics"""
    try:
        table_client = get_table_client()
        if not table_client:
            return jsonify({'success': False, 'message': 'Table storage unavailable'}), 500
        
        entities = list(table_client.query_entities(""))
        
        # Calculate statistics
        total_count = len(entities)
        
        # Count by category
        category_counts = {}
        importance_counts = {}
        overall_rating_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        status_counts = {'new': 0, 'reviewed': 0, 'resolved': 0}
        rating_sum = 0
        rating_count = 0
        detailed_count = 0
        
        # Trend data: count by date
        date_counts = {}
        
        for entity in entities:
            # Category counts
            category = entity.get('category', 'その他')
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Importance counts
            importance = entity.get('importance', '中')
            importance_counts[importance] = importance_counts.get(importance, 0) + 1
            
            # Overall rating counts
            overall = entity.get('overallRating', 'neutral')
            overall_rating_counts[overall] = overall_rating_counts.get(overall, 0) + 1
            
            # Status counts
            status = entity.get('status', 'new')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Average rating
            rating = entity.get('rating', 0)
            if rating > 0:
                rating_sum += rating
                rating_count += 1
            
            # Detailed feedback count (feedback with substantial text or admin memo)
            feedback_text = entity.get('feedbackText', '')
            admin_memo = entity.get('adminMemo', '')
            if len(feedback_text) > 50 or admin_memo:
                detailed_count += 1
            
            # Date counts for trend
            date = entity.get('PartitionKey', '')
            if date:
                date_counts[date] = date_counts.get(date, 0) + 1
        
        # Calculate average rating
        average_rating = round(rating_sum / rating_count, 2) if rating_count > 0 else 0
        
        # Sort trend data by date
        trend_data = [{'date': date, 'count': count} for date, count in date_counts.items()]
        trend_data.sort(key=lambda x: x['date'])
        
        return jsonify({
            'success': True,
            'stats': {
                'totalCount': total_count,
                'averageRating': average_rating,
                'categoryBreakdown': category_counts,
                'importanceBreakdown': importance_counts,
                'overallRatingBreakdown': overall_rating_counts,
                'statusBreakdown': status_counts,
                'detailedCount': detailed_count,
                'trendData': trend_data
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@feedback_bp.route('/api/feedback/update-status', methods=['POST'])
def update_feedback_status():
    """Update feedback status and admin memo"""
    try:
        data = request.json
        feedback_id = data.get('feedbackId')
        new_status = data.get('status', 'reviewed')
        admin_memo = data.get('adminMemo', '')
        partition_key = data.get('partitionKey')
        
        if not feedback_id or not partition_key:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        table_client = get_table_client()
        if not table_client:
            return jsonify({'success': False, 'message': 'Table storage unavailable'}), 500
        
        # Get existing entity
        entity = table_client.get_entity(partition_key, feedback_id)
        entity['status'] = new_status
        entity['adminMemo'] = admin_memo
        
        # Update entity using UpdateMode.REPLACE
        from azure.data.tables import UpdateMode
        table_client.update_entity(entity, mode=UpdateMode.REPLACE)
        
        return jsonify({
            'success': True,
            'message': 'ステータスを更新しました'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating feedback status: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
