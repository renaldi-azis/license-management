import hashlib
import secrets
import base64
import string
import re

def hash_license_key(license_key):
    """Create a SHA-256 hash of the license key for secure storage."""
    return hashlib.sha256(license_key.encode('utf-8')).hexdigest()

def hash_machine_code(machine_code):
    """Create a SHA-256 hash of the machine code for secure storage."""
    return hashlib.sha256(machine_code.encode('utf-8')).hexdigest()

def generate_license_key(length=16):
    """Generate a random alphanumeric license key."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def validate_license_format(license_key):
    """Validate license key format."""
    # Basic format: alphanumeric, 16-32 characters    
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