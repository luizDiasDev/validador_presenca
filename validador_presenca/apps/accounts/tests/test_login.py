import pyotp
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.accounts.domain.cipher import Cipher
from apps.accounts.domain.totp_auth import TotpAuth
from apps.audit.models import AuditLog


@pytest.fixture
def usuario_sem_totp(db):
    return Usuario.objects.create_user(email="aluno.teste@umc.br", password="SenhaForte123")


@pytest.fixture
def usuario_com_totp(db):
    usuario = Usuario.objects.create_user(email="professor.teste@umc.br", password="SenhaForte123")

    segredo = TotpAuth(cipher=Cipher()).create_secret(usuario)
    usuario.totp_ativo = True
    usuario.save(update_fields=["totp_cifrado", "totp_ativo"])

    # guardo o segredo em texto puro só pra gerar códigos válidos no teste
    usuario.segredo_em_texto_puro = segredo
    return usuario


def test_wrong_password_does_not_login_and_logs_LOGIN_FALHA(db, usuario_sem_totp):
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "aluno.teste@umc.br",
        "password": "senha-errada",
        "aceite_termos": "on",
    })

    assert response.status_code == 200  # form_invalid renderiza a mesma página
    log = AuditLog.objects.first()
    assert log.acao == "LOGIN_FALHA"
    assert log.payload["email_tentado"] == "aluno.teste@umc.br"


def test_first_login_without_totp_redirects_to_config(usuario_sem_totp):
    client = Client()

    response = client.post(reverse("accounts:login"), {
        "username": "aluno.teste@umc.br",
        "password": "SenhaForte123",
        "aceite_termos": "on",
    })

    assert response.status_code == 302
    assert response.url == reverse("accounts:config_totp")


def test_configuring_totp_with_correct_code_activates_user_and_logs_in(usuario_sem_totp):
    client = Client()
    client.post(reverse("accounts:login"), {
        "username": "aluno.teste@umc.br",
        "password": "SenhaForte123",
        "aceite_termos": "on",
    })

    client.get(reverse("accounts:config_totp"))

    usuario_sem_totp.refresh_from_db()
    segredo = Cipher().decrypt(bytes(usuario_sem_totp.totp_cifrado))
    codigo = pyotp.TOTP(segredo).now()

    response = client.post(reverse("accounts:config_totp"), {"code": codigo})

    usuario_sem_totp.refresh_from_db()
    assert usuario_sem_totp.totp_ativo is True
    assert response.status_code == 302
    assert response.url == reverse("validator:painel")

    log = AuditLog.objects.filter(acao="TOTP_CONFIGURADO").first()
    assert log is not None
    assert log.autor_id == usuario_sem_totp.id


def test_login_with_totp_already_active_asks_for_read_code(usuario_com_totp):
    client = Client()
    response = client.post(reverse("accounts:login"), {
        "username": "professor.teste@umc.br",
        "password": "SenhaForte123",
        "aceite_termos": "on",
    })

    assert response.status_code == 302
    assert response.url == reverse("accounts:read_totp")


def test_read_totp_wrong_code_logs_TOTP_FALHA(usuario_com_totp):
    client = Client()
    client.post(reverse("accounts:login"), {
        "username": "professor.teste@umc.br",
        "password": "SenhaForte123",
        "aceite_termos": "on",
    })

    client.post(reverse("accounts:read_totp"), {"code": "000000"})

    log = AuditLog.objects.filter(acao="TOTP_FALHA").first()
    assert log is not None
    assert log.autor_id == usuario_com_totp.id


def test_logout_logs_and_ends_session(usuario_com_totp):
    client = Client()
    client.post(reverse("accounts:login"), {
        "username": "professor.teste@umc.br",
        "password": "SenhaForte123",
        "aceite_termos": "on",
    })
    codigo = pyotp.TOTP(usuario_com_totp.segredo_em_texto_puro).now()
    client.post(reverse("accounts:read_totp"), {"code": codigo})

    client.post(reverse("accounts:logout"))

    log = AuditLog.objects.filter(acao="LOGOUT").first()
    assert log is not None
    assert log.autor_id == usuario_com_totp.id