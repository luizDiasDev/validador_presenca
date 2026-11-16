from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Professor, Usuario
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.domain.services.dashboard_service import DashboardService
from apps.teacher_panel.models import Aluno, Aula, Disciplina
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def student(cenario, email, matricula):
    user = Usuario.objects.create_user(email=email, password="senha-forte-123")
    Aluno.objects.create(usuario=user, turma=cenario["turma"], matricula=matricula)
    return user


def session(aula, professor, tempos, closed=True):
    now = timezone.now()
    return ChamadaSession.objects.create(
        aula=aula, sala=aula.disciplina.turma.sala, professor=professor, tempos_cobertos=tempos,
        abre_em=now - timedelta(minutes=30), fecha_em=now - timedelta(minutes=1) if closed else now + timedelta(minutes=10),
    )


def record(sessao, usuario, status):
    return PresencaRecord.objects.create(
        sessao=sessao, usuario=usuario, qr_token_hash="hash", geo_valida=True,
        score_facial=Decimal("0.8"), score_vida=Decimal("0.8"),
        score_final=Decimal("0.8"), aprovado=status == "APPROVED", status=status, origem="qr+facial",
    )


@pytest.fixture
def attendance(cenario_professor):
    professor = cenario_professor["professor"]
    aula = cenario_professor["aula"]
    present = student(cenario_professor, "presente@alunos.umc.br", "1001")
    missing = student(cenario_professor, "faltante@alunos.umc.br", "1002")

    first_call = session(aula, professor, tempos=2)
    second_call = session(aula, professor, tempos=2)
    open_call = session(aula, professor, tempos=4, closed=False)

    record(first_call, present, "REJECTED")
    record(first_call, present, "APPROVED")
    record(second_call, present, "APPROVED")
    record(first_call, missing, "PENDING")
    record(open_call, missing, "APPROVED")
    return cenario_professor


def test_frequency_is_weighted_by_the_periods_of_each_closed_call(attendance):
    data = DashboardService().gerar_dados(professor=attendance["professor"])

    assert data["total_chamadas"] == 2
    assert data["presencas_esperadas"] == 4
    assert (data["aprovados"], data["pendentes"], data["faltas"]) == (2, 1, 1)
    assert data["frequencia_media"] == 50.0


def test_a_retry_after_a_rejection_counts_as_present_and_no_check_in_counts_as_absence(attendance):
    students = {row["matricula"]: row for row in DashboardService().gerar_dados(professor=attendance["professor"])["resumo_alunos"]}

    assert students["1001"]["tempos"] == {"presente": 4, "pendente": 0, "falta": 0}
    assert students["1001"]["frequencia"] == 100.0
    assert students["1002"]["tempos"] == {"presente": 0, "pendente": 2, "falta": 2}
    assert students["1002"]["frequencia"] == 0.0


def test_subject_summary_uses_the_same_periods(attendance):
    (subject,) = DashboardService().gerar_dados(professor=attendance["professor"])["resumo_disciplinas"]

    assert subject["chamadas"] == 2
    assert subject["tempos"] == {"presente": 4, "pendente": 2, "falta": 2}
    assert subject["frequencia"] == 50.0


def test_teacher_does_not_see_calls_of_another_teacher_but_the_admin_sees_all(attendance):
    other_user = Usuario.objects.create_user(email="outro@umc.br", password="senha-forte-123")
    other = Professor.objects.create(usuario=other_user, area_atuacao="Direito")
    other_subject = Disciplina.objects.create(professor=other, turma=attendance["turma"], nome="Ética")
    other_class = Aula.objects.create(
        disciplina=other_subject, dia_semana=0, hora_inicio=time(19), hora_fim=time(22), tempos_aula=2,
    )
    session(other_class, other, tempos=2)

    assert DashboardService().gerar_dados(professor=attendance["professor"])["total_chamadas"] == 2
    assert DashboardService().gerar_dados(professor=None)["total_chamadas"] == 3


def test_dashboard_page_shows_the_absences(client, attendance):
    client.force_login(attendance["user"])

    html = client.get(reverse("teacher_panel:dashboard")).content.decode()

    assert "Faltas" in html
    assert "50,0%" in html


def test_date_filter_keeps_only_the_calls_inside_the_period(attendance):
    older = ChamadaSession.objects.order_by("id").first()
    ChamadaSession.objects.filter(pk=older.pk).update(
        abre_em=older.abre_em - timedelta(days=30), fecha_em=older.fecha_em - timedelta(days=30)
    )
    today = timezone.localdate()

    recent = DashboardService().gerar_dados(professor=attendance["professor"], data_inicio=today - timedelta(days=7))
    old = DashboardService().gerar_dados(professor=attendance["professor"], data_fim=today - timedelta(days=7))

    assert recent["total_chamadas"] == 1
    assert old["total_chamadas"] == 1


def test_dashboard_page_reads_the_period_and_keeps_it_in_the_class_filter(client, attendance):
    client.force_login(attendance["user"])
    today = timezone.localdate().isoformat()

    html = client.get(reverse("teacher_panel:dashboard"), {"de": today, "ate": today}).content.decode()

    assert f'value="{today}"' in html
    assert f"turma={attendance['turma'].id}" in html and f"de={today}" in html
    assert client.get(reverse("teacher_panel:dashboard"), {"de": "ontem"}).status_code == 200
