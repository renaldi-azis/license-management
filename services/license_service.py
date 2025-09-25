from datetime import datetime
from models.license import License
from models.product import Product
from utils.hash_utils import hash_license_key

def create_license(product_id, user_id, credit_number, machine_code,expires_hours=24):
    """Create a new license for a product."""
    # Verify product exists
    product = Product.get_by_id(product_id)
    if not product:
        return {'success': False, 'error': 'Product not found'}
    
    return License.create(product_id, user_id, credit_number , machine_code, expires_hours)

def get_licenses(search_query="", page=1, per_page=10):
    """Get all licenses with pagination."""
    from models.database import get_db_connection
    
    offset = (page - 1) * per_page
    # Get keywords from search_query ignore empty strings
    keywords = [kw.strip() for kw in search_query.split(',') if kw.strip()]
    
    with get_db_connection() as conn:
        c = conn.cursor()
        if(keywords):
            query_conditions = []
            params = []
            for kw in keywords:
                condition = "(l.user_id LIKE ? OR l.machine_code LIKE ? OR l.key LIKE ? OR p.name LIKE ?)"
                query_conditions.append(condition)
                like_kw = f'%{kw}%'
                params.extend([like_kw, like_kw, like_kw, like_kw])
            where_clause = " OR ".join(query_conditions)
            count_query = f'''
                SELECT COUNT(*) FROM licenses l
                LEFT JOIN products p ON l.product_id = p.id
                WHERE {where_clause}
            '''
            c.execute(count_query, params)
        else:
            c.execute("SELECT COUNT(*) FROM licenses")
        total = c.fetchone()[0]

        # update licenses expired status
        c.execute('''
            UPDATE licenses
            SET status = 'expired'
            WHERE expires_at IS NOT NULL AND expires_at < ? AND status != 'revoked'
        ''', (datetime.now(),))
        conn.commit()
        
        if(keywords):
            data_query = f'''
                SELECT l.*, p.name as product_name
                FROM licenses l
                LEFT JOIN products p ON l.product_id = p.id
                WHERE {where_clause}
                ORDER BY l.created_at DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([per_page, offset])
            c.execute(data_query, params)
        else:
            c.execute('''
                SELECT l.*, p.name as product_name
                FROM licenses l
                LEFT JOIN products p ON l.product_id = p.id
                ORDER BY l.created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset)) 

        licenses = []
        for row in c.fetchall():
            license_data = dict(row)
            # Show partial key for security
            license_data['key_display'] = license_data['key'][:8] + '...' if license_data['key'] else None
            license_data['key']  # Hide full key
            licenses.append(license_data)

        return licenses, total

def get_license_detail(license_key):
    """Get detailed information for a specific license."""
    from models.database import get_db_connection

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT l.*, p.name as product_name
            FROM licenses l
            LEFT JOIN products p ON l.product_id = p.id
            WHERE l.key = ?
        ''', (license_key,))
        row = c.fetchone()
        if not row:
            return None
        license_data = dict(row)
        # Optionally, hide the full key in the response
        license_data['key_display'] = license_data['key']
        return license_data

def get_license_stats():
    """Get overall license statistics."""
    from models.database import get_db_connection
    from datetime import datetime, timedelta
    
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Basic stats
        c.execute("SELECT COUNT(*) as total FROM licenses")
        total_licenses = c.fetchone()['total']
        
        c.execute("SELECT COUNT(*) as active FROM licenses WHERE status = 'active'")
        active_licenses = c.fetchone()['active']
        
        c.execute("SELECT COUNT(*) as expired FROM licenses WHERE status = 'expired'")
        expired_licenses = c.fetchone()['expired']
        
        c.execute("SELECT COUNT(*) as revoked FROM licenses WHERE status = 'revoked'")
        revoked_licenses = c.fetchone()['revoked']
        
        # Usage stats
        c.execute("SELECT AVG(usage_count) as avg_usage, MAX(usage_count) as max_usage FROM licenses")
        usage_stats = c.fetchone()
        
        # Recent activity (last 3 days)
        week_ago = datetime.now() - timedelta(days=3)
        c.execute('''
            SELECT COUNT(*) as recent_validations
            FROM usage_logs 
            WHERE action = 'validation' AND timestamp > ?
        ''', (week_ago,))
        recent_validations = c.fetchone()['recent_validations']
        
        return {
            'total_licenses': total_licenses,
            'active_licenses': active_licenses,
            'expired_licenses': expired_licenses,
            'revoked_licenses': revoked_licenses,
            'avg_usage_per_license': round(usage_stats['avg_usage'] or 0, 2),
            'max_usage': usage_stats['max_usage'] or 0,
            'recent_validations': recent_validations
        }
    
def revoke_license(license_key):
    """Revoke a license key."""
    return License.revoke(license_key)

def delete_license(license_key):
    """Delete a license key."""
    return License.delete(license_key)
    
def validate_license(product_name, license_key, ip_address, device_id=None):
    """Validate a license key for a product."""
    # Find product by name
    product = Product.get_by_name(product_name)
    if not product:
        return {'valid': False, 'error': 'Product not found'}

    product_id = product['id']
    # Validate license using License model
    result = License.validate(product_id, license_key, ip_address, device_id)
    return result