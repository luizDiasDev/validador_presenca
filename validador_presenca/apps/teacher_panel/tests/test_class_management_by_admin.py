import pytest
from django.urls import reverse

from apps.teacher_panel.models import Turma
from apps.teacher_panel.tests.test_teacher_management import admin_client, platform_admin  # noqa: F401
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401

pytestmark = pytest.mark.django_db


def class_data(cenario, **changes):
    data = {
        "codigo": "3001",
        "nome": "1 Semestre A",
        "curso": "Engenharia de Software",
        "sala": cenario["sala"].id,
        "semestre_inicio": "2027-02-01",
    }
    data.update(changes)
    return data


def test_admin_lists_the_classes_with_students_and_subjects(admin_client, cenario_professor):
    html = admin_client.get(reverse("teacher_panel:gestao_turmas")).content.decode()

    assert "GESTÃO DE TURMAS" in html
    assert cenario_professor["turma"].codigo in html
    assert reverse("teacher_panel:gestao_turmas") in admin_client.get(reverse("teacher_panel:alunos")).content.decode()


def test_admin_creates_edits_and_deletes_a_class(admin_client, cenario_professor):
    admin_client.post(reverse("teacher_panel:criar_turma"), class_data(cenario_professor))
    turma = Turma.objects.get(codigo="3001")

    admin_client.post(
        reverse("teacher_panel:editar_turma", kwargs={"turma_id": turma.id}),
        class_data(cenario_professor, nome="1 Semestre B"),
    )
    turma.refresh_from_db()
    assert turma.nome == "1 Semestre B"

    response = admin_client.post(reverse("teacher_panel:excluir_turma", kwargs={"turma_id": turma.id}))
    assert response.url == reverse("teacher_panel:gestao_turmas")
    assert not Turma.objects.filter(pk=turma.id).exists()


def test_teacher_cannot_create_or_delete_classes(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    client.post(reverse("teacher_panel:criar_turma"), class_data(cenario_professor))
    client.post(reverse("teacher_panel:excluir_turma", kwargs={"turma_id": cenario_professor["turma"].id}))

    assert not Turma.objects.filter(codigo="3001").exists()
    assert Turma.objects.filter(pk=cenario_professor["turma"].id).exists()
    assert client.get(reverse("teacher_panel:gestao_turmas")).status_code == 302


def test_teacher_page_keeps_subjects_and_lessons_but_not_the_class_crud(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    html = client.get(reverse("teacher_panel:turmas") + "?aba=disciplinas").content.decode()

    assert "Nova Disciplina" in html
    assert "Nova Turma" not in html
    assert f'<option value="{cenario_professor["turma"].id}">' in html
