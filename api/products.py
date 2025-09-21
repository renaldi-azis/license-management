from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.database import get_db_connection
from services.product_service import (
    create_product, get_products, update_product, 
    get_product_stats
)
from utils.validators import validate_json

bp = Blueprint('products', __name__, url_prefix='/products')

@bp.route('', methods=['POST'])
@jwt_required()
@validate_json({'name': str, 'max_devices': int})
def create_product_route():
    if get_jwt_identity() != 'admin':
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

@bp.route('', methods=['GET'])
@jwt_required()
def list_products():
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    page = request.args.get('page', 1, type=int)
    products, total = get_products(page=page)
    
    return jsonify({
        'products': products,
        'pagination': {'page': page, 'total': total}
    })

@bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
@validate_json({'name': str, 'max_devices': int})
def update_product_route(product_id):
    if get_jwt_identity() != 'admin':
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
    if get_jwt_identity() != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    stats = get_product_stats(product_id)
    return jsonify(stats)