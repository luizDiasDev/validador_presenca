from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.validator.management.commands.medir_checkin import medir_tempos
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db


def finished_check_in(seconds, origem="qr+facial"):
    record = PresencaRecord.objects.create(
        qr_token_hash="hash", score_facial=Decimal("0.9"), score_vida=Decimal("0.9"), geo_valida=True,
        score_final=Decimal("0.9"), aprovado=True, status="APPROVED", origem=origem,
    )
    record.data_decisao = record.data_criacao + timedelta(seconds=seconds)
    record.save(update_fields=["data_decisao"])
    return record


def test_times_go_from_the_phone_check_in_to_the_face_verdict():
    for seconds in (10, 20, 30, 40, 100):
        finished_check_in(seconds)
    finished_check_in(500, origem="qr")

    times = medir_tempos()

    assert times["amostras"] == 5
    assert times["media"] == pytest.approx(40.0, abs=0.1)
    assert times["mediana"] == pytest.approx(30.0, abs=0.1)
    assert times["p95"] == pytest.approx(100.0, abs=0.1)
    assert times["maximo"] == pytest.approx(100.0, abs=0.1)


def test_days_filter_ignores_old_check_ins():
    old = finished_check_in(60)
    PresencaRecord.objects.filter(pk=old.pk).update(data_criacao=timezone.now() - timedelta(days=30))
    finished_check_in(15)

    assert medir_tempos(dias=7)["amostras"] == 1


def test_command_says_when_there_is_nothing_to_measure(capsys):
    call_command("medir_checkin")

    assert "Nenhum check-in" in capsys.readouterr().out
