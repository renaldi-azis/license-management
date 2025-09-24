from models.database import get_db_connection

class User:
    @staticmethod
    def create(username, password_hash, first_name=None, last_name=None, role='user'):
        """Create a new user."""
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(
                    'INSERT INTO users (username, password_hash, first_name, last_name, role) VALUES (?, ?, ?, ?, ?)',
                    (username, password_hash, first_name, last_name, role)
                )
                conn.commit()
                return {'success': True, 'user_id': c.lastrowid}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_by_username(username):
        """Get user by username."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            return dict(row) if row else None
        
    @staticmethod
    def get_all(page=1, per_page=50):
        """Get all users with pagination."""
        offset = (page - 1) * per_page
        
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get total count
            c.execute('SELECT COUNT(*) FROM users')
            total = c.fetchone()[0]
            
            # Get users
            c.execute('''
                SELECT id, username, first_name, last_name, role, created_at 
                FROM users 
                ORDER BY username 
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            users = [dict(row) for row in c.fetchall()]
            return users, total
        
    @staticmethod
    def update(username, **kwargs):
        """Update user details."""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(username)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(f'UPDATE users SET {", ".join(fields)} WHERE username = ?', values)
                if c.rowcount == 0:
                    return {'success': False, 'error': 'User not found'}
                conn.commit()
                return {'success': True}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}

    