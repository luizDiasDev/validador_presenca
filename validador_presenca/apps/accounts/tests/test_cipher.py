import pytest
from django.test import override_settings

from apps.accounts.domain.cipher import Cipher


def test_encrypt_returns_bytes():
    cipher = Cipher()

    cifrado = cipher.encrypt("segredo-totp")

    assert isinstance(cifrado, bytes)
    assert cifrado != b"segredo-totp"


def test_decrypt_reverses_encrypt():
    cipher = Cipher()

    cifrado = cipher.encrypt("segredo-totp")
    decifrado = cipher.decrypt(cifrado)

    assert decifrado == "segredo-totp"


def test_cipher_recusa_chave_de_criptografia_invalida():
    with override_settings(TOTP_ENCRYPTION_KEY="chave-curta-demais"):
        with pytest.raises(ValueError, match="32 url-safe base64-encoded bytes"):
            Cipher()


def test_cipher_cifra_e_decifra_texto_vazio():
    cipher = Cipher()

    cifrado = cipher.encrypt("")

    assert cipher.decrypt(cifrado) == ""
