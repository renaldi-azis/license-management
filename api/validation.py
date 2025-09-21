from flask import Blueprint, request, jsonify
from flask_limiter import Limiter

from models.database import get_db_connection
from services.license_service import validate_license
from services.rate_limiter import suspicious_activity_check
from utils.hash_utils import hash_license_key
from utils.validators import validate_license_key

bp = Blueprint('validation', __name__, url_prefix='/validate')

@bp.route('/<product_name>/<license_key>', methods=['GET'])
@validate_license_key
def validate_license_route(product_name, license_key):
    ip = request.remote_addr
    
    # Check for suspicious activity
    if suspicious_activity_check(ip):
        return jsonify({
            'valid': False,
            'error': 'Too many requests from this IP. Please try again later.'
        }), 429
    
    # Validate license
    result = validate_license(product_name, license_key, ip)
    
    if result['valid']:
        return jsonify(result), 200
    return jsonify(result), 400