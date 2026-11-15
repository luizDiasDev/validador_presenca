import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.privacy.models import AceiteTermo, Termo
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401

pytestmark = pytest.mark.django_db


def term(cenario, tipo):
    return Termo.objects.create(
        instituicao=cenario["inst"], tipo=tipo, versao="1.0", titulo=tipo,
        conteudo="Conteúdo", documento_hash="a" * 64, ativo=True,
    )


def student(cenario, matricula):
    user = Usuario.objects.create_user(email=f"{matricula}@alunos.umc.br", password="senha-forte-123")
    Aluno.objects.create(usuario=user, turma=cenario["turma"], matricula=matricula)
    return user


def badges_of(html, matricula):
    row = html.split(f">{matricula}<", 1)[1].split("</tr>", 1)[0]
    return [label for label in ("Aceitos", "Pendente", "Consentida", "Revogada", "Sem consentimento") if f">{label}<" in row]


def test_student_list_shows_terms_and_biometric_consent(client, cenario_professor):
    policy = term(cenario_professor, Termo.TIPO_POLITICA)
    terms_of_use = term(cenario_professor, Termo.TIPO_TERMO)
    biometric = term(cenario_professor, Termo.TIPO_BIOMETRICO)

    complete = student(cenario_professor, "2001")
    for accepted in (policy, terms_of_use, biometric):
        AceiteTermo.objects.create(usuario=complete, termo=accepted, concedido=True)

    revoked = student(cenario_professor, "2002")
    AceiteTermo.objects.create(usuario=revoked, termo=policy, concedido=True)
    AceiteTermo.objects.create(usuario=revoked, termo=biometric, concedido=True, data_revogada=timezone.now())

    student(cenario_professor, "2003")
    client.force_login(cenario_professor["user"])

    html = client.get(reverse("teacher_panel:alunos")).content.decode()

    assert badges_of(html, "2001") == ["Aceitos", "Consentida"]
    assert badges_of(html, "2002") == ["Pendente", "Revogada"]
    assert badges_of(html, "2003") == ["Pendente", "Sem consentimento"]
