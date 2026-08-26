import os
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

KEYS_DIR = "keys"
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "system_private.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "system_public.pem")

class CryptoService:
    def __init__(self):
        self._ensure_keys_exist()
        self.private_key = self._load_private_key()
        self.public_key_pem = self._load_public_key_pem()

    def _ensure_keys_exist(self):
        if not os.path.exists(KEYS_DIR):
            os.makedirs(KEYS_DIR)
            
        if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH):
            print("Generating new RSA key pair for the system...")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Save Private Key
            with open(PRIVATE_KEY_PATH, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
            # Save Public Key
            public_key = private_key.public_key()
            with open(PUBLIC_KEY_PATH, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def _load_private_key(self):
        with open(PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
            )
            
    def _load_public_key_pem(self) -> str:
        with open(PUBLIC_KEY_PATH, "r") as f:
            return f.read()

    def sign_data(self, data: bytes) -> str:
        """
        Signs the data using the system's private RSA key.
        Returns the signature as a base64 encoded string.
        """
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def get_public_key_pem(self) -> str:
        return self.public_key_pem
