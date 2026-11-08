import pytest
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.teacher_panel.tests.test_teacher_management import admin_client, platform_admin  # noqa: F401
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401


@pytest.fixture
def student_client(client, db):
    student = Usuario.objects.create_user(email="aluno@alunos.umc.br", password="senha-forte-123")
    client.force_login(student)
    return client


def test_teacher_opens_the_attendance_history(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    response = client.get(reverse("validator:painel"))

    assert response.status_code == 200


def test_admin_cannot_open_the_attendance_history(admin_client):
    response = admin_client.get(reverse("validator:painel"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:login")


def test_student_cannot_open_the_attendance_history(student_client):
    response = student_client.get(reverse("validator:painel"))

    assert response.status_code == 302


def test_student_sent_to_the_dashboard_lands_on_the_live_checkin(student_client):
    response = student_client.get(reverse("teacher_panel:dashboard"))

    assert response.status_code == 302
    assert response.url == reverse("checkin:qr_demo")


def test_student_menu_hides_the_attendance_history(student_client):
    html = student_client.get(reverse("privacy:central")).content.decode()

    assert "Histórico de Presença" not in html