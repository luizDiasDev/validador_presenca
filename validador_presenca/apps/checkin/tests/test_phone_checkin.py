from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

CAMPUS_CENTER = {"lat": "-23.5169621", "lon": "-46.1826845"}
FAR_AWAY = {"lat": "-23.5505", "lon": "-46.6333"}


@pytest.fixture
def open_session(cenario_professor):
    now = timezone.now()
    return ChamadaSession.objects.create(
        sala=cenario_professor["sala"], professor=cenario_professor["professor"], aula=cenario_professor["aula"],
        sequencia=1, abre_em=now - timedelta(minutes=5), fecha_em=now + timedelta(minutes=10),
    )


@pytest.fixture
def student_phone(client, cenario_professor):
    student = Usuario.objects.create_user(email="aluno.celular@alunos.umc.br", password="senha-forte-123")
    Aluno.objects.create(usuario=student, turma=cenario_professor["turma"], matricula="445566")
    client.force_login(student)
    return client


def room_token(session):
    return QrTokenService(cache=cache).gerar(sessao_id=session.id, maquina_id=0, ttl_s=30).token


def test_phone_without_a_token_offers_the_qr_reader(student_phone):
    html = student_phone.get(reverse("checkin:qr_demo")).content.decode()

    assert 'id="botao-ler-qr"' in html
    assert "html5-qrcode" in html
    assert "getCurrentPosition" not in html


def test_phone_opening_the_link_gets_the_location_form(student_phone):
    html = student_phone.get(reverse("checkin:qr_demo") + "?t=abc123").content.decode()

    assert 'name="token" value="abc123"' in html
    assert "getCurrentPosition" in html
    assert 'id="botao-ler-qr"' not in html


def test_phone_scan_inside_campus_registers_a_pending_presence(student_phone, open_session):
    html = student_phone.post(reverse("checkin:qr_demo"), {"token": room_token(open_session), **CAMPUS_CENTER}).content.decode()

    record = PresencaRecord.objects.get()
    assert record.status == "PENDING"
    assert record.sessao == open_session
    assert "Presença registrada" in html


def test_same_qr_read_twice_is_refused(student_phone, open_session):
    token = room_token(open_session)
    student_phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER})

    html = student_phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER}).content.decode()

    assert "já foi usado" in html
    assert PresencaRecord.objects.filter(status="REJECTED").count() == 1


def test_phone_far_from_campus_is_refused(student_phone, open_session):
    html = student_phone.post(reverse("checkin:qr_demo"), {"token": room_token(open_session), **FAR_AWAY}).content.decode()

    assert PresencaRecord.objects.get().status == "REJECTED"
    assert "acima do raio" in html


def test_teacher_cannot_check_in_through_the_phone_page(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    response = client.get(reverse("checkin:qr_demo") + "?t=abc")

    assert response.status_code == 302


def test_room_qr_screen_no_longer_exists_for_the_teacher(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    html = client.get(reverse("teacher_panel:chamadas")).content.decode()

    assert client.get("/checkin/sala/").status_code == 404
    assert "QR da Sala" not in html
