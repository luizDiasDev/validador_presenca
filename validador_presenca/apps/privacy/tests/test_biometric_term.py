import hashlib
import uuid

import pytest
from django.core.management import call_command
from django.test import RequestFactory

from apps.accounts.models import Usuario
from apps.institution.models import Institution
from apps.privacy.models import AceiteTermo, Termo
from apps.privacy.signals import registrar_aceite_no_login

pytestmark = pytest.mark.django_db


def create_student():
    return Usuario.objects.create_user(email=f"aluno.{uuid.uuid4().hex}@umc.br", password="SenhaForte123")


def create_active_term(institution, term_type):
    return Termo.objects.create(
        instituicao=institution, tipo=term_type, versao="1.0", titulo=term_type,
        conteudo="Conteúdo do documento", documento_hash="a" * 64, ativo=True,
    )


def test_login_accepts_policy_and_terms_of_use_but_not_the_biometric_term():
    suffix = uuid.uuid4().hex[:8]
    institution = Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))
    for term_type in (Termo.TIPO_POLITICA, Termo.TIPO_TERMO, Termo.TIPO_BIOMETRICO):
        create_active_term(institution, term_type)
    student = create_student()
    # simula o login com a checkbox de aceite marcada
    request = RequestFactory().post("/accounts/login/")
    request.session = {"aceite_termos_dado": True}

    registrar_aceite_no_login(sender=None, request=request, user=student)

    accepted_types = set(AceiteTermo.objects.filter(usuario=student).values_list("termo__tipo", flat=True))
    assert accepted_types == {Termo.TIPO_POLITICA, Termo.TIPO_TERMO}


def test_biometric_term_fixture_loads_active_with_matching_hash():
    call_command("loaddata", "initial_data", "termos_iniciais", "termo_biometrico", verbosity=0)

    term = Termo.objects.get(tipo=Termo.TIPO_BIOMETRICO)

    assert term.ativo is True
    assert term.versao == "1.0"
    # o hash guardado precisa ser o do texto, para provar qual versão o aluno aceitou
    assert term.documento_hash == hashlib.sha256(term.conteudo.encode()).hexdigest()


def test_biometric_term_has_its_own_label():
    term = Termo(tipo=Termo.TIPO_BIOMETRICO)

    assert term.get_tipo_display() == "Termo de Consentimento Biométrico"