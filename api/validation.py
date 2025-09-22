from flask import Blueprint, request, jsonify
from datetime import datetime

from models.database import get_db_connection
from services.license_service import validate_license
from services.rate_limiter import suspicious_activity_check, redis_client
from utils.hash_utils import hash_license_key
from utils.validators import validate_license_key

bp = Blueprint('validation', __name__)

@bp.route('/<product_name>/<license_key>', methods=['GET'])
@validate_license_key
def validate_license_route(product_name, license_key):
    """Validate license with safety checks."""
    try:
        ip = request.remote_addr
    
        # Safe suspicious activity check
        # if suspicious_activity_check(ip):
        #     return jsonify({
        #         'valid': False,
        #         'error': 'Too many requests from this IP. Please try again later.',
        #         'error_code': 'RATE_LIMITED'
        #     }), 429
    
        # Perform validation
        result = validate_license(product_name, license_key, ip)
    
        return jsonify(result), 200 if result.get('valid') else 400
        
    except Exception as e:
        # Log error but don't expose details
        if hasattr(bp, 'logger'):
            bp.logger.error(f"Validation error for {product_name}/{license_key}: {e}")
       
        return jsonify({
            'valid': False,
            'error': 'Validation service temporarily unavailable',
            'error_code': 'SERVICE_UNAVAILABLE'
        }), 503