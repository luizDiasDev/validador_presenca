from cryptography.fernet import Fernet
from django.conf import settings

class Cipher:

    def __init__(self, key):
        self.fernet = Fernet(key)

    def encrypt_text(self, text_to_encrypt: str) -> bytes:
        #fernet só aceita byte, por isso o encode no str que chega
        return self.fernet.encrypt(text_to_encrypt.encode())

    def decrypt_text(self, encrypted_data: bytes) -> str:
        return self.fernet.decrypt(encrypted_data).decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        return self.fernet.decrypt(bytes(encrypted_data))