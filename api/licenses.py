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

from utils.hash_utils import hash_machine_code
from utils.validators import validate_license_key

bp = Blueprint('licenses', __name__)

def contains_xss(value):
    # Simple check for script tags or suspicious input
    return bool(re.search(r'<script|onerror=|onload=|javascript:', value, re.IGNORECASE))

@bp.route('', methods=['POST'])
@rate_limited(limit='20 per minute')  # Limit license creation
@jwt_required()
def create_license_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.data
    
    if contains_xss(data.get('user_id', '')):
        return jsonify({'error': 'Invalid input detected'}), 400
    
    result = create_license(
        product_id=data['product_id'],
        user_id=data['user_id'],
        credit_number=data.get('credit_number', 'None'),
        machine_code=hash_machine_code(data.get('machine_code', 'None')),
        expires_hours=data.get('expires_hours', 30)
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
    result = get_license_detail(license_key)
    if result:
        return jsonify(result)
    return jsonify(result), 404

@bp.route('/<license_key>', methods=['PUT'])
@rate_limited(limit='10 per minute')  # Limit license updates
@jwt_required()
@validate_license_key
def update_license_route(license_key):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if 'user_id' in data and contains_xss(data['user_id']):
        return jsonify({'error': 'Invalid input detected'}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM licenses WHERE key = ?", (license_key,))
    license_record = cursor.fetchone()
    if not license_record:
        conn.close()
        return jsonify({'error': 'License not found'}), 404
    
    # Prepare update fields
    update_fields = []
    update_values = []
    
    if 'user_id' in data:
        update_fields.append("user_id = ?")
        update_values.append(data['user_id'])
    
    # change credit_number to int and validate
    data['credit_number'] = int(data['credit_number']) if 'credit_number' in data and isinstance(data['credit_number'], (int, str)) and str(data['credit_number']).isdigit() else 0

    if 'credit_number' in data:
        if not isinstance(data['credit_number'], int) or data['credit_number'] < 0:
            data['credit_number'] = 0  # set to 0 if invalid
        update_fields.append("credit_number = ?")
        update_values.append(data['credit_number'])
    
    if 'expires_at' in data:
        if data['expires_at'] is None or data['expires_at'] == '':
            update_fields.append("expires_at = NULL")
        else:
            update_fields.append("expires_at = ?")
            update_values.append(data['expires_at'])

    if not update_fields:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400
    
    update_values.append(license_key)
    sql_query = f"UPDATE licenses SET {', '.join(update_fields)} WHERE key = ?"
    cursor.execute(sql_query, tuple(update_values))
    conn.commit()
    conn.close()
    
    updated_license = get_license_detail(license_key)
    return jsonify({'success': True, 'data': updated_license})

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
@rate_limited(limit='40 per minute')  # Limit license stats retrieval
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
def automate_license_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.data
    
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

    conn = get_db_connection()
    cursor = conn.cursor()
    # check if any active license of the user_id, machine_code with same product_name already exists
    cursor.execute("""
        SELECT COUNT(*) AS count FROM licenses
        WHERE status = 'active' AND user_id = ? AND machine_code = ? AND product_id = ?
    """, (data['user_id'], hash_machine_code(data['machine_code']), product_id))
    result = cursor.fetchone()
    conn.close()
    if result['count'] > 0:
        return jsonify({'error': 'Active license already exists for this user and machine code'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS count FROM licenses
        WHERE user_id != ? AND machine_code = ?
    """, (data['user_id'], hash_machine_code(data['machine_code'])))
    result = cursor.fetchone()
    conn.close()
    if result['count'] > 0:
        return jsonify({'error': 'Already registered machine_code with another user'}), 400
    
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
    expires_hours = max(1, license_duration_hours)  # at least 1 day

    result = create_license(
        product_id=product_id,
        user_id=data['user_id'],
        credit_number=number_of_credits,
        machine_code=hash_machine_code(data.get('machine_code', 'None')),
        expires_hours=expires_hours
    )
    
    if result['success']:
        return jsonify(result), 200
    return jsonify(result), 400

@bp.route('/update/credit-number', methods=['POST'])
@rate_limited(limit='30 per minute')  # Limit credit number updates
@jwt_required()
def update_credit_number_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.data
    license_key = data.get('license_key')
    used_credits = data.get('used_credits')
    
    if not license_key or not used_credits:
        return jsonify({'error': 'license_key and used_credits are required'}), 400
    
    if not isinstance(used_credits, int) or used_credits < 0:
        used_credits = 0  # set to 0 if invalid
    
    if contains_xss(license_key):
        return jsonify({'error': 'Invalid input detected'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM licenses WHERE key = ?", (license_key,))
    license_record = cursor.fetchone()
    if not license_record:
        conn.close()
        return jsonify({'error': 'License not found'}), 404
    new_credit_number = license_record['credit_number'] - used_credits
    if(new_credit_number < 0):
        new_credit_number = 0
    cursor.execute("""
        UPDATE licenses
        SET credit_number = ?
        WHERE key = ?
    """, (new_credit_number, license_key))
    conn.commit()
    conn.close()

    # get the updated license details
    updated_license = get_license_detail(license_key)
    if not updated_license:
        return jsonify({'error': 'License not found after update'}), 404
    
    return jsonify({'success':True, "data":updated_license}), 200