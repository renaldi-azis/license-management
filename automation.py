# test_security.py - Security and anti-spam tests
import requests
from getpass import getpass
import json

class LicenseRegisterSuite:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.username = username
        self.password = password
        pass

    def setup_security_test(self):
        try:
            # Login as admin and set JWT token
            login_resp = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password}
            )
            login_resp.raise_for_status()
            token = login_resp.json().get("access_token")
            # Print response details
            print(f"\nRequest successful!")
            print(f"Status Code: {login_resp.status_code}")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error occurred: {err}")
            if login_resp.status_code == 401:
                print("Authentication failed - check username/password")
        except requests.exceptions.ConnectionError as err:
            print(f"Connection Error: Cannot connect to server - {err}")
        except requests.exceptions.Timeout as err:
            print(f"Timeout Error: Request took too long - {err}")
        except requests.exceptions.RequestException as err:
            print(f"An error occurred: {err}")
        except Exception as err:
            print(f"Unexpected error: {err}")
        
    # register a license by userId, product_name, and machine_code
    def register_license(self, user_id, product_name, machine_code):
        try:
            resp = self.session.post(
                f"{self.base_url}/api/licenses/automate",
                json={
                    "user_id": user_id,
                    "product_name": product_name,
                    "machine_code": machine_code
                }
            )
            resp.raise_for_status()
            print(f"\nRequest successful!")
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {json.dumps(resp.json(), indent=2)}")
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error occurred: {err}")
            if resp.status_code == 400:
                print("Bad Request - likely due to invalid input or existing active license")
            elif resp.status_code == 403:
                print("Forbidden - admin access required")
            elif resp.status_code == 404:
                print("Not Found - product or settings not found")
        except requests.exceptions.ConnectionError as err:
            print(f"Connection Error: Cannot connect to server - {err}")
        except requests.exceptions.Timeout as err:
            print(f"Timeout Error: Request took too long - {err}")
        except requests.exceptions.RequestException as err:
            print(f"An error occurred: {err}")
        except Exception as err:
            print(f"Unexpected error: {err}")
    
    
if __name__ == "__main__":    
    server_url = input("Enter server URL: ").strip()
    username = input("Enter username: ").strip()
    password = getpass("Enter password: ").strip()
    tester = LicenseRegisterSuite(server_url, username, password)
    tester.setup_security_test()

    test_data=[{"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # Valid
               {"user_id": "<script>alert(1)</script>", "product_name": "ProductA", "machine_code": "MACHINE123"}, # XSS
               {"user_id": "user2", "product_name": "NonExistentProduct", "machine_code": "MACHINE456"}, # Non-existent product
               {"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # Duplicate active license
               {"user_id": "user3", "product_name": "ProductA", "machine_code": "<img src=x onerror=alert(1)>"}] # XSS

    for td in test_data:
        print(f"\nTesting with user_id: {td['user_id']}, product_name: {td['product_name']}, machine_code: {td['machine_code']}")
        tester.register_license(td['user_id'], td['product_name'], td['machine_code'])