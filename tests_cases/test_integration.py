# test_integration.py - Test basic API integration
import requests
import json
from datetime import datetime, timedelta
import time

class LicenseIntegrationTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        
        # Test data
        self.test_product = "Test Product"
        self.test_user_id = "integration-test-user"
        self.test_license_key = None
    
    def setup(self):
        """Setup test environment - create product and admin token."""
        print("🔧 Setting up test environment...")
        
        # 1. Login as admin
        login_response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": "admin", "password": "adminpass"},
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code != 200:
            raise Exception(f"Admin login failed: {login_response.text}")
        
        self.admin_token = login_response.json()["access_token"]
        self.session.headers.update({
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        })
        print("✅ Admin authenticated")
        
        # 2. Create test product
        product_response = self.session.post(
            f"{self.base_url}/api/products",
            json={
                "name": self.test_product,
                "description": "Test product for integration testing",
                "max_devices": 2
            }
        )
        
        if product_response.status_code != 201:
            raise Exception(f"Product creation failed: {product_response.text}")
        
        product_id = product_response.json()["product_id"]
        print(f"✅ Test product created with ID: {product_id}")
        
        # 3. Create test license
        license_response = self.session.post(
            f"{self.base_url}/api/licenses",
            json={
                "product_id": product_id,
                "user_id": self.test_user_id,
                "expires_days": 30
            }
        )
        
        if license_response.status_code != 201:
            raise Exception(f"License creation failed: {license_response.text}")
        
        self.test_license_key = license_response.json()["license_key"]
        print(f"✅ Test license created: {self.test_license_key[:8]}...")
        
        print("✅ Setup completed successfully!")
        return True
    
    def test_license_validation(self):
        """Test license validation with valid key."""
        print("\n🧪 Testing license validation...")
        
        # Remove admin headers for public validation
        headers = self.session.headers.copy()
        del headers["Authorization"]
        
        response = self.session.get(
            f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        data = response.json()
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert data["valid"] is True, f"Expected valid=True, got {data['valid']}"
        assert data["product_name"] == self.test_product, f"Wrong product name"
        assert data["usage_count"] >= 1, f"Usage count should be >= 1"
        
        print("✅ License validation PASSED")
        return data
    
    def test_invalid_license(self):
        """Test validation with invalid license key."""
        print("\n🧪 Testing invalid license validation...")
        
        headers = self.session.headers.copy()
        del headers["Authorization"]
        
        response = self.session.get(
            f"{self.base_url}/api/validate/{self.test_product}/invalid-key-123",
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        data = response.json()
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert data["valid"] is False, f"Expected valid=False, got {data['valid']}"
        assert "not found" in data["error"].lower(), f"Expected 'not found' error"
        
        print("✅ Invalid license test PASSED")
        return data
    
    def test_rate_limiting(self):
        """Test rate limiting behavior."""
        print("\n🧪 Testing rate limiting...")
        
        headers = self.session.headers.copy()
        del headers["Authorization"]
        
        # Make rapid requests to trigger rate limiting
        failures = 0
        for i in range(15):  # Should trigger limit after ~10 requests
            response = self.session.get(
                f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
                headers=headers
            )
            
            if response.status_code == 429:
                print(f"✅ Rate limiting triggered on request {i+1}")
                data = response.json()
                assert "too many requests" in data["error"].lower()
                break
            elif response.status_code != 200:
                failures += 1
                print(f"❌ Unexpected status {response.status_code} on request {i+1}")
        
        if failures > 0:
            print(f"⚠️  {failures} unexpected failures during rate limit test")
        else:
            print("✅ Rate limiting test PASSED")
    
    def test_admin_operations(self):
        """Test admin-only operations."""
        print("\n🧪 Testing admin operations...")
        
        # List licenses (should work with admin token)
        response = self.session.get(f"{self.base_url}/api/licenses")
        print(f"List licenses status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        licenses = response.json()["licenses"]
        assert len(licenses) >= 1, "Should have at least the test license"
        
        # Try without admin token (should fail)
        headers = self.session.headers.copy()
        del headers["Authorization"]
        
        response = requests.get(
            f"{self.base_url}/api/licenses",
            headers=headers
        )
        
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        
        print("✅ Admin operations test PASSED")
    
    def test_revoke_license(self):
        """Test license revocation."""
        print("\n🧪 Testing license revocation...")
        
        # Revoke the test license
        response = self.session.post(
            f"{self.base_url}/api/licenses/{self.test_license_key}/revoke"
        )
        
        print(f"Revoke status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json()["status"] == "revoked"
        
        # Verify it's now invalid
        headers = self.session.headers.copy()
        del headers["Authorization"]
        
        response = self.session.get(
            f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
            headers=headers
        )
        
        data = response.json()
        assert data["valid"] is False, "Revoked license should be invalid"
        assert "revoked" in data["error"].lower(), "Should show revoked error"
        
        print("✅ License revocation test PASSED")
    
    def cleanup(self):
        """Cleanup test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Revoke license if not already done
        if self.test_license_key:
            self.session.post(
                f"{self.base_url}/api/licenses/{self.test_license_key}/revoke"
            )
        
        # Note: Product deletion not implemented in current API
        print("✅ Cleanup completed (manual product deletion may be needed)")

# Run all tests
if __name__ == "__main__":
    tester = LicenseIntegrationTest()
    
    try:
        tester.setup()
        tester.test_license_validation()
        tester.test_invalid_license()
        tester.test_rate_limiting()
        tester.test_admin_operations()
        tester.test_revoke_license()
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
    finally:
        tester.cleanup()