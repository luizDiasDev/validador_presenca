import json

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.test import Client

from apps.accounts.models import Usuario
from apps.institution.models import Room

pytestmark = pytest.mark.django_db


def prepare(tmp_path, machines=3):
    output = tmp_path / "dados_carga.json"
    call_command("preparar_carga", maquinas=machines, saida=str(output))
    return json.loads(output.read_text(encoding="utf-8"))


def test_prepared_machines_see_an_open_call_and_students_are_logged_in(tmp_path):
    data = prepare(tmp_path)

    assert len(data["maquinas"]) == 3
    assert len(data["alunos"]) == 3
    machine = Client().get("/api/v1/maquinas/qr/", HTTP_AUTHORIZATION=f"Bearer {data['maquinas'][0]['token']}")
    assert machine.json()["ativa"] is True

    student = Client()
    student.cookies["sessionid"] = data["alunos"][0]["sessionid"]
    assert student.get("/checkin/").status_code == 200


def test_machines_are_split_in_rooms_of_thirty(tmp_path):
    prepare(tmp_path, machines=31)

    assert Room.objects.filter(codigo__startswith="CARGA-").count() == 2


def test_cleaning_removes_the_load_test_data(tmp_path):
    prepare(tmp_path)

    call_command("preparar_carga", limpar=True)

    assert not Usuario.objects.filter(email__endswith="@carga.adsum").exists()
    assert not Room.objects.filter(codigo__startswith="CARGA-").exists()


def test_it_refuses_a_remote_database(tmp_path, monkeypatch):
    monkeypatch.setitem(settings.DATABASES["default"], "HOST", "ep-banco.neon.tech")

    with pytest.raises(CommandError, match="banco local"):
        prepare(tmp_path)
