from models.database import get_db_connection
from datetime import datetime, timedelta

class License:
    @staticmethod
    def create(product_id, user_id, credit_number, machine_code, expires_days=30, license_key=None):
        """Create a new license."""
        from utils.hash_utils import generate_license_key
        
        if not license_key:
            license_key = generate_license_key()
        
        expires_at = datetime.now() + timedelta(days=expires_days)
        # hashed_key = hash_license_key(license_key)
        
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO licenses (key, product_id, user_id, credit_number, machine_code, expires_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                ''', (license_key, product_id, user_id, credit_number, machine_code, expires_at))
                conn.commit()
                return {'success': True, 'license_key': license_key}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}
    
    @staticmethod
    def validate(product_id, license_key, ip_address, device_id=None):
        """Validate a license key."""
        from models.product import Product        
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT l.*, p.name as product_name, p.max_devices
                FROM licenses l
                JOIN products p ON l.product_id = p.id
                WHERE l.key = ? AND l.product_id = ? AND l.status = 'active'
            ''', (license_key, product_id))
            
            license = c.fetchone()
            
            if not license:
                return {'valid': False, 'error': 'Invalid license key'}
            
            # Check expiration
            expires_at = license['expires_at']
            if expires_at:
                if isinstance(expires_at, str):
                    # Try parsing as ISO format or SQLite format
                    try:
                        expires_at = datetime.fromisoformat(expires_at)
                    except ValueError:
                        expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > expires_at:
                    c.execute("UPDATE licenses SET status = 'expired' WHERE key = ?", (license_key,))
                    conn.commit()
                    return {'valid': False, 'error': 'License expired'}
            
            # Check device limit
            if device_id and license['device_id'] and license['device_id'] != device_id:
                return {'valid': False, 'error': 'Device limit exceeded'}
            
            # Update usage
            c.execute('''
                UPDATE licenses 
                SET usage_count = usage_count + 1, 
                    device_id = COALESCE(?, device_id)
                WHERE key = ?
            ''', (device_id, license_key))
            conn.commit()
    
            License.log_usage(license_key, ip_address, 'validation', 'success')
            
            return {
                'valid': True,
                'license_id': license['id'],
                'product_name': license['product_name'],
                'expires_at': expires_at.isoformat() if expires_at else None,
                'usage_count': license['usage_count'] + 1,
                'max_devices': license['max_devices']
            }
    
    @staticmethod
    def log_usage(license_key, ip_address, action, status='success', user_agent=None):
        """Log license usage."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO usage_logs (license_key, ip_address, action, response_status, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (license_key, ip_address, action, status, user_agent))
            conn.commit()
    
    @staticmethod
    def revoke(license_key):
        """Revoke a license."""
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE licenses SET status = 'revoked' WHERE key = ?", (license_key,))
            affected = c.rowcount
            conn.commit()
            
            if affected > 0:
                License.log_usage(license_key, 'admin', 'revocation', 'success')
                return {'success': True, 'message': 'License revoked'}
            
            return {'success': False, 'error': 'License not found'}
        
    @staticmethod
    def delete(license_key):
        """Delete a license."""
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM licenses WHERE key = ?", (license_key,))
            affected = c.rowcount
            conn.commit()
            
            if affected > 0:
                License.log_usage(license_key, 'admin', 'deletion', 'success')
                return {'success': True, 'message': 'License deleted'}
            
            return {'success': False, 'error': 'License not found'}
        
    @staticmethod
    def get_by_name(name):
        from models.database import get_db_connection
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM products WHERE product_name = ?', (name,))
            row = c.fetchone()
            return dict(row) if row else None