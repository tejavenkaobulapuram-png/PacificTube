"""
Dashboard Access Control
Restricts dashboard access to authorized users only
"""

from functools import wraps
from flask import session, redirect, url_for, abort, render_template_string

# Authorized users who can access the dashboard
AUTHORIZED_DASHBOARD_USERS = [
    "hiroki.shibuya@ss.pacific.co.jp",
    "kuruniawanha.girbert@tk.pacific.co.jp",
    "kavya.konakati@tk.pacific.co.jp",
    "tejavenka.obulapuram@tk.pacific.co.jp"
]


def require_dashboard_access(f):
    """
    Decorator to restrict dashboard access to authorized users only
    Checks if user's email is in the AUTHORIZED_DASHBOARD_USERS list
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user info from Entra ID session
        user_info = session.get('user', {})
        user_email = user_info.get('email') or ''
        user_email = user_email.lower() if user_email else ''
        
        # Check if user is authenticated
        if not user_email:
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>アクセス拒否 - Access Denied</title>
                    <style>
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .error-container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                            text-align: center;
                            max-width: 500px;
                        }
                        h1 {
                            color: #dc3545;
                            margin-bottom: 20px;
                        }
                        p {
                            color: #666;
                            line-height: 1.6;
                            margin-bottom: 20px;
                        }
                        .icon {
                            font-size: 64px;
                            margin-bottom: 20px;
                        }
                        a {
                            display: inline-block;
                            background: #007bff;
                            color: white;
                            padding: 12px 30px;
                            text-decoration: none;
                            border-radius: 5px;
                            transition: background 0.3s;
                        }
                        a:hover {
                            background: #0056b3;
                        }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="icon">🔒</div>
                        <h1>アクセス拒否 / Access Denied</h1>
                        <p>ダッシュボードにアクセスするには、ログインが必要です。</p>
                        <p>You need to be logged in to access the dashboard.</p>
                        <a href="/">ホームに戻る / Back to Home</a>
                    </div>
                </body>
                </html>
            '''), 403
        
        # Check if user is authorized to access dashboard
        if user_email not in AUTHORIZED_DASHBOARD_USERS:
            return render_template_string('''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>アクセス権限なし - Unauthorized</title>
                    <style>
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .error-container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                            text-align: center;
                            max-width: 500px;
                        }
                        h1 {
                            color: #dc3545;
                            margin-bottom: 20px;
                        }
                        p {
                            color: #666;
                            line-height: 1.6;
                            margin-bottom: 20px;
                        }
                        .icon {
                            font-size: 64px;
                            margin-bottom: 20px;
                        }
                        .email {
                            background: #f8f9fa;
                            padding: 10px;
                            border-radius: 5px;
                            font-family: monospace;
                            color: #333;
                            margin: 15px 0;
                        }
                        a {
                            display: inline-block;
                            background: #007bff;
                            color: white;
                            padding: 12px 30px;
                            text-decoration: none;
                            border-radius: 5px;
                            transition: background 0.3s;
                        }
                        a:hover {
                            background: #0056b3;
                        }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="icon">⛔</div>
                        <h1>アクセス権限がありません / Unauthorized Access</h1>
                        <p>申し訳ございませんが、このダッシュボードへのアクセス権限がありません。</p>
                        <p>Sorry, you don't have permission to access this dashboard.</p>
                        <div class="email">Your email: ''' + user_email + '''</div>
                        <p style="font-size: 14px; color: #999;">管理者に連絡してアクセス権限をリクエストしてください。<br>Please contact an administrator to request access.</p>
                        <a href="/">ホームに戻る / Back to Home</a>
                    </div>
                </body>
                </html>
            '''), 403
        
        # User is authorized - proceed to the route
        return f(*args, **kwargs)
    
    return decorated_function
