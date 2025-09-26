import base64
import secrets
import time
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.session_timeout = 3600  # 1 hour
        
    def create_session(self, client_id: str) -> str:
        """Create new session with client"""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'client_id': client_id,
            'created_at': time.time(),
            'aes_key': None,
            'server_private_key': rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            ),
            'client_public_key': None
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session and validate timeout"""
        session = self.sessions.get(session_id)
        if not session:
            return None
            
        if time.time() - session['created_at'] > self.session_timeout:
            del self.sessions[session_id]
            return None
            
        return session

class CryptoManager:
    @staticmethod
    def generate_rsa_keypair() -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate RSA 2048 keypair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    @staticmethod
    def rsa_encrypt(public_key: rsa.RSAPublicKey, data: bytes) -> bytes:
        """Encrypt data with RSA public key"""
        return public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def rsa_decrypt(private_key: rsa.RSAPrivateKey, encrypted_data: bytes) -> bytes:
        """Decrypt data with RSA private key"""
        return private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def generate_aes_key() -> bytes:
        """Generate 256-bit AES key"""
        return secrets.token_bytes(32)
    
    @staticmethod
    def aes_encrypt(key: bytes, data: str) -> dict:
        """Encrypt data with AES-256-CBC"""
        iv = secrets.token_bytes(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data to 16-byte boundary
        data_bytes = data.encode('utf-8')
        pad_length = 16 - (len(data_bytes) % 16)
        data_bytes += bytes([pad_length] * pad_length)
        
        encrypted = encryptor.update(data_bytes) + encryptor.finalize()
        
        return {
            'iv': base64.b64encode(iv).decode('utf-8'),
            'data': base64.b64encode(encrypted).decode('utf-8')
        }
    
    @staticmethod
    def aes_decrypt(key: bytes, encrypted_data: dict) -> str:
        """Decrypt AES-256-CBC encrypted data"""
        iv = base64.b64decode(encrypted_data['iv'])
        data = base64.b64decode(encrypted_data['data'])
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted = decryptor.update(data) + decryptor.finalize()
        
        # Remove padding
        pad_length = decrypted[-1]
        decrypted = decrypted[:-pad_length]
        
        return decrypted.decode('utf-8')
    

# Global instances
session_manager = SessionManager()
crypto_manager = CryptoManager()