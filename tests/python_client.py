# client.py
import requests
import json
import base64
import secrets
from getpass import getpass
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding
from urllib.parse import quote
from HttpAntiDebug import SessionServer as SV
import os

class SecureLicenseClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.client_id = 'x-client'
        self.session_id = None
        self.aes_key = None
        self.server_public_key = None
        self.client_private_key = None
        self.client_public_key = None
        self.access_token = None
        self.access_token_cookie = None
        self.anti_debug_session = SV(server_url)
        self.test_license_key=""
        self.test_product=""
        
        # Set default headers for HttpAntiDebug
        self.anti_debug_session.headers.update({
            'X-Client-ID': self.client_id,
            'Content-Type': 'application/json'
        })

    def initialize_session(self):
        """Initialize session with server using HttpAntiDebug"""
        try:
            response = self.anti_debug_session.get(f"/init-session")
            print(f"Init session status: {response.status_code}")
            print(f"Init session response: {response.text}")
            
            if response.status_code == 200:
                # Handle HttpAntiDebug response
                if hasattr(response, 'json') and callable(response.json):
                    data = response.json()
                else:
                    data = json.loads(response.text)
                
                self.session_id = data['session_id']
                self.server_public_key = self.import_public_key(data['server_public_key'])
                
                # Update session ID header
                self.anti_debug_session.headers.update({'X-Session-ID': self.session_id})
                return True
            return False
        except Exception as error:
            print(f'Session initialization failed: {error}')
            return False

    def base64_to_bytes(self, base64_string):
        """Convert base64 string to bytes"""
        return base64.b64decode(base64_string)

    def bytes_to_base64(self, data_bytes):
        """Convert bytes to base64 string"""
        return base64.b64encode(data_bytes).decode('utf-8')

    def import_public_key(self, pem_string):
        """Import public key from PEM string"""
        try:
            # Load public key directly from PEM format
            public_key = serialization.load_pem_public_key(
                pem_string.encode('utf-8')
            )
            return public_key
        except Exception as e:
            print(f"Error importing public key: {e}")
            raise

    def generate_key_pair(self):
        """Generate RSA key pair for client"""
        self.client_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.client_public_key = self.client_private_key.public_key()

    def export_public_key(self):
        """Export public key to PEM format"""
        public_key_bytes = self.client_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes.decode('utf-8')

    def perform_key_exchange(self):
        """Perform RSA key exchange with server using HttpAntiDebug"""
        print("Performing key exchange...")
        try:
            # Generate client key pair
            self.generate_key_pair()
            
            # Generate AES key
            self.aes_key = secrets.token_bytes(32)  # 256-bit AES key
            
            # Encrypt AES key with server's public key
            encrypted_aes_key = self.server_public_key.encrypt(
                self.aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Export client public key
            client_public_key_pem = self.export_public_key()            
            
            print(f"Key exchange payload prepared")
            
             # METHOD 1: Try to send as raw JSON with proper Content-Type
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Client-ID': self.client_id,
                'X-Session-ID': self.session_id
            }

            # Prepare JSON payload as string
            json_payload = json.dumps({
                'session_id': self.session_id,
                'encrypted_aes_key': self.bytes_to_base64(encrypted_aes_key),
                'client_public_key': client_public_key_pem
            })            
            form_payload = {'json_data': json_payload}
            response = self.anti_debug_session.post(
                f"/key-exchange",
                data=form_payload,
                headers=headers
            )
            
            print(f"Key exchange status: {response.status_code}")
            print(f"Key exchange response: {response.text}")
            
            if response.status_code == 200:
                # Handle HttpAntiDebug response
                if hasattr(response, 'json') and callable(response.json):
                    result = response.json()
                else:
                    result = json.loads(response.text)
                print(f"Key exchange result: {result}")
                return True
            
            return False
            
        except Exception as error:
            print(f'Key exchange failed: {error}')
            import traceback
            traceback.print_exc()
            return False

    def pkcs7_pad(self, data):
        """PKCS7 padding implementation"""
        block_size = 16
        pad_length = block_size - (len(data) % block_size)
        padding = bytes([pad_length] * pad_length)
        return data + padding

    def pkcs7_unpad(self, data):
        """PKCS7 unpadding implementation"""
        pad_length = data[-1]
        if pad_length > len(data):
            raise ValueError("Invalid padding")
        # Verify padding bytes
        for i in range(1, pad_length + 1):
            if data[-i] != pad_length:
                raise ValueError("Invalid padding")
        return data[:-pad_length]

    def aes_encrypt(self, data):
        """Encrypt data with AES-CBC with PKCS7 padding"""
        try:
            # Generate random IV
            iv = secrets.token_bytes(16)
            
            # Convert data to JSON string and encode to bytes
            if isinstance(data, dict):
                data_str = json.dumps(data, ensure_ascii=False)
            else:
                data_str = str(data)
            data_bytes = data_str.encode('utf-8')
            
            # Apply PKCS7 padding
            padded_data = self.pkcs7_pad(data_bytes)
            
            # Encrypt
            cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                'iv': self.bytes_to_base64(iv),
                'data': self.bytes_to_base64(encrypted)
            }
            
        except Exception as error:
            print(f'Encryption failed: {error}')
            raise

    def aes_decrypt(self, encrypted_data):
        """Decrypt AES-CBC encrypted data with PKCS7 unpadding"""
        try:
            if encrypted_data is None:
                raise ValueError("Encrypted data is None")
                
            print("AES_DECRYPT input:", encrypted_data)
            
            # Handle string input (base64 encoded JSON)
            if isinstance(encrypted_data, str):
                # Base64 decode the string
                decoded_bytes = base64.b64decode(encrypted_data)
                decoded_str = decoded_bytes.decode('utf-8')
                print(decoded_str)
                encrypted_data = json.loads(decoded_str)
            
            print("AES_DECRYPT parsed:", encrypted_data)
            
            # Extract IV and encrypted data
            iv = self.base64_to_bytes(encrypted_data['iv'])
            encrypted_bytes = self.base64_to_bytes(encrypted_data['data'])
            
            # Decrypt
            cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            # Remove PKCS7 padding
            decrypted = self.pkcs7_unpad(decrypted_padded)
            
            # Parse JSON and return
            result = json.loads(decrypted.decode('utf-8'))
            print("AES_DECRYPT result:", result)
            return result
            
        except Exception as error:
            print(f'Decryption failed: {error}')
            import traceback
            traceback.print_exc()
            raise

    def login_user(self, username, password):
        """Login user using HttpAntiDebug and manual cookie handling"""
        try:
            # Prepare JSON payload as string
            json_payload = json.dumps({
                'username': username,
                'password': password
            })
            
            # Send login request with HttpAntiDebug
            headers = self.anti_debug_session.headers.copy()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            form_payload = {'json_data': json_payload}
            response = self.anti_debug_session.post(
                f"/api/auth/login",
                data=form_payload,
                headers=headers
            )            
            print(f"Login status: {response.status_code}")
            print(f"Login response: {response.text}")
            
            if response.status_code == 200:
                # Handle HttpAntiDebug response
                if hasattr(response, 'json') and callable(response.json):
                    token_data = response.json()
                else:
                    token_data = json.loads(response.text)
                
                self.access_token = token_data.get("access_token")
                
                if self.access_token:
                    # Store the token as our cookie (since HttpAntiDebug might not handle cookies well)
                    self.access_token_cookie = self.access_token
                    print(f"Stored access token as cookie: {self.access_token_cookie}")
                    
                    # Also set Authorization header
                    self.anti_debug_session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                    return True
            
            return False
        except Exception as e:
            print(f"Login failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _make_authenticated_request(self, method, endpoint, data=None):
        """Make authenticated request with HttpAntiDebug and manual cookie handling"""
        try:
            # Prepare headers with manual cookie
            headers = self.anti_debug_session.headers.copy()
            
            # Add manual cookie header if we have the token
            if self.access_token_cookie:
                headers['Cookie'] = f'access_token_cookie={self.access_token_cookie}'
            
            if method.upper() == 'GET':
                response = self.anti_debug_session.get(endpoint, headers=headers)
            elif method.upper() == 'POST':
                if data:
                    # For POST requests, use form data
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    json_payload = json.dumps(data)
                    form_data = {"json_data" : json_payload}
                    response = self.anti_debug_session.post(endpoint, data=form_data, headers=headers)
                else:
                    response = self.anti_debug_session.post(endpoint, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
            
        except Exception as e:
            raise

    def get_all_licenses(self):
        """Get all licenses using HttpAntiDebug with manual cookie"""
        try:
            page = 1
            query = ""
            endpoint = f"/api/licenses?page={page}&query={quote(query)}"
            
            response = self._make_authenticated_request('GET', endpoint)
            
            print(f"Get licenses status: {response.status_code}")
            print(f"Get licenses response: {response.text}")
            
            if response.status_code == 200:
                # Handle HttpAntiDebug response
                if hasattr(response, 'json') and callable(response.json):
                    res_encrypted = response.json()
                else:
                    res_encrypted = json.loads(response.text)
                    
                encryptedRes = res_encrypted.get("encrypted_data")
                if encryptedRes:
                    res = self.aes_decrypt(encryptedRes)
                    print("Decrypted licenses:", res)
                    return res
            elif response.status_code == 401:
                print("Authentication failed even with manual cookie")
                print("Trying alternative approach...")
                # Try without manual cookie, maybe server sets it automatically
                return self._get_licenses_without_manual_cookie()
            return None
        except Exception as e:
            print(f"Get licenses failed: {e}")
            return None

    def _get_licenses_without_manual_cookie(self):
        """Alternative approach without manual cookie"""
        try:
            page = 1
            query = ""
            
            # Try with just Authorization header
            response = self.anti_debug_session.get(
                f"/api/licenses?page={page}&query={quote(query)}"
            )
            
            print(f"Alternative get licenses status: {response.status_code}")
            
            if response.status_code == 200:
                if hasattr(response, 'json') and callable(response.json):
                    res_encrypted = response.json()
                else:
                    res_encrypted = json.loads(response.text)
                    
                encryptedRes = res_encrypted.get("encrypted_data")
                if encryptedRes:
                    res = self.aes_decrypt(encryptedRes)
                    print("Decrypted licenses (alternative):", res)
                    return res
            return None
        except Exception as e:
            print(f"Alternative get licenses failed: {e}")
            return None

    def send_encrypted_post_request(self, endpoint, data):
        """Send encrypted POST request using HttpAntiDebug"""
        try:
            # Encrypt the request data
            encrypted_request = self.aes_encrypt(data)
            # print(f"Encrypted request prepared")
            
            # Prepare payload as form data
            encrypted_request_json = json.dumps(encrypted_request)
            payload = {'encryptedRequest': encrypted_request_json}
            
            response = self._make_authenticated_request(
                'POST', 
                f"/api/{endpoint.lstrip('/')}", 
                payload
            )
            
            if response.status_code == 200:
                # Handle HttpAntiDebug response
                encrypted_response = None
                if hasattr(response, 'json') and callable(response.json):
                    encrypted_response = response.json()
                else:
                    encrypted_response = json.loads(response.text)
                encryptedRes = encrypted_response.get("encrypted_data")
                if encryptedRes:
                    res = self.aes_decrypt(encryptedRes)
                return res
            else:
                result = json.loads(response.text)
                result['status'] = response.status_code
                return result
                
        except Exception as error:
            return {'error': f'Request failed: {str(error)}'}
    
    def register_license(self, user_id, product_name, machine_code):
        """Register a license"""
        data = {
            "user_id": user_id,
            "product_name": product_name,
            "machine_code": machine_code
        }
        response = self.send_encrypted_post_request('/licenses/automate', data)
        return response
    def get_test_data(self):
        resp = self.anti_debug_session.get(f"/api/licenses/test/data")
        assert resp.status_code == 200, "Failed to get test license data"
        if hasattr(resp, 'json') and callable(resp.json):
            res_encrypted = resp.json()
        else:
            res_encrypted = json.loads(resp.text)
            
        encryptedRes = res_encrypted.get("encrypted_data")
        if encryptedRes:
            res = self.aes_decrypt(encryptedRes)
        res = json.loads(res)
        self.test_license_key = res.get("key")
        self.test_product = res.get("product_name")
        assert self.test_license_key and self.test_product, "Test license data incomplete"
        return True
    
    def check_license_validate(self, t_license_key, t_product_name, t_machine_code):        
        resp = self.send_encrypted_post_request('/validate/', {
            "license_key": t_license_key,
            "product_name": t_product_name,
            "machine_code": t_machine_code
        })
        print("License validation response:", resp)
        return resp

    def update_credit_number(self, license_key, used_credits):
        """Update credit number for a license"""
        data = {
            "license_key": license_key,
            "used_credits": used_credits
        }
        response = self.send_encrypted_post_request('/licenses/update/credit-number', data)
        return response

# Usage example
if __name__ == "__main__":
    server_url = input("Enter server URL (e.g., https://www.richtoolsquantri.online): ").strip()
    client = SecureLicenseClient(server_url)
    
    if client.initialize_session():
        print("Session initialized successfully")
        if client.perform_key_exchange():
            print("Key exchange successful")
            
            # Example: Login
            username = input("Enter username: ").strip()
            password = getpass("Enter password: ").strip()
            
            if client.login_user(username, password):
                print("Login successful")
                # Test getting licenses
                # licenses = client.get_all_licenses()
                # if licenses:
                #     print("Fetched all licenses successfully")
                # else:
                #     print("Failed to fetch licenses")
                
                # # Test data
                # test_data=[{"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # This is valid data
                #     {"user_id": "<script>alert(1)</script>", "product_name": "ProductA", "machine_code": "MACHINE123"}, # XSS => this data includes XSS
                #     {"user_id": "user2", "product_name": "NonExistentProduct", "machine_code": "MACHINE456"}, # Non-existent product
                #     {"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # Duplicate active license, this includes same values with first data so => fails
                #     {"user_id": "user3", "product_name": "ProductA", "machine_code": "<img src=x onerror=alert(1)>"},
                #     {"user_id":"user4", "product_name":"ProductA","machine_code":"MACHINE123"}] # XSS => this also includes XSS
                
                # for td in test_data:
                #     print(f"\nTesting with user_id: {td['user_id']}, product_name: {td['product_name']}, machine_code: {td['machine_code']}")
                #     result = client.register_license(td['user_id'], td['product_name'], td['machine_code'])
                #     print(f"Result: {result}")
                
                # # validation test
                # validate_test_data = [{"product_name": "ProductA", "machine_code": "MACHINE1234","license_key": "9vpNiWsU8nsT9CnE"}] # This is valid data
                # for td in validate_test_data:
                #     print(f"\nTesting validation with product_name: {td['product_name']}, license_key: {td['license_key']}, machine_code: {td['machine_code']}")
                #     result = client.check_license_validate(td['license_key'], td['product_name'], td['machine_code'])
                #     print(f"Validation Result: {result}")

                client.update_credit_number("e8tYhqwQ5OgcA3TN", 10)

            else:
                print("Login failed")
        else:
            print("Key exchange failed")
    else:
        print("Failed to initialize session")