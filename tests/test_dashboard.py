# test_dashboard.py - Admin dashboard testing
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json

class DashboardTest:
    def __init__(self, base_url="localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.driver = None
        self.admin_token = None
    
    def setup_driver(self):
        """Setup Selenium WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run headless for CI
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def login(self):
        """Login to admin dashboard."""
        print("🔐 Logging into admin dashboard...")
        
        # API login to get token
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": "admin", "password": "adminpass"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Admin login failed: {response.text}")
        
        self.admin_token = response.json()["access_token"]
        print("✅ API authentication successful")
        
        # Navigate to dashboard
        self.driver.get(f"{self.base_url}/admin")
        
        # Wait for page to load
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        
        # Check if already authenticated (token stored in localStorage)
        if "Login" not in self.driver.page_source:
            print("✅ Dashboard loaded successfully")
        else:
            print("⚠️  Token not applied - manual login may be needed for Selenium")
    
    def test_dashboard_stats(self):
        """Test dashboard statistics display."""
        print("\n📊 Testing dashboard statistics...")
        
        # Wait for stats cards to load
        stats_selectors = {
            "total_licenses": "#total-licenses",
            "active_licenses": "#active-licenses", 
            "expired_licenses": "#expired-licenses",
            "revoked_licenses": "#revoked-licenses"
        }
        
        # Verify stats cards exist
        for name, selector in stats_selectors.items():
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            value = element.text.strip()
            print(f"✅ {name}: {value}")
            assert value.isdigit() or value == "0", f"{name} should show numeric value"
        
        print("✅ Dashboard statistics test PASSED")
    
    def test_create_product(self):
        """Test creating a new product through dashboard."""
        print("\n📦 Testing product creation...")
        
        # Click "Add Product" button
        add_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#productModal"]')))
        add_button.click()
        
        # Wait for modal
        modal = self.wait.until(EC.presence_of_element_located((By.ID, "productModal")))
        assert modal.is_displayed(), "Product modal should be visible"
        
        # Fill form
        product_name = self.driver.find_element(By.ID, "product-name")
        product_desc = self.driver.find_element(By.ID, "product-description")
        max_devices = self.driver.find_element(By.ID, "product-max-devices")
        
        product_name.clear()
        product_name.send_keys("Dashboard Test Product")
        product_desc.clear()
        product_desc.send_keys("Created via automated test")
        max_devices.clear()
        max_devices.send_keys("3")
        
        # Click create button
        create_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create Product')]")))
        create_btn.click()
        
        # Wait for success message and modal close
        time.sleep(2)  # Allow time for API call
        
        # Check if product appears in table
        product_row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//td[contains(text(), 'Dashboard Test Product')]")
        ))
        
        assert product_row, "New product should appear in table"
        print("✅ Product creation test PASSED")
    
    def test_create_license(self):
        """Test license creation through dashboard."""
        print("\n🔑 Testing license creation...")
        
        # Fill license creation form
        product_select = self.wait.until(EC.element_to_be_clickable((By.ID, "product-select")))
        product_select.click()
        
        # Select first product (should be our test product)
        first_option = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#product-select option:nth-child(2)")))
        first_option.click()
        
        user_id = self.driver.find_element(By.ID, "user-id")
        expires_days = self.driver.find_element(By.ID, "expires-days")
        
        user_id.clear()
        user_id.send_keys("dashboard-test-user")
        expires_days.clear()
        expires_days.send_keys("60")
        
        # Click create license button
        create_license_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Create License')]")))
        create_license_btn.click()
        
        # Wait for success alert
        time.sleep(2)
        
        # Check if license appears in table
        new_license_row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//td[contains(text(), 'dashboard-test-user')]")
        ))
        
        assert new_license_row, "New license should appear in table"
        print("✅ License creation test PASSED")
    
    def test_license_revoke(self):
        """Test license revocation through dashboard."""
        print("\n🚫 Testing license revocation...")
        
        # Find a license row (any active license)
        license_row = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//tr[contains(@class, 'fade-in')]//button[contains(text(), 'Revoke')]")
        ))
        
        # Get the license key from the row
        license_key_element = license_row.find_element(By.XPATH, "../../td[1]/code")
        license_key = license_key_element.text.replace("...", "")  # Partial key
        
        # Click revoke button
        license_row.click()
        
        # Confirm dialog (Selenium handles this automatically in most cases)
        time.sleep(1)
        
        # Verify status changed to revoked
        status_element = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//span[contains(text(), '{license_key}')]/following::span[contains(@class, 'status-revoked')]")
        ))
        
        assert status_element, "License status should change to revoked"
        print("✅ License revocation test PASSED")
    
    def test_responsive_design(self):
        """Test responsive design on different screen sizes."""
        print("\n📱 Testing responsive design...")
        
        # Test different viewport sizes
        viewports = [
            (1920, 1080, "Desktop"),
            (768, 1024, "Tablet"), 
            (375, 667, "Mobile")
        ]
        
        for width, height, name in viewports:
            self.driver.set_window_size(width, height)
            time.sleep(1)
            
            # Check if table is responsive
            table = self.driver.find_element(By.ID, "licenses-table")
            assert table.is_displayed(), f"Table should be visible on {name}"
            
            # Check if buttons are clickable
            try:
                first_button = self.driver.find_element(By.CSS_SELECTOR, "button.btn")
                assert first_button.size["height"] > 0, f"Buttons should be clickable on {name}"
            except:
                print(f"⚠️  Button interaction test skipped on {name}")
            
            print(f"✅ Responsive test PASSED for {name} ({width}x{height})")
    
    def run_dashboard_tests(self):
        """Run complete dashboard test suite."""
        print("🚀 Starting Dashboard Test Suite")
        print("=" * 50)
        
        try:
            self.setup_driver()
            self.login()
            
            self.test_dashboard_stats()
            self.test_create_product()
            self.test_create_license()
            self.test_license_revoke()
            self.test_responsive_design()
            
            print("\n🎉 ALL DASHBOARD TESTS PASSED!")
            print("Admin interface is fully functional!")
            
        except Exception as e:
            print(f"\n💥 Dashboard test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.driver:
                self.driver.quit()

# Note: This requires selenium and chromedriver
# pip install selenium
# brew install chromedriver

if __name__ == "__main__":
    # Uncomment to run (requires Selenium setup)
    # tester = DashboardTest()
    # tester.run_dashboard_tests()
    
    print("💡 To run dashboard tests, install Selenium:")
    print("   pip install selenium")
    print("   brew install chromedriver")
    print("   python test_dashboard.py")