import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.institution.models import Machine
from apps.institution.tests.test_institution_pairing import cenario_instituicao  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def machine(cenario_instituicao):
    return MachinePairingService().criar_maquina(
        sala=cenario_instituicao["sala"], apelido="PC-01", autor_id=cenario_instituicao["user"].id
    )


def pair(client, code, ip="200.1.1.1"):
    return client.post(
        reverse("institution:parear_maquina_api"),
        data=json.dumps({"codigo_pareamento": code}),
        content_type="application/json",
        HTTP_X_FORWARDED_FOR=ip,
    )


def wrong_code(machine):
    return "0000" if machine.codigo_pareamento != "0000" else "1111"


def test_a_paired_machine_cannot_be_paired_again_with_the_same_code(client, machine):
    assert pair(client, machine.codigo_pareamento).status_code == 200
    machine.refresh_from_db()
    original_token = machine.token_hash

    response = pair(client, machine.codigo_pareamento, ip="200.9.9.9")

    machine.refresh_from_db()
    assert response.status_code == 409
    assert "já está pareado" in response.json()["erro"]
    assert machine.token_hash == original_token


def test_after_the_admin_disconnects_the_machine_it_can_be_paired_again(client, machine, cenario_instituicao):
    pair(client, machine.codigo_pareamento)
    MachinePairingService().desparear(maquina_id=machine.id, autor_id=cenario_instituicao["user"].id)

    assert pair(client, machine.codigo_pareamento).status_code == 200


def test_too_many_wrong_codes_block_the_address_even_with_the_right_code(client, machine):
    for _ in range(10):
        assert pair(client, wrong_code(machine)).status_code == 404

    blocked = pair(client, machine.codigo_pareamento)

    assert blocked.status_code == 429
    assert "Muitas tentativas" in blocked.json()["erro"]
    assert not Machine.objects.get(pk=machine.pk).esta_pareada


def test_the_block_is_per_address(client, machine):
    for _ in range(10):
        pair(client, wrong_code(machine), ip="200.1.1.1")

    assert pair(client, machine.codigo_pareamento, ip="200.2.2.2").status_code == 200


def test_the_address_is_the_last_hop_added_by_the_proxy(client, machine):
    for attempt in range(10):
        pair(client, wrong_code(machine), ip=f"10.0.0.{attempt}, 200.1.1.1")

    assert pair(client, machine.codigo_pareamento, ip="10.9.9.9, 200.1.1.1").status_code == 429
