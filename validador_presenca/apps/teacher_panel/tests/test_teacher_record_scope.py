from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Professor, Usuario
from apps.audit.models import AuditLog
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def session_of(professor, cenario):
    now = timezone.now()
    return ChamadaSession.objects.create(
        aula=cenario["aula"], sala=cenario["sala"], professor=professor,
        abre_em=now - timedelta(minutes=5), fecha_em=now,
    )


def record_in(session, status="PENDING", motivo="Score intermediario"):
    return PresencaRecord.objects.create(
        sessao=session, qr_token_hash="hash", score_facial=Decimal("0.6"), score_vida=Decimal("0.8"),
        geo_valida=True, score_final=Decimal("0.66"), aprovado=status == "APPROVED",
        status=status, origem="qr+facial", motivo=motivo,
    )


@pytest.fixture
def other_professor():
    user = Usuario.objects.create_user(email="outro.prof@umc.br", password="testpassword123")
    return Professor.objects.create(usuario=user, area_atuacao="Direito")


def review(client, record, status="APPROVED"):
    return client.post(
        reverse("teacher_panel:revisar_pendencia", kwargs={"registro_id": record.id}),
        {"status": status, "motivo": "Aluno conferido em sala"},
    )


def test_history_shows_only_the_records_of_the_logged_teacher(client, cenario_professor, other_professor):
    mine = record_in(session_of(cenario_professor["professor"], cenario_professor), status="APPROVED")
    record_in(session_of(other_professor, cenario_professor), status="APPROVED")
    client.force_login(cenario_professor["user"])

    response = client.get(reverse("validator:painel"))

    assert list(response.context["registers"]) == [mine]
    assert response.context["total"] == 1
    assert response.context["approved"] == 1


def test_teacher_cannot_review_a_record_from_another_teacher(client, cenario_professor, other_professor):
    record = record_in(session_of(other_professor, cenario_professor))
    client.force_login(cenario_professor["user"])

    assert review(client, record).status_code == 404
    record.refresh_from_db()
    assert record.status == "PENDING"


def test_teacher_cannot_review_a_record_that_is_not_pending(client, cenario_professor):
    record = record_in(session_of(cenario_professor["professor"], cenario_professor), status="APPROVED")
    client.force_login(cenario_professor["user"])

    assert review(client, record, status="REJECTED").status_code == 404
    record.refresh_from_db()
    assert record.status == "APPROVED"


def test_review_keeps_the_engine_reason_in_the_audit(client, cenario_professor):
    record = record_in(session_of(cenario_professor["professor"], cenario_professor), motivo="Prova de vida abaixo do esperado")
    client.force_login(cenario_professor["user"])

    review(client, record)

    log = AuditLog.objects.get(acao="REVISAO_MANUAL_PRESENCA", linha_tabela_id=record.id)
    assert log.payload["motivo_anterior"] == "Prova de vida abaixo do esperado"


def test_pending_list_shows_why_the_record_is_pending(client, cenario_professor):
    record_in(session_of(cenario_professor["professor"], cenario_professor), motivo="Rosto não capturado (falha na webcam ou no executável)")
    client.force_login(cenario_professor["user"])

    html = client.get(reverse("teacher_panel:pendencias")).content.decode()

    assert "Rosto não capturado (falha na webcam ou no executável)" in html
