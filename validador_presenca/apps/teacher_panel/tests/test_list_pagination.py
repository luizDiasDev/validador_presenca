import pytest
from django.urls import reverse

from apps.accounts.models import Professor, Usuario
from apps.biometrics.tests.test_biometric_service import enrolled_student
from apps.privacy.models import AceiteTermo, Termo
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_management import admin_client, platform_admin  # noqa: F401
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401

pytestmark = pytest.mark.django_db


def many_students(cenario, count):
    for number in range(count):
        user = Usuario.objects.create_user(email=f"aluno{number}@alunos.umc.br", password="senha-forte-123")
        Aluno.objects.create(usuario=user, turma=cenario["turma"], matricula=f"9{number:04d}")


def test_student_list_is_paged_and_keeps_the_class_filter(admin_client, cenario_professor):
    many_students(cenario_professor, 25)
    turma = cenario_professor["turma"].id

    first = admin_client.get(reverse("teacher_panel:alunos"), {"turma": turma})
    second = admin_client.get(reverse("teacher_panel:alunos"), {"turma": turma, "pagina": 2})

    assert len(first.context["alunos"]) == 20
    assert len(second.context["alunos"]) == 5
    assert f"turma={turma}&amp;pagina=2" in first.content.decode()
    assert "Todas as Turmas (25)" in first.content.decode()


def test_student_list_shows_whether_the_face_is_enrolled(admin_client, cenario_professor):
    enrolled = enrolled_student()
    Aluno.objects.create(usuario=enrolled, turma=cenario_professor["turma"], matricula="70001")
    many_students(cenario_professor, 1)

    html = admin_client.get(reverse("teacher_panel:alunos")).content.decode()

    assert html.split(">70001<", 1)[1].split("</tr>", 1)[0].count(">Cadastrado<") == 1
    assert ">Não cadastrado<" in html.split(">90000<", 1)[1].split("</tr>", 1)[0]


def test_teacher_list_shows_the_terms_status(admin_client, cenario_professor):
    policy = Termo.objects.create(
        instituicao=cenario_professor["inst"], tipo=Termo.TIPO_POLITICA, versao="1.0", titulo="Política",
        conteudo="Texto", documento_hash="a" * 64, ativo=True,
    )
    AceiteTermo.objects.create(usuario=cenario_professor["user"], termo=policy, concedido=True)
    pending_user = Usuario.objects.create_user(email="novo.prof@umc.br", password="senha-forte-123", first_name="Zeca")
    Professor.objects.create(usuario=pending_user, area_atuacao="Direito")

    html = admin_client.get(reverse("teacher_panel:professores")).content.decode()

    assert ">Aceitos<" in html.split("prof.teste@umc.br", 1)[1].split("</tr>", 1)[0]
    assert ">Pendente<" in html.split("novo.prof@umc.br", 1)[1].split("</tr>", 1)[0]


def test_an_invalid_page_falls_back_to_a_valid_one(admin_client, cenario_professor):
    many_students(cenario_professor, 3)

    response = admin_client.get(reverse("teacher_panel:alunos"), {"pagina": "abc"})

    assert response.status_code == 200
    assert len(response.context["alunos"]) == 3
