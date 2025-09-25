from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.setting_service import (create_setting, update_setting, get_settings, get_setting_by_product_id, delete_setting)
from services.users_service import get_role_by_username
from utils.validators import validate_json

bp = Blueprint('settings', __name__)

@bp.route('', methods=['POST'])
@jwt_required()
@validate_json({
    'product_id': int,
    'number_of_credits': int,
    'license_duration_hours': int
})
def create_setting_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    return create_setting(
        product_id=data['product_id'],
        number_of_credits=data['number_of_credits'],
        license_duration_hours=data['license_duration_hours']
    )

@bp.route('', methods=['GET'])
@jwt_required()
def get_all_settings_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    query = request.args.get('query', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    settings, total  = get_settings(query, page, per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'settings': settings,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    }), 200

@bp.route('/<int:product_id>', methods=['GET'])
@jwt_required()
def get_setting_route(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    setting = get_setting_by_product_id(product_id)
    if setting:
        return jsonify(setting), 200
    return jsonify({'error': 'Setting not found'}), 404

@bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
@validate_json({
    'number_of_credits': int,
    'license_duration_hours': int
})
def update_setting_route(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    result = update_setting(
        product_id=product_id,
        number_of_credits=data.get('number_of_credits'),
        license_duration_hours=data.get('license_duration_hours')
    )
    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 404

@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_setting_route(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = delete_setting(product_id)
    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 404

