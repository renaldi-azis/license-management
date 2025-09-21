from flask import request, jsonify
from functools import wraps
from werkzeug.exceptions import BadRequest

def validate_json(schema):
    """Decorator to validate JSON request body against schema."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    raise BadRequest('Request must be JSON')
                
                # Validate required fields
                for field, field_type in schema.items():
                    if field not in data:
                        raise BadRequest(f'Missing required field: {field}')
                    
                    value = data[field]
                    if field_type == str and not isinstance(value, str):
                        raise BadRequest(f'Field {field} must be string')
                    elif field_type == int and not isinstance(value, int):
                        raise BadRequest(f'Field {field} must be integer')
                
                # Add validated data to request for use in function
                request.validated_data = data
                
            except BadRequest:
                raise
            except Exception as e:
                return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_license_key(f):
    """Decorator to validate license key format."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_key = kwargs.get('license_key')
        if not license_key or not isinstance(license_key, str):
            return jsonify({'error': 'Valid license key required'}), 400
        
        from .hash_utils import validate_license_format
        if not validate_license_format(license_key):
            return jsonify({'error': 'Invalid license key format'}), 400
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin access."""
    from flask_jwt_extended import jwt_required, get_jwt_identity
    
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        if get_jwt_identity() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function