import pytest
from django.urls import reverse

from apps.accounts.models import Administrador, Professor, Usuario
from apps.institution.models import Institution
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401


@pytest.fixture
def platform_admin(db):
    institution = Institution.objects.create(nome="Plataforma ADSUM", cnpj="11222333000181")
    user = Usuario.objects.create_user(email="admin@umc.br", password="senha-forte-123", instituicao=institution)
    Administrador.objects.create(usuario=user, cargo="Secretaria")
    return user


@pytest.fixture
def admin_client(client, platform_admin):
    client.force_login(platform_admin)
    return client


def new_teacher_data(**changes):
    data = {
        "nome": "Maria Souza",
        "email": "maria.souza@umc.br",
        "area_atuacao": "Engenharia de Software",
        "senha": "senha-forte-123",
    }
    data.update(changes)
    return data


def test_admin_sees_the_teachers_page(admin_client):
    response = admin_client.get(reverse("teacher_panel:professores"))

    assert response.status_code == 200


def test_admin_creates_a_teacher_who_can_log_in(admin_client, platform_admin):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())

    teacher = Professor.objects.select_related("usuario").get(usuario__email="maria.souza@umc.br")
    assert teacher.area_atuacao == "Engenharia de Software"
    assert teacher.usuario.first_name == "Maria"
    assert teacher.usuario.last_name == "Souza"
    assert teacher.usuario.check_password("senha-forte-123")
    assert teacher.usuario.instituicao == platform_admin.instituicao


def test_email_already_in_use_is_rejected(admin_client):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())

    response = admin_client.post(reverse("teacher_panel:criar_professor"),
                                 new_teacher_data(nome="Outra Pessoa"), follow=True)

    assert Professor.objects.count() == 1
    assert "Já existe um usuário cadastrado com este e-mail." in response.content.decode()


def test_password_is_required_to_create(admin_client):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data(senha=""))

    assert not Professor.objects.exists()


def test_editing_without_password_keeps_the_old_one(admin_client):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())
    teacher = Professor.objects.get()

    admin_client.post(reverse("teacher_panel:editar_professor", args=[teacher.id]),
                      new_teacher_data(area_atuacao="Banco de Dados", senha=""))

    teacher.refresh_from_db()
    teacher.usuario.refresh_from_db()
    assert teacher.area_atuacao == "Banco de Dados"
    assert teacher.usuario.check_password("senha-forte-123")


def test_admin_deletes_a_teacher_without_classes(admin_client):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())
    teacher = Professor.objects.get()

    admin_client.post(reverse("teacher_panel:excluir_professor", args=[teacher.id]))

    assert not Professor.objects.exists()
    assert not Usuario.objects.filter(email="maria.souza@umc.br").exists()


def test_teacher_with_subjects_cannot_be_deleted(admin_client, cenario_professor):
    teacher = cenario_professor["professor"]

    response = admin_client.post(reverse("teacher_panel:excluir_professor", args=[teacher.id]), follow=True)

    assert Professor.objects.filter(pk=teacher.pk).exists()
    assert "disciplinas ou chamadas vinculadas" in response.content.decode()


def test_teacher_cannot_manage_other_teachers(client, cenario_professor):
    client.force_login(cenario_professor["user"])

    page = client.get(reverse("teacher_panel:professores"))
    client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())

    assert page.status_code == 302
    assert not Professor.objects.filter(usuario__email="maria.souza@umc.br").exists()