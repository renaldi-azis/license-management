from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from models.database import get_db_connection
from services.license_service import (
    create_license, revoke_license, get_licenses, 
    get_license_stats, get_license_detail
)
import re
from utils.validators import validate_json, validate_license_key

bp = Blueprint('licenses', __name__)



def contains_xss(value):
    # Simple check for script tags or suspicious input
    return bool(re.search(r'<script|onerror=|onload=|javascript:', value, re.IGNORECASE))

@bp.route('', methods=['POST'])
@jwt_required()
@validate_json({
    'product_id': int,
    'user_id': str,
    'expires_days': int
})
def create_license_route():
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    result = create_license(
        product_id=data['product_id'],
        user_id=data['user_id'],
        expires_days=data.get('expires_days', 30)
    )
    
    if contains_xss(data.get('user_id', '')):
        return jsonify({'error': 'Invalid input detected'}), 400

    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400

@bp.route('/<license_key>/revoke', methods=['POST'])
@jwt_required()
@validate_license_key
def revoke_license_route(license_key):
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = revoke_license(license_key)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 404

@bp.route('/<license_key>', methods=['GET'])
@jwt_required()
@validate_license_key
def get_license_route(license_key):
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = get_license_detail(license_key)
    if result:
        return jsonify(result)
    return jsonify(result), 404

@bp.route('', methods=['GET'])
@jwt_required()
def list_licenses():
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    
    licenses, total = get_licenses(page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'licenses': licenses,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/stats', methods=['GET'])
@jwt_required()
def license_stats():
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    stats = get_license_stats()
    return jsonify(stats)