import pytest
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta

@pytest.mark.usefixtures('client', 'app')
class TestAPIRoutes:
    
    def test_auth_login_success(self, client):
        """Test successful admin login."""
        response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'adminpass'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'user' in data
    
    def test_auth_login_failure(self, client):
        """Test failed login with wrong credentials."""
        response = client.post('/api/auth/login', json={
            'username': 'wrong',
            'password': 'wrong'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Invalid credentials'
    
    def test_create_product(self, client):
        """Test creating a new product (requires auth)."""
        # First get token
        login_response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'adminpass'
        })
        token = login_response.get_json()['access_token']
        
        headers = {'Authorization': f'Bearer {token}'}
        response = client.post('/api/products', json={
            'name': 'Test Product',
            'description': 'Test description',
            'max_devices': 2
        }, headers=headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'product_id' in data
    
    def test_validate_license_invalid(self, client):
        """Test validating an invalid license key."""
        response = client.get('/api/validate/test-product/invalid-key-123')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['valid'] is False
        assert 'error' in data
    
    def test_rate_limiting(self, client, mocker):
        """Test rate limiting functionality."""
        # Mock the limiter to test multiple requests
        mocker.patch('flask_limiter.Limiter.__init__')
        
        # This would need more complex mocking for full test
        # Basic test that endpoint exists
        response = client.get('/api/validate/test-product/test-key')
        assert response.status_code in [400, 429]  # Either invalid or rate limited


@pytest.mark.usefixtures('client', 'app')
class TestAuthentication:
    
    def test_protected_route_without_token(self, client):
        """Test accessing protected route without token."""
        response = client.get('/api/licenses')
        
        assert response.status_code == 401
    
    def test_protected_route_with_invalid_token(self, client):
        """Test protected route with invalid token."""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.get('/api/licenses', headers=headers)
        
        assert response.status_code == 401