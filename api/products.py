from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.users_service import get_role_by_username
from services.product_service import (
    create_product, get_products, update_product, 
    get_product_stats, remove_product
)
from utils.validators import validate_json

bp = Blueprint('products', __name__)

@bp.route('', methods=['GET'])
@jwt_required()
def list_products():
    page = int(request.args.get('page', 1))
    query = request.args.get('q', '').strip()
    per_page = int(request.args.get('per_page', 5))
    products, total = get_products(search_query=query, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'products': products,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/all', methods=['GET'])
def get_all_products():
    from services.product_service import get_products
    # Get all products without pagination
    products, _ = get_products(page=1, per_page=10000)  # Use a large per_page to fetch all
    return jsonify({'products': products})

@bp.route('', methods=['POST'])
@jwt_required()
@validate_json({'name': str, 'max_devices': int})
def create_product_route():
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    result = create_product(
        name=data['name'],
        description=data.get('description'),
        max_devices=data['max_devices']
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400

@bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
@validate_json({'name': str, 'max_devices': int})
def update_product_route(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    result = update_product(
        product_id=product_id,
        **data
    )
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400

@bp.route('/<int:product_id>/stats', methods=['GET'])
@jwt_required()
def product_stats(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    stats = get_product_stats(product_id)
    return jsonify(stats)

@bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product_route(product_id):
    username = get_jwt_identity()
    if get_role_by_username(username) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    result = remove_product(product_id)
    if result.get('success'):
        return jsonify({'success': True, 'message': 'Product removed'})
    return jsonify({'success': False, 'error': result.get('error', 'Unknown error')}), 400