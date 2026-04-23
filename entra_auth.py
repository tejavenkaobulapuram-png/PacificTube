"""
Entra ID (Azure AD) Authentication Module
Handles Microsoft authentication for PacificTube

This module is ready to use - just add credentials from ICT team to .env file:
1. Set ENABLE_ENTRA_ID=True
2. Add ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, ENTRA_TENANT_ID
3. Restart the application
"""

import os
import msal
from flask import session, redirect, url_for, request, jsonify, render_template
from functools import wraps
from datetime import datetime, timedelta
from telemetry import TelemetryTracker


class EntraIDAuth:
    """Entra ID authentication handler"""
    
    def __init__(self, app=None):
        self.app = app
        self.enabled = False
        self.client_id = None
        self.client_secret = None
        self.tenant_id = None
        self.authority = None
        self.redirect_path = None
        self.allowed_groups = []
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Entra ID authentication with Flask app"""
        self.app = app
        
        # Load configuration from environment
        self.enabled = os.getenv('ENABLE_ENTRA_ID', 'False').lower() == 'true'
        self.client_id = os.getenv('ENTRA_CLIENT_ID')
        self.client_secret = os.getenv('ENTRA_CLIENT_SECRET')
        self.tenant_id = os.getenv('ENTRA_TENANT_ID')
        self.authority = os.getenv('ENTRA_AUTHORITY', f'https://login.microsoftonline.com/{self.tenant_id}')
        self.redirect_path = os.getenv('ENTRA_REDIRECT_PATH', '/auth/callback')
        
        # Parse allowed groups
        groups_str = os.getenv('ENTRA_ALLOWED_GROUPS', '')
        self.allowed_groups = [g.strip() for g in groups_str.split(',') if g.strip()]
        
        if self.enabled:
            print(f"✅ Entra ID authentication ENABLED")
            print(f"   - Tenant ID: {self.tenant_id}")
            print(f"   - Client ID: {self.client_id}")
            print(f"   - Authority: {self.authority}")
            print(f"   - Redirect: {self.redirect_path}")
            if self.allowed_groups:
                print(f"   - Restricted to groups: {', '.join(self.allowed_groups)}")
            else:
                print(f"   - All authenticated users allowed")
        else:
            print(f"⚠️  Entra ID authentication DISABLED (set ENABLE_ENTRA_ID=True to enable)")
    
    def is_enabled(self):
        """Check if Entra ID authentication is enabled"""
        return self.enabled
    
    def get_msal_app(self):
        """Create MSAL confidential client application"""
        if not self.enabled:
            return None
        
        return msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
    
    def get_auth_url(self):
        """Get authorization URL for login"""
        if not self.enabled:
            return None
        
        msal_app = self.get_msal_app()
        
        # Scopes to request (only use permissions granted by ICT team)
        scopes = ['User.Read']
        
        # Generate authorization URL
        auth_url = msal_app.get_authorization_request_url(
            scopes=scopes,
            redirect_uri=request.host_url.rstrip('/') + self.redirect_path,
            state=session.get('state', os.urandom(16).hex())
        )
        
        session['state'] = auth_url
        return auth_url
    
    def handle_callback(self, auth_response):
        """Handle authentication callback from Entra ID"""
        if not self.enabled:
            return {'error': 'Entra ID not enabled'}
        
        try:
            msal_app = self.get_msal_app()
            
            # Acquire token from authorization code
            result = msal_app.acquire_token_by_authorization_code(
                auth_response.get('code'),
                scopes=['User.Read'],
                redirect_uri=request.host_url.rstrip('/') + self.redirect_path
            )
            
            if 'error' in result:
                return {
                    'error': result.get('error'),
                    'error_description': result.get('error_description')
                }
            
            # Store user information in session
            session['user'] = {
                'name': result.get('id_token_claims', {}).get('name'),
                'email': result.get('id_token_claims', {}).get('preferred_username'),
                'oid': result.get('id_token_claims', {}).get('oid'),
                'token': result.get('access_token'),
                'logged_in_at': datetime.utcnow().isoformat()
            }
            
            # Track login to Application Insights + Table Storage
            try:
                from telemetry import TelemetryTracker
                user_email = result.get('id_token_claims', {}).get('preferred_username', 'unknown')
                TelemetryTracker.track_user_login(user_email)
            except Exception as track_error:
                # Don't fail login if tracking fails
                print(f"Login tracking failed: {track_error}")
            
            # Check group membership if required
            if self.allowed_groups:
                user_groups = self.get_user_groups(result.get('access_token'))
                if not any(group in user_groups for group in self.allowed_groups):
                    return {
                        'error': 'access_denied',
                        'error_description': 'User is not member of allowed groups'
                    }
            
            return {'success': True, 'user': session['user']}
            
        except Exception as e:
            return {
                'error': 'authentication_failed',
                'error_description': str(e)
            }
    
    def get_user_groups(self, access_token):
        """Get user's group memberships from Microsoft Graph API"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/memberOf',
                headers=headers
            )
            response.raise_for_status()
            
            groups = response.json().get('value', [])
            return [group.get('displayName') for group in groups]
        except:
            return []
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        if not self.enabled:
            return True  # If auth is disabled, all users are "authenticated"
        
        return 'user' in session and session['user'] is not None
    
    def get_current_user(self):
        """Get currently authenticated user"""
        if not self.enabled:
            return {'name': 'Guest', 'email': 'guest@localhost'}
        
        return session.get('user')
    
    def logout(self):
        """Logout current user"""
        session.clear()
        
        if self.enabled:
            # Redirect to Microsoft logout
            logout_url = f"{self.authority}/oauth2/v2.0/logout" + \
                        f"?post_logout_redirect_uri={request.host_url}"
            return logout_url
        
        return url_for('index')
    
    def require_auth(self, f):
        """Decorator to require authentication for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.is_authenticated():
                # Store the original URL
                session['next_url'] = request.url
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function


def setup_auth_routes(app, auth):
    """Setup authentication routes"""
    
    @app.route('/login')
    def login():
        """Login route - redirects to Entra ID"""
        if not auth.is_enabled():
            return jsonify({
                'error': 'Entra ID not enabled',
                'message': 'Authentication is currently disabled. Contact administrator.'
            }), 501
        
        auth_url = auth.get_auth_url()
        return redirect(auth_url)
    
    @app.route('/auth/callback')
    def auth_callback():
        """Callback route for Entra ID authentication"""
        if not auth.is_enabled():
            return redirect(url_for('index'))
        
        # Handle authentication response
        result = auth.handle_callback(request.args)
        
        if 'error' in result:
            # Show friendly error page instead of JSON
            error_messages = {
                'access_denied': 'アプリケーションへのアクセス権限がありません。管理者にアクセス権限を申請してください。',
                'invalid_grant': '認証セッションが期限切れです。もう一度ログインしてください。',
                'invalid_request': 'リクエストが無効です。もう一度お試しください。',
                'unauthorized_client': 'アプリケーションの設定に問題があります。管理者にお問い合わせください。',
                'unsupported_response_type': 'サポートされていない認証方式です。',
                'invalid_scope': '要求されたスコープが無効です。',
                'authentication_failed': '認証に失敗しました。もう一度お試しください。',
                'redirect_uri_mismatch': 'リダイレクトURIが登録されていません。管理者にICT部門への登録依頼をお願いしてください。'
            }
            
            error_type = result.get('error', 'unknown')
            error_description = result.get('error_description') or error_messages.get(error_type, '予期しないエラーが発生しました。')
            
            return render_template('auth_error.html', 
                                 error_type=error_type,
                                 error_description=error_description), 401
        
        # Track successful login to Application Insights + Table Storage
        try:
            TelemetryTracker.track_user_login('EntraID')
        except Exception as e:
            print(f"Login tracking failed (non-critical): {e}")
        
        # Redirect to original URL or home
        next_url = session.pop('next_url', url_for('index'))
        return redirect(next_url)
    
    @app.route('/logout')
    def logout():
        """Logout route"""
        # Track logout to Application Insights + Table Storage
        try:
            TelemetryTracker.track_user_logout()
        except Exception as e:
            print(f"Logout tracking failed (non-critical): {e}")
        
        logout_url = auth.logout()
        return redirect(logout_url)
    
    @app.route('/api/user')
    def get_user():
        """Get current user information"""
        if not auth.is_enabled():
            # Auth not enabled - return not authenticated but not an error
            return jsonify({'authenticated': False, 'auth_enabled': False}), 200
        
        if not auth.is_authenticated():
            # Auth enabled but user not logged in
            return jsonify({'authenticated': False, 'auth_enabled': True}), 200
        
        user = auth.get_current_user()
        return jsonify({
            'authenticated': True,
            'auth_enabled': True,
            'user': {
                'name': user.get('name'),
                'email': user.get('email')
            }
        })
