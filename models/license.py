from models.database import get_db_connection
from datetime import datetime, timedelta
from utils.hash_utils import hash_machine_code

class License:
    @staticmethod
    def create(product_id, user_id, credit_number, machine_code, expires_hours=24, license_key=None):
        """Create a new license."""
        from utils.hash_utils import generate_license_key
        
        if not license_key:
            license_key = generate_license_key()
        
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat() if expires_hours > 0 else None
        created_at = datetime.now().isoformat();

        # check user_id and machine_code combination does not already exist for the same product
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT COUNT(*) FROM licenses
                WHERE product_id = ? AND (user_id = ? OR machine_code = ?)
            ''', (product_id, user_id, machine_code))
            if c.fetchone()[0] > 0:
                return {'success': False, 'error': 'A license for this user and machine already exists for the product'}

        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO licenses (key, product_id, user_id, credit_number, machine_code, expires_at, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ? ,'active')
                ''', (license_key, product_id, user_id, credit_number, machine_code, expires_at, created_at))
                conn.commit()
                return {'success': True, 'license_key': license_key}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}
    
    @staticmethod
    def validate(product_id, license_key, machine_code):
        """Validate a license key."""   
        # Check license existence and status based on product_id , license_key and machine_code
        machine_code = hash_machine_code(machine_code)
        print(machine_code)
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT l.*, p.name as product_name, p.max_devices
                FROM licenses l
                JOIN products p ON l.product_id = p.id
                WHERE l.key = ? AND l.product_id = ? AND l.machine_code = ?
            ''', (license_key, product_id, machine_code))

            license = c.fetchone()
            print(license)
            if not license:
                return {'valid': False, 'error': 'Invalid license key or machine code'}
            if license['status'] == 'expired':
                return {'valid': False, 'error': 'License is expired'}
            
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
            
            return{
                'valid': True,
                'license_id': license['id'],
                'product_name': license['product_name'],
                'user_id': license['user_id'],
                'machine_code': license['machine_code'],
                'credit_number': license['credit_number'],
                'expires_at': expires_at.isoformat() if expires_at else None,
                'status': license['status']
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