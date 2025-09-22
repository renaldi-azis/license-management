import datetime
from flask import Flask, redirect, render_template, url_for
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from api import auth, licenses, products , validation
from models.database import init_db
from services.rate_limiter import init_limiter
from services.security import init_recaptcha

limiter = Limiter(
    get_remote_address,
    app=None,  # Will be set later
    default_limits=["10 per minute"]  # Example: 10 requests per minute per IP
)

def create_app():
    app = Flask(__name__)
    limiter.init_app(app)
    app.config.from_object(Config)
    
    # Register error handlers first
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Endpoint not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return {"error": "Internal server error"}, 500
    
    # Initialize extensions (in correct order)
    jwt = JWTManager(app)
    
    # Initialize database
    with app.app_context():
        init_db()
    
    # Initialize rate limiter (requires app context)
    init_limiter(app)
    
    # Initialize reCAPTCHA
    init_recaptcha(app)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        try:
            # Test database
            with app.app_context():
                from models.database import get_db_connection
                with get_db_connection() as conn:
                    conn.execute("SELECT 1")
            
            # Test Redis (if available)
            from services.rate_limiter import redis_client
            redis_status = "connected" if redis_client and redis_client.ping() else "unavailable"
            
            return {
                'status': 'healthy',
                'timestamp': app.config.get('TESTING', False) and "test" or str(datetime.utcnow()),
                'database': 'connected',
                'redis': redis_status,
                'version': '1.2.0'
            }
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}, 503
    
    # Register blueprints
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(licenses.bp, url_prefix='/api/licenses')
    app.register_blueprint(products.bp, url_prefix='/api/products')
    app.register_blueprint(validation.bp, url_prefix='/api/validate')  # For web routes
    
    # Simple routes
    @app.route('/')
    def index():
        try:
            verify_jwt_in_request(optional=True)
            if get_jwt_identity() == 'admin':
                return redirect(url_for('admin'))
        except Exception:
            pass

        try:
            verify_jwt_in_request(optional=True)
            user = get_jwt_identity()
        except Exception:
            user = None
        if user:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('login'))
    
    @app.route('/admin')
    def admin():
        return render_template('admin.html')
    
    @app.route('/admin/licenses')
    def admin_licenses():
        return render_template('licenses.html')

    @app.route('/admin/products')
    def admin_products():
        return render_template('products.html')
    
    @app.route('/admin/users')
    def admin_users():
        return render_template('users.html')

    @app.route('/admin/settings')
    def admin_settings():
        return render_template('settings.html')
    
    @app.route('/login')
    def login():
        return render_template('login.html')
    
    # Global error handler for rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {
            'error': 'Rate limit exceeded',
            'retry_after': getattr(e, 'retry_after', 60)
        }, 429
    
    @app.context_processor
    def inject_current_user():
        try:
            verify_jwt_in_request(optional=True)
            user = get_jwt_identity()
            # get user info from db by username
            from models.database import get_db_connection
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT username, first_name, last_name, role FROM users WHERE username = ?', (user,))
                row = c.fetchone()
                if row:
                    user = {
                        'username': row[0],
                        'first_name': row[1],
                        'last_name': row[2],
                        'role': row[3]
                    }
                else:
                    user = None
        except Exception:
            user = None
        return dict(current_user=user)
    
    return app

# Create and run app
app = create_app()

if __name__ == '__main__':
    # Ensure app context for initialization
    with app.app_context():
        # Final initialization that needs app context
        pass
    
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)