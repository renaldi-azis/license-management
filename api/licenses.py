import pandas as pd
import io
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

import re

from models.database import get_db_connection
from services.users_service import get_role_by_username
from services.license_service import (
    create_license, revoke_license, get_licenses, delete_license,
    get_license_stats, get_license_detail
)

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
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if contains_xss(data.get('user_id', '')):
        return jsonify({'error': 'Invalid input detected'}), 400
    
    result = create_license(
        product_id=data['product_id'],
        user_id=data['user_id'],
        credit_number=data.get('credit_number', 'None'),
        machine_code=data.get('machine_code', 'None'),
        expires_days=data.get('expires_days', 30)
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400

@bp.route('/<license_key>/revoke', methods=['POST'])
@jwt_required()
@validate_license_key
def revoke_license_route(license_key):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = revoke_license(license_key)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 404

@bp.route('/<license_key>', methods=['GET'])
@jwt_required()
@validate_license_key
def get_license_route(license_key):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = get_license_detail(license_key)
    if result:
        return jsonify(result)
    return jsonify(result), 404

@bp.route('', methods=['GET'])
@jwt_required()
def list_licenses():
    query = request.args.get('q', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    
    licenses, total = get_licenses(search_query=query , page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'licenses': licenses,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/search', methods=['GET'])
@jwt_required()
def search_licenses():   
    query = request.args.get('q', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    
    if contains_xss(query):
        return jsonify({'error': 'Invalid input detected'}), 400
    
    licenses, total = get_licenses(search_query=query, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'licenses': licenses,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/<license_key>',methods=['DELETE'])
@jwt_required()
@validate_license_key
def delete_license_route(license_key):    
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    result = delete_license(license_key)
    if result['success']:
        return jsonify({'message': 'License deleted successfully'})
    return jsonify(result), 404

@bp.route('/stats', methods=['GET'])
@jwt_required()
def license_stats():   
    stats = get_license_stats()
    return jsonify(stats)

@bp.route('/test/data', methods=['GET'])
@jwt_required()
def test_route():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.key, p.name AS product_name
        FROM licenses l
        JOIN products p ON l.product_id = p.id
        WHERE l.status = 'active'
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({
            'key': row['key'],
            'product_name': row['product_name']
        })
    return jsonify({'error': 'No active licenses found'}), 404


@bp.route('/backup', methods=['GET'])
@jwt_required()
def backup_licenses():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM licenses")
    rows = cursor.fetchall()
    conn.close()

    licenses = [dict(row) for row in rows]
    df = pd.DataFrame(licenses)
    output = io.BytesIO()
    # Use ExcelWriter, then close and seek
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Licenses')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='licenses_backup.xlsx'
    )