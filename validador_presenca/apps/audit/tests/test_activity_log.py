from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Administrador, Professor, Usuario
from apps.audit.domain.log_register import registrar_acao
from apps.audit.models import AuditLog
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def user(email):
    return Usuario.objects.create_user(email=email, password="senha-forte-123")


@pytest.fixture
def world(cenario_professor):
    student = user("aluno@alunos.umc.br")
    Aluno.objects.create(usuario=student, turma=cenario_professor["turma"], matricula="1001")
    classmate = user("colega@alunos.umc.br")
    Aluno.objects.create(usuario=classmate, turma=cenario_professor["turma"], matricula="1002")
    other_teacher_user = user("outro.prof@umc.br")
    Professor.objects.create(usuario=other_teacher_user, area_atuacao="Direito")
    admin = user("admin@umc.br")
    Administrador.objects.create(usuario=admin, cargo="TI")

    now = timezone.now()
    session = ChamadaSession.objects.create(
        aula=cenario_professor["aula"], sala=cenario_professor["sala"], professor=cenario_professor["professor"],
        abre_em=now - timedelta(minutes=10), fecha_em=now,
    )
    record = PresencaRecord.objects.create(
        sessao=session, usuario=student, qr_token_hash="hash", score_facial=Decimal("0.6"), score_vida=Decimal("0.9"),
        geo_valida=True, score_final=Decimal("0.69"), aprovado=False, status="PENDING", origem="qr+facial",
    )

    registrar_acao(student, "accounts", "LOGIN_SUCESSO", "usuario", student.id)
    registrar_acao(classmate, "accounts", "LOGIN_SUCESSO", "usuario", classmate.id)
    registrar_acao(student, "checkin", "PENDING", "registro_presenca", record.id, {"status": "PENDING"})
    registrar_acao(cenario_professor["user"], "checkin", "SESSAO_ABERTA", "sessao_chamada", session.id)
    registrar_acao(cenario_professor["user"], "teacher_panel", "REVISAO_MANUAL_PRESENCA", "registro_presenca", record.id)
    registrar_acao(other_teacher_user, "checkin", "SESSAO_ABERTA", "sessao_chamada", 999)
    registrar_acao(admin, "institution", "SALA_CRIADA", "sala", 1)
    return {"student": student, "classmate": classmate, "teacher": cenario_professor["user"],
            "other_teacher": other_teacher_user, "admin": admin}


def events_seen_by(client, person, **params):
    client.force_login(person)
    response = client.get(reverse("audit:registro"), params)
    return [(event.acao, event.autor_id) for event in response.context["eventos"]]


def test_student_sees_own_actions_and_what_happened_to_own_presence(client, world):
    seen = events_seen_by(client, world["student"])

    assert ("LOGIN_SUCESSO", world["student"].id) in seen
    assert ("PENDING", world["student"].id) in seen
    assert ("REVISAO_MANUAL_PRESENCA", world["teacher"].id) in seen
    assert ("LOGIN_SUCESSO", world["classmate"].id) not in seen
    assert ("SESSAO_ABERTA", world["teacher"].id) not in seen


def test_teacher_sees_the_calls_and_presences_of_own_classes_only(client, world):
    seen = events_seen_by(client, world["teacher"])

    assert ("SESSAO_ABERTA", world["teacher"].id) in seen
    assert ("PENDING", world["student"].id) in seen
    assert ("SESSAO_ABERTA", world["other_teacher"].id) not in seen
    assert ("LOGIN_SUCESSO", world["student"].id) not in seen
    assert ("SALA_CRIADA", world["admin"].id) not in seen


def test_admin_sees_everything(client, world):
    assert len(events_seen_by(client, world["admin"])) == AuditLog.objects.count()


def test_filter_by_event_keeps_the_scope(client, world):
    seen = events_seen_by(client, world["student"], acao="LOGIN_SUCESSO")

    assert seen == [("LOGIN_SUCESSO", world["student"].id)]


def test_page_shows_readable_labels_and_authors(client, world):
    client.force_login(world["student"])

    html = client.get(reverse("audit:registro")).content.decode()

    assert "Presença revisada pelo professor" in html
    assert "prof.teste@umc.br" in html


def test_admin_crud_is_now_audited(client, world, cenario_professor):
    client.force_login(world["admin"])

    client.post(reverse("teacher_panel:criar_turma"), {
        "codigo": "7777", "nome": "Nova", "curso": "ES", "sala": cenario_professor["sala"].id,
        "semestre_inicio": "2027-02-01",
    })

    assert AuditLog.objects.filter(acao="TURMA_CRIADA", autor_id=world["admin"].id).exists()


def test_student_request_is_audited_and_visible_to_the_student(client, world):
    client.force_login(world["student"])

    client.post(reverse("privacy:solicitar_direito"), {
        "tipo": "exportar_dados", "justificativa": "", "confirmo_impacto": "on",
    })

    assert ("SOLICITACAO_LGPD_CRIADA", world["student"].id) in events_seen_by(client, world["student"])
