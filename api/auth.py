from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

from services.security import verify_admin_credentials
from utils.validators import validate_json

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['POST'])
@validate_json({'username': str, 'password': str})
def login():
    data = request.get_json()
    username, password = data['username'], data['password']
    
    if verify_admin_credentials(username, password):
        access_token = create_access_token(
            identity=username,
            expires_delta=86400  # 24 hours
        )
        return jsonify({'access_token': access_token, 'user': username})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    return jsonify({'user': current_user})