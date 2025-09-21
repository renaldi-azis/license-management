from models.license import License
from models.product import Product
from utils.hash_utils import hash_license_key

def create_license(product_id, user_id, expires_days=30):
    """Create a new license for a product."""
    # Verify product exists
    product = Product.get_by_id(product_id)
    if not product:
        return {'success': False, 'error': 'Product not found'}
    
    return License.create(product_id, user_id, expires_days)

def revoke_license(license_key):
    """Revoke a license key."""
    return License.revoke(license_key)

def get_licenses(page=1, per_page=10):
    """Get all licenses with pagination."""
    from models.database import get_db_connection
    
    offset = (page - 1) * per_page
    
    # Get licenses with product info
       
    with get_db_connection() as conn:
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM licenses')
        total = c.fetchone()[0]
        
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
            del license_data['key']  # Hide full key
            licenses.append(license_data)

        return licenses, total

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
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
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