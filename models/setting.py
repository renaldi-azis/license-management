from models.database import get_db_connection
from datetime import datetime

class Setting:
    @staticmethod
    def create(product_id, number_of_credits=0, license_duration_hours=24):
        """Create a new setting for a product."""
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO settings (product_id, number_of_credits, license_duration_hours)
                    VALUES (?, ?, ?)
                ''', (product_id, number_of_credits, license_duration_hours))
                conn.commit()
                return {'success': True, 'setting_id': c.lastrowid}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}, 400
    
    @staticmethod
    def update(product_id, number_of_credits=None, license_duration_hours=None):
        """Update settings for a product."""
        setting = Setting.get_by_product_id(product_id)
        if not setting:
            return {'success': False, 'error': 'Setting not found'}
        
        fields = []
        params = []
        if number_of_credits is not None:
            fields.append('number_of_credits = ?')
            params.append(number_of_credits)
        if license_duration_hours is not None:
            fields.append('license_duration_hours = ?')
            params.append(license_duration_hours)
        
        if not fields:
            return {'success': False, 'error': 'No fields to update'}
        
        params.append(product_id)
        query = f'UPDATE settings SET {", ".join(fields)} WHERE product_id = ?'
        
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(query, params)
                conn.commit()
                return {'success': True}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}, 400
    
    @staticmethod
    def get_all():
        """Get all settings."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM settings')
            return c.fetchall()
        
    @staticmethod
    def get_by_product_id(product_id):
        """Get setting by product ID."""
        with get_db_connection() as conn:
            c = conn.cursor()
            # get setting and product name by product_id
            c.execute('''
                SELECT s.*, p.name as product_name FROM settings s
                LEFT JOIN products p ON s.product_id = p.id
                WHERE s.product_id = ?
            ''', (product_id,))
            row = c.fetchone()
            return dict(row) if row else None
            
        
    @staticmethod
    def delete(product_id):
        """Delete setting by product ID."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM settings WHERE product_id = ?', (product_id,))
            conn.commit()
            affected = c.rowcount
            if affected > 0:
                return {'success': True, 'message': 'Setting deleted'}
            return {'success': False, 'error': 'Setting not found'}
            