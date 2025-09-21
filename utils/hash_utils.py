import hashlib
import secrets
import base64

def hash_license_key(license_key):
    """Create a SHA-256 hash of the license key for secure storage."""
    return hashlib.sha256(license_key.encode('utf-8')).hexdigest()

def generate_license_key(length=16):
    """Generate a random license key."""
    # Generate random bytes and encode to base62 (0-9, A-Z, a-z)
    random_bytes = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')[:length]

def validate_license_format(license_key):
    """Validate license key format."""
    # Basic format: alphanumeric, 16-32 characters
    import re
    pattern = r'^[A-Za-z0-9]{16,32}$'
    return bool(re.match(pattern, license_key))

def create_license_signature(license_key, product_id, user_id):
    """Create a digital signature for license verification."""
    import hmac
    from config import Config
    
    message = f"{license_key}:{product_id}:{user_id}"
    signature = hmac.new(
        Config.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature