import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import Usuario
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.domain.services.dashboard_service import DashboardService
from apps.teacher_panel.models import Turma
from apps.teacher_panel.tests.test_teacher_panel import cenario_professor  # noqa: F401
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def seed(cenario, **options):
    call_command("seed_demo", professor=cenario["user"].email, alunos=12, semanas=6, **options)


def test_seed_fills_the_teacher_dashboard_with_past_calls(cenario_professor):
    seed(cenario_professor)

    turma = Turma.objects.get(codigo="DEMO-01")
    data = DashboardService().gerar_dados(professor=cenario_professor["professor"], turma_id=turma.id)

    assert data["total_chamadas"] == 6
    assert data["presencas_esperadas"] == 72
    assert 0 < data["frequencia_media"] < 100
    assert data["faltas"] > 0
    assert PresencaRecord.objects.filter(revisado_por=cenario_professor["user"].id).exists()


def test_seed_refuses_to_run_twice_and_cleans_everything(cenario_professor):
    seed(cenario_professor)
    with pytest.raises(CommandError, match="--limpar"):
        seed(cenario_professor)

    call_command("seed_demo", limpar=True)

    assert not Turma.objects.filter(codigo="DEMO-01").exists()
    assert not Usuario.objects.filter(email__endswith="@demo.adsum").exists()
    assert not ChamadaSession.objects.filter(aula__disciplina__turma__codigo="DEMO-01").exists()
    assert Turma.objects.filter(pk=cenario_professor["turma"].pk).exists()


def test_seed_needs_an_existing_teacher(cenario_professor):
    with pytest.raises(CommandError, match="--professor"):
        call_command("seed_demo", professor="ninguem@umc.br")
