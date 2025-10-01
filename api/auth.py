from datetime import timedelta
from flask import Blueprint, flash, render_template, request, jsonify, make_response, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
# from flask_recaptcha import ReCaptcha
from services.rate_limiter import rate_limited
from services.users_service import get_role_by_username
from services.security_service import (hash_password, verify_credentials)
from services.users_service import (create_user, get_users_count, get_users, update_user, remove_user)
from models.database import get_db_connection

from cryptography.hazmat.primitives import serialization
from api.security import session_manager

bp = Blueprint('auth', __name__)
# recaptcha = ReCaptcha()  # or pass your app if not using factory

# Update registration logic to set role
@bp.route('/register', methods=['GET', 'POST'])
@rate_limited(limit='30 per minute')  # Limit registration attempts
def register():
    if request.method == 'POST':
        data = request.get_json()
        username, password , firstname, lastname = data['username'], data['password'], data['firstname'], data['lastname']
        role = 'user'  # Default role
        
        if get_users_count() == 0:
            # If no users exist, create the first user as admin
            role = 'admin'
        hashed_pw = hash_password(password)
        create_user(
            username=username,
            password_hash=hashed_pw,
            first_name=firstname,
            last_name=lastname,
            role=role  # Subsequent users are regular users
        )
        return jsonify({"result":"success"}), 201
        
    return render_template('register.html')


@bp.route('/login', methods=['POST','GET'])
@rate_limited(limit='10 per minute')  # Limit login attempts
def login():
    if request.method == 'POST':
        print(request)
        data = request.get_json()
        username, password = data['username'], data['password']
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT password, role FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            if not row or not verify_credentials(row[0], password):
                return jsonify({'error': 'Invalid credentials'}), 401
            if row:
                expected_password_hash = row[0]
            else:
                expected_password_hash = None      

        if verify_credentials(expected_password_hash, password):
            access_token = create_access_token(
                identity= username,  # Use username as identity
                expires_delta=timedelta(days=1)
            )          

            resp = make_response({'access_token': access_token, 'user': username})
            resp.set_cookie('access_token_cookie', access_token, httponly=True, samesite='Lax')

            return resp
        return jsonify({'error': 'Invalid credentials'}), 401
    return render_template('login.html')



@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    resp = make_response(redirect('/admin'))
    resp.set_cookie('access_token_cookie', '', expires=0)
    return resp

@bp.route('/users', methods=['GET'])
@rate_limited(limit='20 per minute')  # Limit user listing
@jwt_required()
def list_users():
    current_user = get_jwt_identity()
    if get_role_by_username(current_user) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))
    (users, total) = get_users(page, per_page)
    users = [user for user in users if user['username'] != current_user]
    total_pages = (len(users) + per_page - 1) // per_page
    return jsonify({
        'users': users,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/users/<string:username>', methods=['PUT'])
@rate_limited(limit='20 per minute')  # Limit user updates
@jwt_required()
def update_user_info(username):
    current_user = get_jwt_identity()
    if get_role_by_username(current_user) != 'admin' and current_user != username:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    
    update_user(username, first_name=first_name, last_name=last_name)    
    return jsonify({'result': 'success'})

@bp.route('/users/<string:username>/<string:role>', methods=['PUT'])
@rate_limited(limit='20 per minute')  # Limit user listing
@jwt_required()
def change_user_role(username, role):
    current_user = get_jwt_identity()
    if get_role_by_username(current_user) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403    
    update_user(username, role=role) 
    return jsonify({'result': 'success'})

@bp.route('/users/<string:username>', methods=['DELETE'])
@rate_limited(limit='20 per minute')  # Limit user deletion
@jwt_required()
def delete_user(username):
    current_user = get_jwt_identity()
    if get_role_by_username(current_user) != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    remove_user(username)    
    return jsonify({'result': 'success'})