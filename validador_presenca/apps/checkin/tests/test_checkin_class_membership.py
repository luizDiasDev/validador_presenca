from datetime import date, timedelta

import pytest

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.institution.domain.services.pairing_service import MachinePairingService

from apps.checkin.tests.test_phone_checkin import (  # noqa: F401
    CAMPUS_CENTER,
    cenario_professor,
    open_session,
    room_token,
    student_phone,
)
from apps.teacher_panel.models import Aluno, Turma
from apps.validator.models import PresencaRecord


def test_student_from_another_class_is_refused(student_phone, open_session, cenario_professor):
    other_class = Turma.objects.create(
        sala=cenario_professor["sala"], codigo="9999", nome="Outra turma",
        curso="Direito", semestre_inicio=date(2026, 8, 1),
    )
    Aluno.objects.filter(matricula="445566").update(turma=other_class)

    html = student_phone.post(
        reverse("checkin:qr_demo"), {"token": room_token(open_session), **CAMPUS_CENTER}
    ).content.decode()

    record = PresencaRecord.objects.get()
    assert record.status == "REJECTED"
    assert record.motivo == "Você não está matriculado na turma desta chamada"
    assert "Você não está matriculado na turma desta chamada" in html


def test_qr_of_a_closed_call_is_refused_with_its_reason(student_phone, open_session):
    open_session.fecha_em = timezone.now() - timedelta(minutes=1)
    open_session.save()

    html = student_phone.post(
        reverse("checkin:qr_demo"), {"token": room_token(open_session), **CAMPUS_CENTER}
    ).content.decode()

    record = PresencaRecord.objects.get()
    assert record.status == "REJECTED"
    assert record.motivo == "A chamada deste QR Code não está aberta"
    assert "A chamada deste QR Code não está aberta" in html


def machine_token(session, machine):
    return QrTokenService(cache=cache).gerar(sessao_id=session.id, maquina_id=machine.id, ttl_s=30).token


def classmate_already_checked_in(session, machine, cenario):
    classmate = Usuario.objects.create_user(email="colega@alunos.umc.br", password="senha-forte-123")
    Aluno.objects.create(usuario=classmate, turma=cenario["turma"], matricula="778899")
    PresencaRecord.objects.create(
        sessao=session, maquina=machine, usuario=classmate, qr_token_hash="colega",
        geo_valida=True, score_facial=0, score_vida=0, score_final=0, aprovado=False, status="PENDING", origem="qr",
    )


@pytest.fixture
def room_machine(cenario_professor):
    return MachinePairingService().criar_maquina(
        sala=cenario_professor["sala"], apelido="PC-01", autor_id=cenario_professor["user"].id
    )


def test_machine_that_reached_the_teacher_limit_refuses_another_student(
    student_phone, open_session, room_machine, cenario_professor
):
    classmate_already_checked_in(open_session, room_machine, cenario_professor)

    html = student_phone.post(
        reverse("checkin:qr_demo"), {"token": machine_token(open_session, room_machine), **CAMPUS_CENTER}
    ).content.decode()

    record = PresencaRecord.objects.exclude(qr_token_hash="colega").get()
    assert record.status == "REJECTED"
    assert record.motivo == "Este computador já atingiu o limite de 1 aluno(s) nesta chamada"
    assert "limite de 1 aluno(s)" in html


def test_machine_below_the_teacher_limit_accepts_another_student(
    student_phone, open_session, room_machine, cenario_professor
):
    open_session.limite_por_maquina = 2
    open_session.save()
    classmate_already_checked_in(open_session, room_machine, cenario_professor)

    student_phone.post(
        reverse("checkin:qr_demo"), {"token": machine_token(open_session, room_machine), **CAMPUS_CENTER}
    )

    assert PresencaRecord.objects.exclude(qr_token_hash="colega").get().status == "PENDING"
