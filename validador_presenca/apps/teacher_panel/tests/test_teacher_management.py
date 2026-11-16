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

@pytest.mark.parametrize("weak_password", ["123", "12345678", "senha"])
def test_a_weak_password_is_rejected_when_creating_a_teacher(admin_client, weak_password):
    response = admin_client.post(
        reverse("teacher_panel:criar_professor"), new_teacher_data(senha=weak_password), follow=True,
    )

    assert not Professor.objects.filter(usuario__email="maria.souza@umc.br").exists()
    assert "senha" in response.content.decode().lower()


def test_a_weak_password_is_rejected_when_editing_a_teacher(admin_client):
    admin_client.post(reverse("teacher_panel:criar_professor"), new_teacher_data())
    teacher = Professor.objects.get(usuario__email="maria.souza@umc.br")

    admin_client.post(reverse("teacher_panel:editar_professor", args=[teacher.id]), new_teacher_data(senha="123"))

    teacher.usuario.refresh_from_db()
    assert teacher.usuario.check_password("senha-forte-123")


def test_a_weak_password_is_rejected_when_creating_a_student(admin_client, platform_admin):
    from datetime import date

    from apps.institution.models import Campus, Room
    from apps.teacher_panel.models import Aluno, Turma

    campus = Campus.objects.create(
        instituicao=platform_admin.instituicao, nome="Sede", latitude="-23.5", longitude="-46.1", raio_metros=300,
    )
    turma = Turma.objects.create(
        sala=Room.objects.create(campus=campus, codigo="A-30", nome="Lab"),
        codigo="2324", nome="ES", curso="ES", semestre_inicio=date(2026, 8, 1),
    )
    data = {"turma": turma.id, "matricula": "11221100123", "nome": "Ana Lima", "email": "ana@umc.br"}

    admin_client.post(reverse("teacher_panel:criar_aluno"), {**data, "senha": "abc"})
    assert not Aluno.objects.exists()

    admin_client.post(reverse("teacher_panel:criar_aluno"), {**data, "senha": "Matricula#2026"})
    assert Aluno.objects.filter(matricula="11221100123").exists()


def test_django_admin_hashes_the_password_and_hides_internal_fields(admin_client, platform_admin):
    platform_admin.is_staff = True
    platform_admin.is_superuser = True
    platform_admin.save()

    response = admin_client.post(reverse("admin:accounts_usuario_add"), {
        "email": "novo@umc.br", "first_name": "Novo", "last_name": "Usuário",
        "instituicao": platform_admin.instituicao_id, "usable_password": "true",
        "password1": "Senha#Forte2026", "password2": "Senha#Forte2026",
    })

    created = Usuario.objects.get(email="novo@umc.br")
    assert response.status_code == 302
    assert created.password != "Senha#Forte2026"
    assert created.check_password("Senha#Forte2026")
    assert created.username == "novo@umc.br"

    change_page = admin_client.get(reverse("admin:accounts_usuario_change", args=[created.id])).content.decode()
    assert 'name="totp_cifrado"' not in change_page
    assert 'name="chave_sessao_ativa"' not in change_page
    assert 'name="password"' not in change_page
