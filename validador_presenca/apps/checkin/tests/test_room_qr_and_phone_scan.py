import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
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


@pytest.fixture
def room_computer(cenario_professor):
    from django.test import Client
    computer = Client()
    computer.force_login(cenario_professor["user"])
    return computer


def token_shown_in_the_room(room_computer, monkeypatch):
    """Lê o link que vai dentro do QR: troca o gerador de imagem por um que só guarda o texto."""
    captured = {}

    class FakeImage:
        def save(self, buffer, format):
            buffer.write(b"png")

    def fake_make(text):
        captured["link"] = text
        return FakeImage()

    monkeypatch.setattr("apps.checkin.views.qrcode.make", fake_make)
    room_computer.get(reverse("checkin:sala"))
    return re.search(r"\?t=(.+)$", captured["link"]).group(1), captured["link"]


def test_room_screen_shows_the_qr_while_the_session_is_open(room_computer, open_session, monkeypatch):
    token, link = token_shown_in_the_room(room_computer, monkeypatch)

    assert token
    assert "/checkin/?t=" in link


def test_room_screen_without_open_session_says_so(room_computer):
    html = room_computer.get(reverse("checkin:sala")).content.decode()

    assert "Nenhuma chamada aberta" in html


def test_phone_without_a_token_shows_how_to_check_in(student_phone):
    html = student_phone.get(reverse("checkin:qr_demo")).content.decode()

    assert "Aponte a câmera do celular" in html
    assert "getCurrentPosition" not in html


def test_room_screen_can_name_its_machine(room_computer, open_session, cenario_professor, monkeypatch):
    from apps.institution.models import Machine
    Machine.objects.create(sala=cenario_professor["sala"], apelido="PC-01", codigo_pareamento="1111")
    second = Machine.objects.create(sala=cenario_professor["sala"], apelido="PC-02", codigo_pareamento="2222")
    monkeypatch.setattr("apps.checkin.views.qrcode.make", lambda text: type("I", (), {"save": lambda self, b, format: b.write(b"x")})())

    html = room_computer.get(reverse("checkin:sala") + f"?maquina={second.id}").content.decode()

    assert "PC-02" in html


def test_phone_opening_the_link_gets_the_location_form(student_phone):
    html = student_phone.get(reverse("checkin:qr_demo") + "?t=abc123").content.decode()

    assert 'name="token" value="abc123"' in html
    assert "getCurrentPosition" in html


def test_phone_scan_inside_campus_registers_a_pending_presence(room_computer, student_phone, open_session, monkeypatch):
    token, _ = token_shown_in_the_room(room_computer, monkeypatch)

    html = student_phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER}).content.decode()

    record = PresencaRecord.objects.get()
    assert record.status == "PENDING"
    assert record.sessao == open_session
    assert "Presença registrada" in html


def test_same_qr_read_twice_is_refused(room_computer, student_phone, open_session, monkeypatch):
    token, _ = token_shown_in_the_room(room_computer, monkeypatch)
    student_phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER})

    html = student_phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER}).content.decode()

    assert "já foi usado" in html
    assert PresencaRecord.objects.filter(status="REJECTED").count() == 1


def test_phone_far_from_campus_is_refused(room_computer, student_phone, open_session, monkeypatch):
    token, _ = token_shown_in_the_room(room_computer, monkeypatch)

    html = student_phone.post(reverse("checkin:qr_demo"), {"token": token, **FAR_AWAY}).content.decode()

    assert PresencaRecord.objects.get().status == "REJECTED"
    assert "acima do raio" in html


def test_student_cannot_open_the_room_screen(student_phone):
    response = student_phone.get(reverse("checkin:sala"))

    assert response.status_code == 302


def test_teacher_cannot_check_in_through_the_phone_page(room_computer):
    response = room_computer.get(reverse("checkin:qr_demo") + "?t=abc")

    assert response.status_code == 302