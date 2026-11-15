import pytest
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.biometrics.domain.services.biometric_service import BiometricService
from apps.biometrics.models import Biometria
from apps.biometrics.tests.test_biometric_service import enrolled_student
from apps.privacy.models import SolicitacaoLGPD

pytestmark = pytest.mark.django_db


@pytest.fixture
def dpo_client(client):
    dpo = Usuario.objects.create_superuser(email="dpo@umc.br", password="SenhaForte123")
    client.force_login(dpo)
    return client


def revocation_request_of(student):
    return SolicitacaoLGPD.objects.create(
        usuario=student, tipo=SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA
    )


def test_attending_a_revocation_with_the_admin_action_deletes_the_biometric(dpo_client):
    student = enrolled_student()
    request = revocation_request_of(student)

    dpo_client.post(
        reverse("admin:privacy_solicitacaolgpd_changelist"),
        {"action": "marcar_como_atendida", "_selected_action": [request.id]},
    )

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert request.data_resposta is not None
    assert not Biometria.objects.filter(usuario=student).exists()
    assert BiometricService().get_active_consent(student) is None


def test_attending_a_revocation_in_the_edit_form_deletes_the_biometric(dpo_client):
    student = enrolled_student()
    request = revocation_request_of(student)

    dpo_client.post(
        reverse("admin:privacy_solicitacaolgpd_change", args=[request.id]),
        {
            "status": SolicitacaoLGPD.STATUS_ATENDIDA,
            "resposta_dpo": "",
            "data_resposta_0": "",
            "data_resposta_1": "",
        },
    )

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert not Biometria.objects.filter(usuario=student).exists()


def test_attending_another_request_type_keeps_the_biometric(dpo_client):
    student = enrolled_student()
    request = SolicitacaoLGPD.objects.create(
        usuario=student, tipo=SolicitacaoLGPD.TIPO_EXPORTAR_DADOS
    )

    dpo_client.post(
        reverse("admin:privacy_solicitacaolgpd_changelist"),
        {"action": "marcar_como_atendida", "_selected_action": [request.id]},
    )

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert Biometria.objects.filter(usuario=student).exists()
