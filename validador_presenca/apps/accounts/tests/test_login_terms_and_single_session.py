import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.audit.models import AuditLog
from apps.institution.models import Institution
from apps.privacy.models import AceiteTermo, Termo

pytestmark = pytest.mark.django_db

PASSWORD = "SenhaForte123"


@pytest.fixture
def institution():
    suffix = uuid.uuid4().hex[:8]
    return Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))


def publish(institution, tipo, versao="1.0"):
    Termo.objects.filter(instituicao=institution, tipo=tipo).update(ativo=False)
    return Termo.objects.create(
        instituicao=institution, tipo=tipo, versao=versao, titulo=tipo,
        conteudo="Conteúdo", documento_hash="a" * 64, ativo=True,
    )


@pytest.fixture
def login_terms(institution):
    return [publish(institution, Termo.TIPO_POLITICA), publish(institution, Termo.TIPO_TERMO)]


@pytest.fixture
def user(institution):
    return Usuario.objects.create_user(email="usuario@umc.br", password=PASSWORD, instituicao=institution)


def accept(user, terms):
    for term in terms:
        AceiteTermo.objects.create(usuario=user, termo=term, concedido=True)


def log_in(client):
    return client.post(reverse("accounts:login"), {"username": "usuario@umc.br", "password": PASSWORD})


def test_first_login_shows_the_terms_before_the_second_factor(client, user, login_terms):
    response = log_in(client)

    assert response.url == reverse("accounts:aceitar_termos")
    assert client.get(reverse("accounts:config_totp")).url == reverse("accounts:aceitar_termos")


def test_accepting_the_terms_records_them_and_continues_to_the_second_factor(client, user, login_terms):
    log_in(client)

    response = client.post(reverse("accounts:aceitar_termos"), {"aceite": "sim"})

    assert response.url == reverse("accounts:config_totp")
    assert AceiteTermo.objects.filter(usuario=user, concedido=True).count() == 2
    assert AuditLog.objects.filter(acao="TERMOS_ACEITOS", autor_id=user.id).exists()


def test_leaving_the_checkbox_unchecked_keeps_the_user_on_the_terms(client, user, login_terms):
    log_in(client)

    response = client.post(reverse("accounts:aceitar_termos"), {})

    assert response.status_code == 200
    assert not AceiteTermo.objects.filter(usuario=user).exists()


def test_user_who_accepted_the_current_version_goes_straight_to_the_second_factor(client, user, login_terms):
    accept(user, login_terms)

    assert log_in(client).url == reverse("accounts:config_totp")


def test_a_new_version_asks_only_for_the_changed_document(client, user, institution, login_terms):
    accept(user, login_terms)
    new_policy = publish(institution, Termo.TIPO_POLITICA, versao="2.0")

    log_in(client)
    response = client.get(reverse("accounts:aceitar_termos"))

    assert list(response.context["termos"]) == [new_policy]


def test_logging_in_on_another_device_ends_the_first_session(user):
    first_device, second_device = Client(), Client()
    first_device.force_login(user)
    second_device.force_login(user)

    response = first_device.get(reverse("privacy:central"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")
    assert second_device.get(reverse("privacy:central")).status_code == 200
