import base64
import datetime
import json
from flask import Flask, redirect, request, jsonify, render_template, url_for
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask import Request

from config import Config
from api import auth, licenses, products , validation, settings
from models.database import init_db
from services.rate_limiter import limiter
from services.rate_limiter import redis_client
from services.rate_limiter import suspicious_activity_check

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from api.security import session_manager, crypto_manager

class FlexibleJSONRequest(Request):
    def get_json(self, force=False, silent=False, cache=True):
        """
        Override get_json to be more flexible about Content-Type
        """
        # First try the parent method (standard JSON parsing)
        result = super().get_json(force=force, silent=silent, cache=cache)
        if result is not None:
            return result
        
        # If standard method failed, try our flexible parsing
        try:
            # Try raw data
            if self.get_data():
                data = self.get_data(as_text=True)
                if data.strip():
                    return json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        
        # Try form data
        if self.form:
            data = {}
            for key, value in self.form.items():
                if isinstance(value, list) and len(value) == 1:
                    data[key] = value[0]
                else:
                    data[key] = value
            return data
        
        return None

def create_app():
    app = Flask(__name__)
    app.request_class = FlexibleJSONRequest
    
    app.config.from_object(Config)
    limiter.init_app(app)

    # Register error handlers first
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Endpoint not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return {"error": "Internal server error"}, 500
    
    # Initialize extensions (in correct order)
    app.config['JWT_SECRET_KEY'] = 'your-secret-key'
    app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']  # Accept both
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
    app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disable for API, enable for web
    app.config['JWT_COOKIE_SAMESITE'] = 'None'  # Required for cross-origin
    jwt = JWTManager(app)
    
    CORS(app, 
     supports_credentials=True,
     origins=["http://localhost:3000", "https://richtoolsquantri.online"],  # Add your domains
     allow_headers=["Content-Type", "Authorization", "X-Client-ID", "X-Session-ID"],
     methods=["GET", "POST", "PUT", "DELETE"])

    # Initialize database
    with app.app_context():
        init_db()

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
    app.register_blueprint(validation.bp, url_prefix='/api/validate')
    app.register_blueprint(settings.bp, url_prefix='/api/settings')
    
    # Simple routes
    @app.route('/')
    def index():
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
    
    @app.route('/init-session', methods=['GET'])
    def initialize_session():
        """Initialize new session and start key exchange"""
        client_id = request.headers.get('X-Client-ID', 'unknown')
        session_id = session_manager.create_session(client_id)
        session_data = session_manager.get_session(session_id)
        
        # Get server public key for key exchange
        server_public_key = session_data['server_private_key'].public_key()
        server_public_pem = server_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return jsonify({
            'ok': True,
            'session_id': session_id,
            'server_public_key': server_public_pem.decode('utf-8'),
            'status': 'session_created'
        })
    
    @app.after_request
    def encrypt_response(response):
        """Encrypt JSON responses if session and AES key are established"""
        if(request.endpoint == 'auth.login' or request.endpoint == 'auth.register' or request.endpoint == 'licenses.backup_licenses'):
            return response
        if (response.content_type == 'application/json' or not request.endpoint in ['/', '/api/auth/login', '/api/auth/register', 'auth.login', 'auth.register']) and response.status_code == 200:
            try:                
                session_id = request.headers.get('X-Session-ID')                
                if session_id:
                    current_session = session_manager.get_session(session_id)
                    if current_session and 'aes_key' in current_session:
                        # Encrypt response data
                        original_data = response.get_data(as_text=True)
                        encrypted_data = crypto_manager.aes_encrypt(
                            current_session['aes_key'],
                            json.dumps(original_data)
                        )
                        # Encode to base64 to make it JSON serializable
                        b64_encrypted = base64.b64encode(json.dumps(encrypted_data).encode('utf-8')).decode('utf-8')
                        
                        # Replace response data with encrypted data
                        return jsonify({
                            'encrypted_data': b64_encrypted,  # Wrap in an object
                            'status': 'encrypted'
                        })
            except Exception as e:
                app.logger.error(f"Response encryption failed: {e}")
                # In case of error, return original response unmodified
                pass
        return response
                
    @app.before_request
    def decrypt_request():
        """Decrypt incoming JSON requests if session and AES key are established"""
        if request.endpoint in ['/', '/api/auth/login', '/api/auth/register', 'auth.login', 'auth.register']:
            return  # Skip decryption for these endpoints
        if request.method in ['POST'] and request.is_json:
            try:
                session_id = request.headers.get('X-Session-ID')
                if session_id:
                    current_session = session_manager.get_session(session_id)
                    if current_session and 'aes_key' in current_session:
                        encrypted_payload = request.get_json()
                        if 'encryptedRequest' in encrypted_payload:
                            encrypted_data = encrypted_payload['encryptedRequest']
                            # Decrypt the data
                            decrypted_json = crypto_manager.aes_decrypt(
                                current_session['aes_key'],
                                encrypted_data
                            )
                            # Replace request.json with decrypted data
                            request.data = json.loads(decrypted_json)
            except Exception as e:
                app.logger.error(f"Request decryption failed: {e}")
                return jsonify({'error': 'Invalid encrypted data'}), 400

    @app.route('/get-session/<string:sessionId>')
    def get_session_info(sessionId):
        session_id = sessionId
        session_data = session_manager.get_session(session_id)
        
        # Get server public key for key exchange
        server_public_key = session_data['server_private_key'].public_key()
        server_public_pem = server_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return jsonify({
            'session_id': session_id,
            'server_public_key': server_public_pem.decode('utf-8'),
            'status': 'get_session'
        })



    @app.route('/key-exchange', methods=['POST'])
    def key_exchange():
        """Complete key exchange with client"""
        data = request.get_json()
        session_id = data.get('session_id')
        encrypted_aes_key = data.get('encrypted_aes_key')
        client_public_key_pem = data.get('client_public_key')
        
        if not all([session_id, encrypted_aes_key, client_public_key_pem]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        current_session = session_manager.get_session(session_id)
        if not current_session:
            return jsonify({'error': 'Invalid session'}), 401
        
        try:
            # Load client public key
            client_public_key = serialization.load_pem_public_key(
                client_public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Decrypt AES key with server private key
            encrypted_key_bytes = base64.b64decode(encrypted_aes_key)
            aes_key = crypto_manager.rsa_decrypt(
                current_session['server_private_key'],
                encrypted_key_bytes
            )
            
            # Store keys in session
            current_session['aes_key'] = aes_key
            current_session['client_public_key'] = client_public_key

            # log current_session
            
            return jsonify({'status': 'key_exchange_complete'})
            
        except Exception as e:
            return jsonify({'error': f'Key exchange failed: {str(e)}'}), 400


    # Global error handler for rate limiting
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {
            'error': 'Rate limit exceeded',
            'retry_after': getattr(e, 'retry_after', 60)
        }, 429
    
    # Check ip suspicious activity
    @app.before_request
    def check_suspicious_activity():        
        ip = get_remote_address()
        if suspicious_activity_check(ip):
            return {
                'error': 'Too many requests from this IP. Please try again later.',
                'retry_after': 3600
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