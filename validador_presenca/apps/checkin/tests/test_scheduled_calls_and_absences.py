from datetime import time, timedelta

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Usuario
from apps.audit.models import AuditLog
from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.domain.services.faltas_service import MOTIVO_FALTA, registrar_faltas_pendentes
from apps.checkin.domain.services.qr_service import QrTokenService
from apps.checkin.models import AgendamentoChamada, ChamadaSession
from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.teacher_panel.models import Aluno, Aula
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db
CAMPUS_CENTER = {"lat": "-23.5169621", "lon": "-46.1826845"}


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()


@pytest.fixture
def all_day_class(cenario_professor):
    return Aula.objects.create(
        disciplina=cenario_professor["disciplina"], dia_semana=timezone.localdate().weekday(),
        hora_inicio=time(0, 0), hora_fim=time(23, 59), tempos_aula=4,
    )


@pytest.fixture
def machine(cenario_professor):
    service = MachinePairingService()
    created = service.criar_maquina(sala=cenario_professor["sala"], apelido="PC-01", autor_id=0)
    return created, Client(HTTP_AUTHORIZATION=f"Bearer {service.emitir_token(created)}")


def student(cenario, email, matricula):
    user = Usuario.objects.create_user(email=email, password="senha-forte-123")
    Aluno.objects.create(usuario=user, turma=cenario["turma"], matricula=matricula)
    return user


def schedule(aula, minutes_ago=2, duration=10, limit=1):
    opens = (timezone.localtime() - timedelta(minutes=minutes_ago)).time().replace(second=0, microsecond=0)
    return AgendamentoChamada.objects.create(
        aula=aula, horario=opens, duracao_min=duration, tempos_cobertos=2, limite_por_maquina=limit,
    )


def test_teacher_schedules_a_call_inside_the_class_time(client, cenario_professor):
    client.force_login(cenario_professor["user"])
    data = {"aula": cenario_professor["aula"].id, "duracao_min": 10, "tempos_cobertos": 2, "limite_por_maquina": 1}

    client.post(reverse("teacher_panel:agendar_chamada"), {**data, "horario": "19:15"})
    client.post(reverse("teacher_panel:agendar_chamada"), {**data, "horario": "18:00"})
    client.post(reverse("teacher_panel:agendar_chamada"), {**data, "horario": "19:20"})
    client.post(reverse("teacher_panel:agendar_chamada"), {**data, "horario": "21:30"})

    times = sorted(f"{ag.horario:%H:%M}" for ag in AgendamentoChamada.objects.all())
    assert times == ["19:15", "21:30"]
    assert AuditLog.objects.filter(acao="CHAMADA_AGENDADA").count() == 2


def test_teacher_removes_a_schedule(client, cenario_professor):
    own = AgendamentoChamada.objects.create(aula=cenario_professor["aula"], horario=time(19, 15))
    client.force_login(cenario_professor["user"])

    client.post(reverse("teacher_panel:excluir_agendamento", kwargs={"agendamento_id": own.id}))

    assert not AgendamentoChamada.objects.exists()


def test_scheduled_call_opens_by_itself_when_the_room_computer_asks(all_day_class, machine):
    agendamento = schedule(all_day_class)

    first = machine[1].get(reverse("class_client:qr")).json()
    machine[1].get(reverse("class_client:qr"))

    session = ChamadaSession.objects.get(agendamento=agendamento)
    assert first["ativa"] is True and "link" in first
    assert session.tempos_cobertos == 2 and session.limite_por_maquina == 1
    assert session.fecha_em - session.abre_em == timedelta(minutes=10)
    assert ChamadaSession.objects.filter(agendamento=agendamento).count() == 1


def test_a_finished_schedule_does_not_open(all_day_class, machine):
    schedule(all_day_class, minutes_ago=30, duration=10)

    assert machine[1].get(reverse("class_client:qr")).json()["ativa"] is False


def test_students_without_check_in_get_an_absence_when_the_call_ends(cenario_professor):
    present = student(cenario_professor, "presente@alunos.umc.br", "1")
    absent = student(cenario_professor, "ausente@alunos.umc.br", "2")
    now = timezone.now()
    session = ChamadaSession.objects.create(
        aula=cenario_professor["aula"], sala=cenario_professor["sala"], professor=cenario_professor["professor"],
        abre_em=now - timedelta(minutes=20), fecha_em=now - timedelta(minutes=1),
    )
    PresencaRecord.objects.create(
        sessao=session, usuario=present, qr_token_hash="x", score_facial=0.9, score_vida=0.9, geo_valida=True,
        score_final=0.9, aprovado=True, status="APPROVED", origem="qr+facial",
    )

    assert registrar_faltas_pendentes() == 1
    assert registrar_faltas_pendentes() == 0

    absence = PresencaRecord.objects.get(usuario=absent)
    assert (absence.status, absence.motivo, absence.sessao) == ("REJECTED", MOTIVO_FALTA, session)
    assert PresencaRecord.objects.filter(usuario=present).count() == 1


def test_open_calls_do_not_get_absences_yet(cenario_professor):
    student(cenario_professor, "ausente@alunos.umc.br", "2")
    now = timezone.now()
    ChamadaSession.objects.create(
        aula=cenario_professor["aula"], sala=cenario_professor["sala"], professor=cenario_professor["professor"],
        abre_em=now - timedelta(minutes=2), fecha_em=now + timedelta(minutes=8),
    )

    assert registrar_faltas_pendentes() == 0


def test_student_cannot_check_in_twice_in_the_same_call(cenario_professor, machine):
    user = student(cenario_professor, "aluno@alunos.umc.br", "1")
    session = ChamadaService().abrir(
        sala_id=cenario_professor["sala"].id, professor=cenario_professor["professor"], aula=cenario_professor["aula"],
        limite_por_maquina=5,
    )
    phone = Client()
    phone.force_login(user)

    def scan():
        token = QrTokenService(cache=cache).gerar(sessao_id=session.id, maquina_id=machine[0].id, ttl_s=30).token
        return phone.post(reverse("checkin:qr_demo"), {"token": token, **CAMPUS_CENTER}).content.decode()

    scan()
    second = scan()

    assert "Você já registrou presença nesta chamada" in second
    assert PresencaRecord.objects.filter(usuario=user).exclude(status="REJECTED").count() == 1


def test_full_machine_stops_showing_the_qr(cenario_professor, machine):
    user = student(cenario_professor, "aluno@alunos.umc.br", "1")
    session = ChamadaService().abrir(
        sala_id=cenario_professor["sala"].id, professor=cenario_professor["professor"], aula=cenario_professor["aula"],
    )
    PresencaRecord.objects.create(
        sessao=session, maquina=machine[0], usuario=user, qr_token_hash="x", score_facial=0, score_vida=0,
        geo_valida=True, score_final=0, aprovado=False, status="PENDING", origem="qr",
    )

    answer = machine[1].get(reverse("class_client:qr")).json()

    assert answer["ativa"] is True and answer["lotada"] is True
    assert "link" not in answer
