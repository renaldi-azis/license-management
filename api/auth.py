from datetime import timedelta
from flask import Blueprint, flash, render_template, request, jsonify, make_response, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import get_db_connection
from services.security import verify_admin_credentials
from utils.validators import validate_json

bp = Blueprint('auth', __name__)

# Update registration logic to set role
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username, password , firstname, lastname = data['username'], data['password'], data['firstname'], data['lastname']
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            
            if c.fetchone()[0] == 0:
                hashed_pw = generate_password_hash(password)
                c.execute(
                    'INSERT INTO users (username, password, first_name, last_name ,role) VALUES (?, ?, ?, ?, ?)',
                    (username, hashed_pw, firstname, lastname, 'admin')
                )
                conn.commit()
                return jsonify({"result":"success"}), 201

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            if c.fetchone():
                # flash('Username already exists', 'danger')
                return jsonify({"error":"Username already exists" }), 400
            hashed_pw = generate_password_hash(password)
            c.execute(
                'INSERT INTO users (username, password, first_name, last_name ,role) VALUES (?, ?, ?, ?, ?)',
                (username, hashed_pw, firstname, lastname, 'admin')
            )
            conn.commit()
            return jsonify({"result":"success"}), 201
        
    return render_template('register.html')

@bp.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':        
        data = request.get_json()
        username, password = data['username'], data['password']
        role = None
        # get role by username & password
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT password, role FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            if not row or not check_password_hash(row[0], password):
                return jsonify({'error': 'Invalid credentials'}), 401
            if row:
                expected_password_hash = row[0]
                role = row[1]
            else:
                expected_password_hash = None      

        if verify_admin_credentials(expected_password_hash, password):
            access_token = create_access_token(
                identity= role,  # Use role as identity
                expires_delta=timedelta(days=1)
            )
            resp = make_response({'access_token': access_token, 'user': username})
            resp.set_cookie('access_token_cookie', access_token, httponly=True, samesite='Lax')
            return resp
        return jsonify({'error': 'Invalid credentials'}), 401
    return render_template('login.html')

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    # find user by username
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT username, first_name, last_name, role FROM users WHERE username = ?', (current_user,))
        user = c.fetchone()
        if user:
            current_user = {
                'username': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'role': user[3]
            }
        else:
            return jsonify({'error': 'User not found'}), 404
    if(current_user is None):
        current_user = get_jwt_identity()
    return jsonify({'user': current_user})

@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    resp = make_response(redirect('/admin'))
    resp.set_cookie('access_token_cookie', '', expires=0)
    return resp

@bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))
    offset = (page - 1) * per_page
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0]
        
        c.execute('''
            SELECT id, username, first_name, last_name, role 
            FROM users 
            WHERE username != ?
            ORDER BY id 
            LIMIT ? OFFSET ?
        ''', (current_user, per_page, offset))
        
        users = [
            {
                'id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'role': row[4]
            } for row in c.fetchall()
        ]
    total_pages = (total + per_page - 1) // per_page
    return jsonify({
        'users': users,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_pages
        }
    })

@bp.route('/users/<string:username>/<string:role>', methods=['PUT'])
@jwt_required()
def change_user_role(username, role):
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # data = request.get_json()
    # new_role = data.get('role')
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Invalid role specified'}), 400
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))
        if c.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
    
    return jsonify({'result': 'success'})

@bp.route('/users/<string:username>', methods=['DELETE'])
@jwt_required()
def delete_user(username):
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        if c.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
    
    return jsonify({'result': 'success'})