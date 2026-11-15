from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

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
