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