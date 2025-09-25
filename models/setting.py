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
                return {'success': False, 'error': str(e)}
    
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
            c.execute('SELECT * FROM settings WHERE product_id = ?', (product_id,))
            return c.fetchone()
        
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
            