import pytest
from datetime import datetime, timedelta
from models.license import License
from models.product import Product
from utils.hash_utils import generate_license_key


@pytest.fixture
def sample_product():
    """Create a sample product for testing."""
    result = Product.create('Test Product', 'Test description', 2)
    assert result['success'] is True
    return result['product_id']


@pytest.mark.usefixtures('app')
class TestLicenseModel:
    
    def test_create_license_success(self, sample_product):
        """Test creating a new license."""
        result = License.create(
            product_id=sample_product,
            user_id='test-user-123',
            expires_days=30
        )
        
        assert result['success'] is True
        assert 'license_key' in result
        assert len(result['license_key']) >= 16
    
    def test_validate_license_success(self, sample_product):
        """Test validating a newly created license."""
        # Create license
        license_key = generate_license_key()
        License.create(sample_product, 'test-user', license_key=license_key)
        
        # Validate
        result = License.validate(
            product_id=sample_product,
            license_key=license_key,
            ip_address='127.0.0.1',
            device_id='device-123'
        )
        
        assert result['valid'] is True
        assert result['product_name'] == 'Test Product'
        assert 'expires_at' in result
    
    def test_validate_expired_license(self, sample_product):
        """Test validating an expired license."""
        # Create expired license
        expires_at = datetime.now() - timedelta(days=1)
        from models.database import get_db_connection
        
        with get_db_connection() as conn:
            c = conn.cursor()
            hashed_key = hash_license_key('expired-key')
            c.execute('''
                INSERT INTO licenses (key, product_id, user_id, status, expires_at)
                VALUES (?, ?, ?, 'active', ?)
            ''', (hashed_key, sample_product, 'test-user', expires_at))
            conn.commit()
        
        # Validate
        result = License.validate(
            sample_product,
            'expired-key',
            '127.0.0.1'
        )
        
        assert result['valid'] is False
        assert result['error'] == 'License expired'
    
    def test_revoke_license(self, sample_product):
        """Test revoking a license."""
        # Create license
        license_key = generate_license_key()
        License.create(sample_product, 'test-user', license_key=license_key)
        
        # Revoke
        result = License.revoke(license_key)
        
        assert result['success'] is True
        assert result['message'] == 'License revoked'


@pytest.mark.usefixtures('app')
class TestProductModel:
    
    def test_create_product(self):
        """Test creating a product."""
        result = Product.create('My App', 'Mobile application', 3)
        
        assert result['success'] is True
        assert 'product_id' in result
        assert isinstance(result['product_id'], int)
    
    def test_get_products_pagination(self):
        """Test getting products with pagination."""
        # Create test products
        Product.create('App 1', 'Description 1')
        Product.create('App 2', 'Description 2')
        Product.create('App 3', 'Description 3')
        
        products, total = Product.get_all(page=1, per_page=2)
        
        assert len(products) == 2
        assert total == 3
        assert 'total_licenses' in products[0]
        assert 'active_licenses' in products[0]
    
    def test_update_product(self, sample_product):
        """Test updating a product."""
        result = Product.update(
            product_id=sample_product,
            name='Updated Product Name',
            max_devices=5
        )
        
        assert result['success'] is True
        assert result['message'] == 'Product updated'
        
        # Verify update
        updated_product = Product.get_by_id(sample_product)
        assert updated_product['name'] == 'Updated Product Name'
        assert updated_product['max_devices'] == 5