from flask_recaptcha import ReCaptcha
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

recaptcha = None

def init_recaptcha(app):
    """Initialize reCAPTCHA if keys are provided."""
    global recaptcha
    if Config.RECAPTCHA_SITE_KEY and Config.RECAPTCHA_SECRET_KEY:
        recaptcha = ReCaptcha(app)

def verify_admin_credentials(username, password):
    """Verify admin credentials."""
    # In production, this should check against database
    # For now, using environment variables
    if (username == Config.ADMIN_USERNAME and 
        check_password_hash(generate_password_hash(Config.ADMIN_PASSWORD), password)):
        return True
    return False

def hash_password(password):
    """Hash a password for storage."""
    return generate_password_hash(password)

def generate_secure_token():
    """Generate a secure random token."""
    import secrets
    return secrets.token_urlsafe(32)

def validate_jwt_token(token):
    """Validate JWT token (placeholder for custom validation)."""
    from flask_jwt_extended import decode_token, PyJWTError
    try:
        decode_token(token, current_app.config['JWT_SECRET_KEY'])
        return True
    except PyJWTError:
        return False