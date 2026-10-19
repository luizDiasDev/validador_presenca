import pytest
from django.test import override_settings

from apps.accounts.domain.cipher import Cipher
from django.conf import settings


def test_encrypt_returns_bytes():
    cipher = Cipher(settings.TOTP_ENCRYPTION_KEY)

    cifrado = cipher.encrypt_text("segredo-totp")

    assert isinstance(cifrado, bytes)
    assert cifrado != b"segredo-totp"


def test_decrypt_reverses_encrypt():
    cipher = Cipher(settings.TOTP_ENCRYPTION_KEY)

    cifrado = cipher.encrypt_text("segredo-totp")
    decifrado = cipher.decrypt_text(cifrado)

    assert decifrado == "segredo-totp"


def test_cipher_recusa_chave_de_criptografia_invalida():
    with override_settings(TOTP_ENCRYPTION_KEY="chave-curta-demais"):
        with pytest.raises(ValueError, match="32 url-safe base64-encoded bytes"):
            Cipher(settings.TOTP_ENCRYPTION_KEY)


def test_cipher_cifra_e_decifra_texto_vazio():
    cipher = Cipher(settings.TOTP_ENCRYPTION_KEY)

    cifrado = cipher.encrypt_text("")

    assert cipher.decrypt_text(cifrado) == ""

def test_cipher_cifra_e_decifra_bytes():
    cipher = Cipher(settings.TOTP_ENCRYPTION_KEY)
    cifrado = cipher.encrypt_bytes(b"\x00\x01 bytes")
    assert cipher.decrypt_bytes(cifrado) == b"\x00\x01 bytes"


def test_cipher_exige_a_chave_na_chamada():
    with pytest.raises(TypeError):
        Cipher()
