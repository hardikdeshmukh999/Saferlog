import os
import base64
import logging
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

logger = logging.getLogger("saferlog")

class MockKMSClient:
    """
    Simulates a Key Management Service (like AWS KMS or Azure Key Vault).
    Keys are generated securely in-memory and NEVER written to disk.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MockKMSClient, cls).__new__(cls)
            cls._instance._generate_keys()
        return cls._instance

    def _generate_keys(self):
        logger.info("MockKMSClient: Generating ephemeral in-memory RSA key pair...")
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key_pem = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def get_private_key(self):
        return self.private_key

    def get_public_key_pem(self) -> str:
        return self.public_key_pem

class CryptoService:
    def __init__(self):
        self.kms = MockKMSClient()
        self.private_key = self.kms.get_private_key()
        self.public_key_pem = self.kms.get_public_key_pem()

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
