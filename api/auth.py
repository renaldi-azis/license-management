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
        username = request.form['username']
        password = request.form['password']
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            if c.fetchone()[0] == 0:
                hashed_pw = generate_password_hash(password)
                c.execute(
                    'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                    (username, hashed_pw, 'admin')
                )
                conn.commit()
                flash('Admin account created! Please sign in.', 'success')
                return redirect(url_for('auth.login'))

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            if c.fetchone():
                flash('Username already exists', 'danger')
                return render_template('register.html')
            hashed_pw = generate_password_hash(password)
            c.execute(
                'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                (username, hashed_pw, 'user')
            )
            conn.commit()
        flash('Account created! Please sign in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@bp.route('/login', methods=['POST'])
@validate_json({'username': str, 'password': str})
def login():
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
        role = row[1]

    if verify_admin_credentials(username, password):
        access_token = create_access_token(
            identity=role,  # Use role as identity
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

@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    resp = make_response(redirect('/admin'))
    resp.set_cookie('access_token_cookie', '', expires=0)
    return resp