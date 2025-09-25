# test_security.py - Security and anti-spam tests
import requests
import time
from concurrent.futures import ThreadPoolExecutor
import json

class SecurityTestSuite:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_license_key = ""
        self.test_product = ""
        self.admin_username = "richtoolsmmo01"
        self.admin_password = "RichTools2025!"  # <-- Set your admin password here

    def setup_security_test(self):
        print("🔧 Setting up security test environment...")

        # Login as admin and set JWT token
        login_resp = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.admin_username, "password": self.admin_password}
        )
        assert login_resp.status_code == 200, "Login failed for security test"
        token = login_resp.json().get("access_token")
        assert token, "No access token received"
        self.session.headers.update({"Authorization": f"Bearer {token}"})

        # Get Test License Key
        resp = self.session.get(f"{self.base_url}/api/licenses/test/data")
        assert resp.status_code == 200, "Failed to get test license data"
        data = resp.json()
        self.test_license_key = data.get("key")
        self.test_product = data.get("product_name")
        assert self.test_license_key and self.test_product, "Test license data incomplete"

        # Create test product if not exists
        resp = self.session.get(f"{self.base_url}/api/products/all")
        products = resp.json().get("products", [])
        if not any(p["name"] == self.test_product for p in products):
            create_resp = self.session.post(
                f"{self.base_url}/api/products",
                json={"name": self.test_product, "max_devices": 1}
            )
            assert create_resp.status_code == 201, "Failed to create test product"

        print("✅ Security test environment ready")

    def test_sql_injection(self):
        print("\n🛡️ Testing SQL injection protection...")
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE licenses; --",
            "1; SELECT * FROM licenses WHERE status='active'",
            "admin' --",
            "'; EXEC xp_cmdshell('dir') --"
        ]
        headers = {"Content-Type": "application/json"}
        for input_val in malicious_inputs:
            response = self.session.get(
                f"{self.base_url}/api/validate/{self.test_product}/{input_val}",
                headers=headers
            )
            assert response.status_code in [400, 404], \
                f"SQL injection test failed for '{input_val[:20]}...' - Status: {response.status_code}"
            data = response.json()
            assert "sql" not in str(data).lower(), \
                f"SQL error exposed in response for '{input_val[:20]}...'"
            print(f"✅ SQL injection blocked: {input_val[:20]}...")
        print("✅ SQL injection protection PASSED")

    def test_xss_protection(self):
        print("\n🛡️ Testing XSS protection...")
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "data:text/html,<script>alert('xss')</script>"
        ]
        headers = {"Content-Type": "application/json"}
        for input_val in xss_inputs:
            response = self.session.post(
                f"{self.base_url}/api/licenses",
                json={
                    "product_id": 1,
                    "user_id": input_val,
                    "expires_days": 1
                },
                headers=headers
            )
            
            # Accept 400, 401, or 422 as valid rejections
            assert response.status_code in [400, 401, 422], \
                f"XSS input accepted: {input_val[:20]}... - Status: {response.status_code}"
            print(f"✅ XSS blocked: {input_val[:20]}...")
        print("✅ XSS protection PASSED")

    def test_rate_limiting_stress(self):
        print("\n⏱️  Testing rate limiting under stress...")
        response = requests.get(
                f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
                timeout=5
            )
        def make_request(_):
            try:
                response = requests.get(
                   f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
                    timeout=5
                )                
                return response.status_code
            except:
                return 500
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))  # Try 20 requests
        duration = time.time() - start_time
        print("Response codes:", results)
        success_count = results.count(200)
        rate_limited = results.count(429)
        errors = len([r for r in results if r not in [200, 429]])
        print(f"📊 Results: {success_count} success, {rate_limited} rate-limited, {errors} errors")
        print(f"⏱️  Duration: {duration:.2f}s ({20/duration:.1f} req/s)")
        assert rate_limited > 0, "Expected rate limiting to trigger"
        assert errors == 0, f"Unexpected errors: {errors}"
        print("✅ Rate limiting stress test PASSED")

    def test_once(self):
        response = requests.get(
            f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
            timeout=10
        )
        print("\n🔍 Testing single validation...")
        print(response.json())
        assert response.status_code == 200, f"Once test failed - Status: {response.status_code}"
        data = response.json()
        assert data["valid"] is True, "Valid license key marked as invalid"
        print("✅ Once test PASSED")

    def test_concurrent_validation(self):
        print("\n🔄 Testing concurrent validation...")
        def validate_concurrently(license_key, index):
            response = requests.get(
                f"{self.base_url}/api/validate/{self.test_product}/{license_key}",
                timeout=10
            )
            return {
                "index": index,
                "status": response.status_code,
                "valid": response.json().get("valid") if response.status_code == 200 else None,
                "usage_count": response.json().get("usage_count") if response.status_code == 200 else None
            }
        futures = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            for i in range(20):
                future = executor.submit(validate_concurrently, self.test_license_key, i)
                futures.append(future)
        results = [future.result() for future in futures]
        valid_results = [r for r in results if r["status"] == 200 and r["valid"] is True]
        usage_counts = [r["usage_count"] for r in valid_results]
        expected_sequence = list(range(1, len(valid_results) + 1))
        actual_sequence = sorted(usage_counts)
        print(f"📊 {len(valid_results)}/{len(results)} successful validations")
        print(f"🔢 Usage counts: {actual_sequence[:5]}... (showing first 5)")
        sequence_ok = all(actual_sequence[i] == expected_sequence[i] for i in range(min(len(actual_sequence), len(expected_sequence))))
        assert sequence_ok, "Race condition detected in usage counting"
        assert len(valid_results) > 0, "No successful validations"
        print("✅ Concurrent validation test PASSED")

    def test_license_key_cracking_resistance(self):
        print("\n🔒 Testing license key cracking resistance...")
        attack_patterns = [
            "0000000000000000",
            "1111111111111111",
            "abcdefghijklmnopqrstuvwxyz",
            "1234567890abcdef",
            "AAAAAAAAAA",
            "testtesttesttest",
        ]
        headers = {"Content-Type": "application/json"}
        for pattern in attack_patterns:
            test_key = (pattern * 2)[:16]
            response = self.session.get(
                f"{self.base_url}/api/validate/{self.test_product}/{test_key}",
                headers=headers
            )
            assert response.status_code in [400, 429], \
                f"Cracking pattern '{test_key}' was accepted - Status: {response.status_code}"
            data = response.json()
            if(data.get("error", "").lower().find("rate limit") != -1):
                return
            assert data["valid"] is False, "Invalid key was marked as valid"
            assert "not found" in data["error"].lower(), "Didn't get expected error"
            time.sleep(0.1)
        print("✅ License key cracking resistance PASSED")

    def run_all_security_tests(self):
        print("🚀 Starting Security Test Suite")
        print("=" * 50)
        self.setup_security_test()
        self.test_once()
        self.test_sql_injection()
        self.test_xss_protection()
        self.test_rate_limiting_stress()
        self.test_license_key_cracking_resistance()
        print("\n🎉 ALL SECURITY TESTS PASSED!")
        print("Your license server is resistant to common attacks!")

if __name__ == "__main__":
    tester = SecurityTestSuite()
    tester.run_all_security_tests()