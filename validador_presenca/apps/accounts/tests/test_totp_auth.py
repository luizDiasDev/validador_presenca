import pyotp

from apps.accounts.domain.cipher import Cipher
from apps.accounts.domain.totp_auth import TotpAuth


class UsuarioFalso:

    def __init__(self):
        self.email = "professor@umc.br"
        self.totp_cifrado = None


def test_create_secret_fills_user_totp_cifrado():
    totp_auth = TotpAuth(cipher=Cipher())
    usuario = UsuarioFalso()

    totp_auth.create_secret(usuario)

    assert usuario.totp_cifrado is not None
    assert isinstance(usuario.totp_cifrado, bytes)


def test_create_uri_contains_email_and_system_name():
    totp_auth = TotpAuth(cipher=Cipher())
    usuario = UsuarioFalso()
    totp_auth.create_secret(usuario)

    uri = totp_auth.create_uri(usuario)

    assert "professor%40umc.br" in uri or "professor@umc.br" in uri
    assert "ADSUM" in uri


def test_verify_code_accepts_correct_code():
    totp_auth = TotpAuth(cipher=Cipher())
    usuario = UsuarioFalso()
    segredo = totp_auth.create_secret(usuario)

    codigo_valido = pyotp.TOTP(segredo).now()

    assert totp_auth.verify_code(usuario, codigo_valido) is True


def test_verify_code_rejects_wrong_code():
    totp_auth = TotpAuth(cipher=Cipher())
    usuario = UsuarioFalso()
    totp_auth.create_secret(usuario)

    assert totp_auth.verify_code(usuario, "000000") is False


def test_verify_code_without_totp_configured_returns_false():
    totp_auth = TotpAuth(cipher=Cipher())
    usuario = UsuarioFalso()  # totp_cifrado continua None

    assert totp_auth.verify_code(usuario, "123456") is False