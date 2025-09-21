import pytest
from flask import url_for
import json


@pytest.mark.usefixtures('client', 'app')
class TestIntegration:
    
    def test_full_workflow(self, client):
        """Test complete workflow: login -> create product -> create license -> validate."""
        
        # Step 1: Login
        login_response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'adminpass'
        })
        assert login_response.status_code == 200
        token = login_response.get_json()['access_token']
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: Create product
        product_response = client.post('/api/products', json={
            'name': 'Integration Test Product',
            'description': 'Created for testing',
            'max_devices': 1
        }, headers=headers)
        
        assert product_response.status_code == 201
        product_data = product_response.get_json()
        product_id = product_data['product_id']
        
        # Step 3: Create license
        license_response = client.post('/api/licenses', json={
            'product_id': product_id,
            'user_id': 'integration-test-user',
            'expires_days': 30
        }, headers=headers)
        
        assert license_response.status_code == 201
        license_data = license_response.get_json()
        license_key = license_data['license_key']
        
        # Step 4: Validate license
        validate_response = client.get(
            f'/api/validate/Integration Test Product/{license_key}'
        )
        
        assert validate_response.status_code == 200
        validate_data = validate_response.get_json()
        assert validate_data['valid'] is True
        assert validate_data['product_name'] == 'Integration Test Product'
    
    def test_error_handling(self, client):
        """Test various error conditions."""
        
        # Invalid JSON
        response = client.post('/api/auth/login', data='invalid json')
        assert response.status_code == 400
        
        # Missing required fields
        response = client.post('/api/products', json={
            'description': 'Only description'
        }, headers={'Authorization': 'Bearer dummy'})
        assert response.status_code == 400
        
        # Unauthorized access
        response = client.get('/api/licenses')
        assert response.status_code == 401
        
        # Non-existent product validation
        response = client.get('/api/validate/nonexistent-product/test-key')
        assert response.status_code == 400
        data = response.get_json()
        assert data['valid'] is False
        assert 'Product not found' in data['error']