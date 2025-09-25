from datetime import datetime
from models.product import Product
from models.setting import Setting

def create_setting(product_id, number_of_credits, license_duration_hours):
    """Create a new setting for a product."""
    if Setting.get_by_product_id(product_id):
        return {'success': False, 'error': 'Setting for this product already exists'}, 400
    
    product = Product.get_by_id(product_id)
    if not product:
        return {'success': False, 'error': 'Product not found'}, 400
    
    return Setting.create(product_id, number_of_credits, license_duration_hours)


def update_setting(product_id, number_of_credits=None, license_duration_hours=None):
    """Update settings for a product."""
    setting = Setting.get_by_product_id(product_id)
    if not setting:
        return {'success': False, 'error': 'Setting not found'}
    
    return Setting.update(product_id, number_of_credits, license_duration_hours)
    
    

def get_settings(search_query="", page=1, per_page=10):
    """Get all settings with pagination."""
    from models.database import get_db_connection
    
    offset = (page - 1) * per_page
    keywords = [kw.strip() for kw in search_query.split(',') if kw.strip()]
    
    with get_db_connection() as conn:
        c = conn.cursor()
        if(keywords):
            query_conditions = []
            params = []
            for kw in keywords:
                condition = "(p.name LIKE ?)"
                query_conditions.append(condition)
                like_kw = f'%{kw}%'
                params.append(like_kw)
            where_clause = " OR ".join(query_conditions)
            count_query = f'''
                SELECT COUNT(*) FROM settings s
                LEFT JOIN products p ON s.product_id = p.id
                WHERE {where_clause}
            '''
            c.execute(count_query, params)
        else:
            c.execute("SELECT COUNT(*) FROM settings")
        total = c.fetchone()[0]
        
        if(keywords):
            data_query = f'''
                SELECT s.*, p.name as product_name
                FROM settings s
                LEFT JOIN products p ON s.product_id = p.id
                WHERE {where_clause}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([per_page, offset])
            c.execute(data_query, params)
        else:
            c.execute('''
                SELECT s.*, p.name as product_name
                FROM settings s
                LEFT JOIN products p ON s.product_id = p.id
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
        rows = c.fetchall()
        settings = [dict(row) for row in rows]
    return settings, total

def get_setting_by_product_id(product_id):
    """Get setting by product ID."""
    return Setting.get_by_product_id(product_id)

def delete_setting(setting_id):
    """Delete a setting by ID."""
    return Setting.delete(setting_id)