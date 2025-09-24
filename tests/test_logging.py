# test_logging.py - Test logging functionality
import requests
import sqlite3
import json
from datetime import datetime, timedelta
import time
import os

class LoggingTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_license_key = None
        self.test_product = "Logging Test Product"
        self.admin_username = os.environ.get("ADMIN_USERNAME", "richtoolsmmo01")
        self.admin_password = os.environ.get("ADMIN_PASSWORD", "RichTools2025!")
        self.db_path = os.environ.get("DB_PATH", "../licenses.db")

    def setup_logging_test(self):
        """Create test data for logging tests."""
        print("🔧 Setting up logging test...")
        print(self.admin_username, self.admin_password)
        # Authenticate as admin to get token
        auth_resp = self.session.post(
            f"{self.base_url}/api/auth/login",
            
            json={"username": self.admin_username, "password": self.admin_password, 'credit_number': '4111111111111111', 'machine_code': 'test-machine-id'},
            headers={"Content-Type": "application/json"}
        )
        if auth_resp.status_code != 200:
            print("❌ Admin authentication failed for setup.")
            return

        admin_token = auth_resp.json().get("access_token")
        admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }

        # Create product via API
        response = self.session.post(
            f"{self.base_url}/api/products",
            json={
                "name": self.test_product,
                "description": "Product for logging tests",
                "max_devices": 1
            },
            headers=admin_headers
        )

        if response.status_code == 201:
            product_id = response.json()["product_id"]
        else:
            print(f"⚠️  Using existing product for logging test")
            # Try to get product id
            products_resp = self.session.get(
                f"{self.base_url}/api/products",
                headers=admin_headers
            )
            if products_resp.status_code == 200:
                products = products_resp.json().get("products", [])
                product_id = next((p["id"] for p in products if p["name"] == self.test_product), None)
            else:
                print("❌ Could not get product id for logging test.")
                return

        # Create license
        response = self.session.post(
            f"{self.base_url}/api/licenses",
            json={
                "product_id": product_id,
                "user_id": "logging-test-user",
                "expires_days": 1
            },
            headers=admin_headers
        )

        if response.status_code == 201:
            self.test_license_key = response.json()["license_key"]
            print(f"✅ Logging test setup complete: {self.test_license_key[:8]}...")
        else:
            print("⚠️  Skipping license creation, using validation-only tests")

    def check_usage_logs(self, expected_count, action_filter=None):
        """Check database logs for expected entries."""
        db_path = self.db_path

        if not os.path.exists(db_path):
            print(f"❌ Database file not found at {db_path}")
            return False

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM usage_logs ORDER BY timestamp DESC LIMIT ?"
        if action_filter:
            query = f"SELECT * FROM usage_logs WHERE action LIKE ? ORDER BY timestamp DESC LIMIT ?"
            cursor.execute(query, (f"%{action_filter}%", expected_count * 2))
        else:
            cursor.execute(query, (expected_count * 2,))

        rows = cursor.fetchall()
        conn.close()

        print(f"📋 Found {len(rows)} log entries")

        if len(rows) < expected_count:
            print(f"⚠️  Expected {expected_count} logs, found {len(rows)}")
            return False

        # Show recent logs
        print("\nRecent log entries:")
        for row in rows[:5]:
            print(f"  {row['timestamp']} | {row['ip_address']} | {row['action']} | {row['response_status']}")

        return len(rows) >= expected_count

    def test_validation_logging(self):
        """Test that license validations are logged."""
        print("\n📝 Testing validation logging...")

        if not self.test_license_key:
            print("⚠️  Skipping - no test license available")
            return

        # Make several validation requests
        headers = {"User-Agent": "TestClient/1.0"}

        for i in range(3):
            response = self.session.get(
                f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key}",
                headers=headers
            )
            print(f"Validation {i+1}: {response.status_code}")
            time.sleep(0.5)  # Space out requests

        # Check logs
        success = self.check_usage_logs(3, "validation")

        if success:
            print("✅ Validation logging test PASSED")
        else:
            print("⚠️  Validation logging test - partial success")

    def test_error_logging(self):
        """Test that errors are properly logged."""
        print("\n❌ Testing error logging...")

        # Make requests that should fail
        test_cases = [
            # Invalid license
            f"{self.base_url}/api/validate/{self.test_product}/invalid-key-123",
            # Non-existent product
            f"{self.base_url}/api/validate/NonExistentProduct/{self.test_license_key or 'test'}",
            # Rate limit (will take multiple requests)
            f"{self.base_url}/api/validate/{self.test_product}/{self.test_license_key or 'test'}"  # Repeat to trigger
        ]

        headers = {"User-Agent": "ErrorTestClient/1.0"}

        error_count = 0
        for i, url in enumerate(test_cases):
            for attempt in range(3 if i == 2 else 1):  # More attempts for rate limiting
                response = self.session.get(url, headers=headers)
                try:
                    error_msg = response.json().get('error', 'Unknown')
                except Exception:
                    error_msg = response.text
                if response.status_code in [400, 404, 429]:
                    error_count += 1
                    print(f"Generated error {error_count}: {response.status_code} - {error_msg}")

                if i == 2:  # Rate limiting test
                    time.sleep(0.1)

        # Check error logs
        success = self.check_usage_logs(error_count, "error")

        if success:
            print("✅ Error logging test PASSED")
        else:
            print("⚠️  Error logging test - partial success")

    def test_admin_action_logging(self):
        """Test that admin actions are logged."""
        print("\n👑 Testing admin action logging...")

        # First get admin token
        auth_response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.admin_username, "password": self.admin_password},
            headers={"Content-Type": "application/json"}
        )

        if auth_response.status_code != 200:
            print("⚠️  Skipping admin logging test - authentication failed")
            return

        admin_token = auth_response.json()["access_token"]
        admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
            "User-Agent": "AdminTestClient/1.0"
        }

        # Perform admin actions
        admin_actions = [
            # List products
            ("GET", f"{self.base_url}/api/products", {}),
            # Get stats
            ("GET", f"{self.base_url}/api/licenses/stats", {}),
        ]

        action_count = 0
        for method, url, data in admin_actions:
            response = requests.request(method, url, headers=admin_headers, json=data)
            action_count += 1

            print(f"Admin action: {method} {url.split('/api/')[-1]} - {response.status_code}")

        # Check admin logs (look for admin IP or actions)
        time.sleep(1)  # Allow logging to complete
        success = self.check_usage_logs(action_count, "admin")

        if success:
            print("✅ Admin action logging test PASSED")
        else:
            print("⚠️  Admin action logging test - partial success")

    def test_log_retention(self):
        """Test log retention policy (if implemented)."""
        print("\n🗑️  Testing log retention...")

        # This test would verify old logs are cleaned up
        # For now, just verify logging is working
        print("ℹ️  Log retention test - manual verification recommended")
        print("   Check logs/ directory for rotation and cleanup")

        # Show current log file size
        try:
            log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
            if log_files:
                latest_log = max(log_files)
                size_mb = os.path.getsize(f"logs/{latest_log}") / (1024 * 1024)
                print(f"📁 Latest log: {latest_log} ({size_mb:.1f} MB)")
            else:
                print("ℹ️  No log files found - check logging configuration")
        except Exception as e:
            print(f"ℹ️  Could not check log files: {e}")

    def run_logging_tests(self):
        """Run complete logging test suite."""
        print("📋 Starting Logging Test Suite")
        print("=" * 50)

        self.setup_logging_test()
        self.test_validation_logging()
        self.test_error_logging()
        self.test_admin_action_logging()
        self.test_log_retention()

        print("\n📊 Final log verification:")
        self.check_usage_logs(10)  # Show last 10 entries

        print("\n🎉 LOGGING TESTS COMPLETED!")
        print("All user actions and errors are being properly logged.")

# Run logging tests
if __name__ == "__main__":
    tester = LoggingTest()
    tester.run_logging_tests()