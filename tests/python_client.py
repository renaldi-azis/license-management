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
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for testing

    def initialize_session(self):
        """Initialize session with server"""
        try:
            self.session.headers.update({
                'X-Client-ID': self.client_id,
                'Content-Type': 'application/json'
            })
            
            response = self.session.get(f"{self.server_url}/init-session")
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data['session_id']
                self.server_public_key = self.import_public_key(data['server_public_key'])
                
                # Set session ID header for future requests
                self.session.headers.update({'X-Session-ID': self.session_id})
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
            # Remove PEM headers and whitespace
            pem_clean = pem_string.replace('-----BEGIN PUBLIC KEY-----', '')\
                                 .replace('-----END PUBLIC KEY-----', '')\
                                 .replace('\n', '')\
                                 .strip()
            
            # Decode base64 and load public key
            public_key_bytes = base64.b64decode(pem_clean)
            public_key = serialization.load_der_public_key(public_key_bytes)
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
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')
        return f"-----BEGIN PUBLIC KEY-----\n{public_key_b64}\n-----END PUBLIC KEY-----"

    def perform_key_exchange(self):
        """Perform RSA key exchange with server"""
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
            
            # Send key exchange request
            response = self.session.post(
                f"{self.server_url}/key-exchange",
                json={
                    'session_id': self.session_id,
                    'encrypted_aes_key': self.bytes_to_base64(encrypted_aes_key),
                    'client_public_key': client_public_key_pem
                }
            )
            
            return response.status_code == 200
            
        except Exception as error:
            print(f'Key exchange failed: {error}')
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
        return data[:-pad_length]

    def aes_encrypt(self, data):
        """Encrypt data with AES-CBC with PKCS7 padding"""
        try:
            # Generate random IV
            iv = secrets.token_bytes(16)
            
            # Convert data to JSON string and encode to bytes
            if isinstance(data, dict):
                data_str = json.dumps(data)
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
            # Handle string input (base64 encoded JSON)
            if isinstance(encrypted_data, str):
                # Base64 decode the string
                decoded_bytes = base64.b64decode(encrypted_data)
                decoded_str = decoded_bytes.decode('utf-8')
                encrypted_data = json.loads(decoded_str)
            
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
            return json.loads(decrypted.decode('utf-8'))
            
        except Exception as error:
            print(f'Decryption failed: {error}')
            raise

    def send_encrypted_post_request(self, endpoint, data):
        """Send encrypted POST request to server"""
        try:
            # Encrypt the request data
            encrypted_request = self.aes_encrypt(data)
            print(f"Encrypted request: {encrypted_request}")
            
            # Send request
            response = self.session.post(
                f"{self.server_url}/api/{endpoint}",
                json={'encryptedRequest': encrypted_request},
                verify=False
            )
            
            if response.status_code == 200:
                encrypted_response = response.json()
                return self.aes_decrypt(encrypted_response)
            else:
                return {'error': f'Request failed: {response.status_code}'}
                
        except Exception as error:
            return {'error': f'Request failed: {str(error)}'}
    
    def login_user(self, username, password):
        """Login user and obtain JWT token"""
        login_resp = self.session.post(f"{self.server_url}/api/auth/login", json={
            'username': username,
            'password': password
        },verify=False)
        print(login_resp.json())
        assert login_resp.status_code == 200, "Login failed for test"
        token = login_resp.json().get("access_token")
        assert token, "No access token received"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return True

    def get_all_licenses(self):
        """Get all licenses"""
        page = 1
        query = ""
        res_encrypted = self.session.get(f"{self.server_url}/api/licenses?page={page}&query={quote(query)}",verify=False).json()
        print(res_encrypted)
        encryptedRes = res_encrypted.get("encrypted_data")
        res = self.aes_decrypt(encryptedRes)
        print(res)
        return res
    
    def register_license(self, user_id, product_name, machine_code):
        """Register a license"""
        data = {
            "user_id": user_id,
            "product_name": product_name,
            "machine_code": machine_code
        }
        response = self.send_encrypted_post_request('licenses/automate', data)
        print(response)
        return response


# Usage example
if __name__ == "__main__":
    server_url = input("Enter server URL (e.g., http://localhost:5000): ").strip()
    client = SecureLicenseClient(server_url)
    
    if client.initialize_session() and client.perform_key_exchange():
        print("Client initialized and key exchange successful")
        
        # Example: Login
        username = input("Enter username: ").strip()
        password = getpass("Enter password: ").strip()
        
        if client.login_user(username, password):
            print("Login successful")
        else:
            print("Login failed")
        
    else:
        print("Failed to initialize client")

    if(client.get_all_licenses()):
        print("Fetched all licenses successfully")

    test_data=[{"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # This is valid data
               {"user_id": "<script>alert(1)</script>", "product_name": "ProductA", "machine_code": "MACHINE123"}, # XSS => this data includes XSS
               {"user_id": "user2", "product_name": "NonExistentProduct", "machine_code": "MACHINE456"}, # Non-existent product
               {"user_id": "user1", "product_name": "ProductA", "machine_code": "MACHINE123"}, # Duplicate active license, this includes same values with first data so => fails
               {"user_id": "user3", "product_name": "ProductA", "machine_code": "<img src=x onerror=alert(1)>"},
               {"user_id":"user4", "product_name":"ProductA","machine_code":"MACHINE1234"}] # XSS => this also includes XSS

    for td in test_data:
        print(f"\nTesting with user_id: {td['user_id']}, product_name: {td['product_name']}, machine_code: {td['machine_code']}")
        client.register_license(td['user_id'], td['product_name'], td['machine_code'])