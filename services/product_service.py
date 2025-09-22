from models.product import Product

def create_product(name, description=None, max_devices=1):
    """Create a new software product."""
    return Product.create(name, description, max_devices)

def get_products(page=1, per_page=10):
    from models.database import get_db_connection
    offset = (page - 1) * per_page
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM products')
        total = c.fetchone()[0]
        c.execute('SELECT * FROM products LIMIT ? OFFSET ?', (per_page, offset))
        rows = c.fetchall()
        products = [dict(row) for row in rows]
        # Optionally, add stats to each product here
        return products, total

def update_product(product_id, **kwargs):
    """Update product information."""
    return Product.update(product_id, **kwargs)

def get_product_stats(product_id):
    """Get detailed statistics for a specific product."""
    from models.database import get_db_connection
    from datetime import datetime, timedelta
    
    product = Product.get_by_id(product_id)
    if not product:
        return {'success': False, 'error': 'Product not found'}
    
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # License counts
        c.execute('''
            SELECT 
                COUNT(*) as total_licenses,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_licenses,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired_licenses,
                SUM(CASE WHEN status = 'revoked' THEN 1 ELSE 0 END) as revoked_licenses,
                AVG(usage_count) as avg_usage,
                MAX(usage_count) as max_usage
            FROM licenses 
            WHERE product_id = ?
        ''', (product_id,))
        
        license_stats = c.fetchone()
        
        # Revenue estimation (assuming $10/license)
        active_licenses = license_stats['active_licenses'] or 0
        estimated_revenue = active_licenses * 10
        
        # Recent activity
        week_ago = datetime.now() - timedelta(days=7)
        c.execute('''
            SELECT COUNT(*) as recent_validations
            FROM usage_logs ul
            JOIN licenses l ON ul.license_key = l.key
            WHERE l.product_id = ? AND ul.action = 'validation' AND ul.timestamp > ?
        ''', (product_id, week_ago))
        
        recent_activity = c.fetchone()['recent_validations']
        
        return {
            'product': product,
            'license_stats': dict(license_stats),
            'estimated_revenue': estimated_revenue,
            'recent_validations': recent_activity
        }

def remove_product(product_id):
    from models.database import get_db_connection
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM products WHERE id = ?', (product_id,))
        c.execute('DELETE FROM licenses WHERE product_id = ?', (product_id,))
        # if c.rowcount == 0:
        #     return {'success': False, 'error': 'Product not found'}
        conn.commit()
        return {'success': True}