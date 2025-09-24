from models.user import User

def create_user(username, password_hash, first_name='', last_name='', role='user'):
    if User.get_by_username(username):
        return {'error': 'Username already exists'}, 400
    
    if role not in ['admin', 'user']:
        return {'error': 'Invalid role specified'}, 400
    
    return User.create(
        username=username,
        password_hash=password_hash,
        first_name=first_name,
        last_name=last_name,
        role=role
    )

def get_users(page=1, per_page=10):
    from models.database import get_db_connection
    offset = (page - 1) * per_page
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0]
        c.execute('''
            SELECT id, username, first_name, last_name, role 
            FROM users
            ORDER BY id 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        users = [
            {
                'id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'role': row[4]
            } for row in c.fetchall()
        ]
    return users, total

def update_user(username, **kwargs):
    """ Update user details. """
    return User.update(username, **kwargs)

def remove_user(username):
    from models.database import get_db_connection
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        if c.rowcount == 0:
            return {'success': False, 'error': 'User not found'}
        conn.commit()
        return {'success': True}

def get_users_count():
    from models.database import get_db_connection
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0]
    return total

def get_role_by_username(username):
        """Get the role of a user by username."""
        from models.database import get_db_connection
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT role FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            return row['role'] if row else None
