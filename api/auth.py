from datetime import timedelta
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

from services.security import verify_admin_credentials
from utils.validators import validate_json

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['POST'])
@validate_json({'username': str, 'password': str})
def login():
    data = request.get_json()
    username, password = data['username'], data['password']
    
    if verify_admin_credentials(username, password):
        access_token = create_access_token(
            identity=username,
            expires_delta=timedelta(days=1)
        )
        resp = make_response({'access_token': access_token, 'user': username})
        resp.set_cookie('access_token_cookie', access_token, httponly=True, samesite='Lax')
        return resp
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    return jsonify({'user': current_user})