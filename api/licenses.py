import pandas as pd
import io
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

import re

from models.database import get_db_connection
from services.rate_limiter import rate_limited
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
@rate_limited(limit='20 per minute')  # Limit license creation
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
@rate_limited(limit='10 per minute')  # Limit license revocation
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
@rate_limited(limit='10 per minute')  # Limit license retrieval
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
@rate_limited(limit='30 per minute')  # Limit license listing
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
@rate_limited(limit='30 per minute')  # Limit license search
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
@rate_limited(limit='20 per minute')  # Limit license deletion
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
@rate_limited(limit='10 per minute')  # Limit license stats retrieval
@jwt_required()
def license_stats():   
    stats = get_license_stats()
    return jsonify(stats)

@bp.route('/test/data', methods=['GET'])
@rate_limited(limit='30 per minute')  # Limit test data retrieval
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
@rate_limited(limit='5 per minute')  # Limit backup downloads
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

@bp.route('/automate', methods=['POST'])
@jwt_required()
@validate_json({
    'product_name': str,
    'user_id': str,
    'machine_code': str,
})
def automate_license_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if contains_xss(data.get('user_id', '')) or contains_xss(data.get('machine_code', '')) or contains_xss(data.get('product_name', '')):
        return jsonify({'error': 'Invalid input detected'}), 400
    
    # check if product exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE name = ?", (data['product_name'],))
    product = cursor.fetchone()
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    product_id = product['id']
    conn.close()

    #check if any of the user_id, product_name, machine_code already exists in active license
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS count FROM licenses
        WHERE status = 'active' AND (user_id = ? OR machine_code = ?)
    """, (data['user_id'], data['machine_code']))
    result = cursor.fetchone()
    conn.close()
    if result['count'] > 0:
        return jsonify({'error': 'Active license already exists for given user_id or machine_code'}), 400
    
    # get number_of_credits, license_duration_hours data for the product
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT number_of_credits, license_duration_hours FROM settings WHERE product_id = ?", (product_id,))
    setting = cursor.fetchone()
    conn.close()
    if not setting:
        return jsonify({'error': 'Settings not found for the product'}), 404
    
    number_of_credits = setting['number_of_credits'] if setting['number_of_credits'] is not None else 0
    license_duration_hours = setting['license_duration_hours'] if setting['license_duration_hours'] is not None else 24  # default a day
    expires_hours = max(1, license_duration_hours // 24)  # at least 1 day

    result = create_license(
        product_id=product_id,
        user_id=data['user_id'],
        credit_number=number_of_credits,
        machine_code=data['machine_code'],
        expires_hours=expires_hours
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400