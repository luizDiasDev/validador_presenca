from cryptography.fernet import Fernet
from django.conf import settings

class Cipher:

    def __init__(self):
        self.fernet = Fernet(settings.TOTP_ENCRYPTION_KEY)

    def encrypt(self, text_to_encrypt: str) -> bytes:
        #fernet só aceita byte, por isso o encode no str que chega
        return self.fernet.encrypt(text_to_encrypt.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        return self.fernet.decrypt(encrypted_data).decode()