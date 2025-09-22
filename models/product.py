from models.database import get_db_connection

class Product:
    @staticmethod
    def create(name, description=None, max_devices=1):
        """Create a new product."""
        with get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(
                    'INSERT INTO products (name, description, max_devices) VALUES (?, ?, ?)',
                    (name, description, max_devices)
                )
                conn.commit()
                return {'success': True, 'product_id': c.lastrowid}
            except Exception as e:
                conn.rollback()
                return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_all(page=1, per_page=50):
        """Get all products with pagination."""
        offset = (page - 1) * per_page
        
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Get total count
            c.execute('SELECT COUNT(*) FROM products')
            total = c.fetchone()[0]
            
            # Get products
            c.execute('''
                SELECT * FROM products 
                ORDER BY name 
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            products = [dict(row) for row in c.fetchall()]
            
            # Add license counts
            for product in products:
                c.execute('''
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
                    FROM licenses WHERE product_id = ?
                ''', (product['id'],))
                counts = c.fetchone()
                product['total_licenses'] = counts['total']
                product['active_licenses'] = counts['active']
            
            return products, total
    
    @staticmethod
    def get_by_id(product_id):
        """Get product by ID."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            row = c.fetchone()
            return dict(row) if row else None
    @staticmethod
    def get_by_name(name):
        """Get product by name."""
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM products WHERE name = ?', (name,))
            row = c.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update(product_id, **kwargs):
        """Update product information."""
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['name', 'description', 'max_devices']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return {'success': False, 'error': 'No valid fields to update'}
        
        values.append(product_id)
        query = f"UPDATE products SET {', '.join(fields)} WHERE id = ?"
        
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute(query, values)
            conn.commit()
            
            if c.rowcount > 0:
                return {'success': True, 'message': 'Product updated'}
            return {'success': False, 'error': 'Product not found'}