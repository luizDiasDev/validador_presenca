from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

CAMPUS_CENTER = {"lat": "-23.5169621", "lon": "-46.1826845"}


def logged_student(client, scenario):
    student = Usuario.objects.create_user(email="aluno.sessao@alunos.umc.br", password="senha-forte-123")
    Aluno.objects.create(usuario=student, turma=scenario["turma"], matricula="998877")
    client.force_login(student)


def scan_qr_of_session(client, session_id):
    token = QrTokenService(cache=cache).gerar(sessao_id=session_id, maquina_id=0).token
    client.post("/checkin/", {"token": token, **CAMPUS_CENTER})
    return PresencaRecord.objects.get()


def test_checkin_without_any_open_session_is_rejected(client, cenario_professor):
    logged_student(client, cenario_professor)

    record = scan_qr_of_session(client, session_id=999)

    assert record.status == "REJECTED"


def test_checkin_after_the_session_closed_is_rejected(client, cenario_professor):
    now = timezone.now()
    closed = ChamadaSession.objects.create(
        sala=cenario_professor["sala"], professor=cenario_professor["professor"], aula=cenario_professor["aula"],
        sequencia=1, abre_em=now - timedelta(hours=2), fecha_em=now - timedelta(hours=1),
    )
    logged_student(client, cenario_professor)

    record = scan_qr_of_session(client, session_id=closed.id)

    assert record.status == "REJECTED"


def test_checkin_during_an_open_session_goes_to_review_without_a_face(client, cenario_professor):
    now = timezone.now()
    opened = ChamadaSession.objects.create(
        sala=cenario_professor["sala"], professor=cenario_professor["professor"], aula=cenario_professor["aula"],
        sequencia=1, abre_em=now - timedelta(minutes=5), fecha_em=now + timedelta(minutes=10),
    )
    logged_student(client, cenario_professor)

    record = scan_qr_of_session(client, session_id=opened.id)

    assert record.status == "PENDING"
    assert record.sessao.professor == cenario_professor["professor"]