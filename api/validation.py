from flask import Blueprint, request, jsonify
from datetime import datetime

from models.database import get_db_connection
from services.license_service import validate_license
from services.rate_limiter import rate_limited, suspicious_activity_check, redis_client

bp = Blueprint('validation', __name__)

@bp.route('/', methods=['POST'])
@rate_limited(limit='30 per minute')  # Limit validation requests
def validate_license_route():
    """Validate license with safety checks."""
    try:
        ip = request.remote_addr
        data = request.data
        license_key = data['license_key']
        product_name = data['product_name']
        machine_code = data['machine_code']
        
        # Safe suspicious activity check
        if suspicious_activity_check(ip):
            return jsonify({
                'valid': False,
                'error': 'Too many requests from this IP. Please try again later.',
                'error_code': 'RATE_LIMITED'
            }), 429
    
        # Perform validation
        result = validate_license(product_name, license_key, machine_code)
    
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