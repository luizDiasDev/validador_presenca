from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.institution.models import Machine
from apps.institution.tests.test_institution_pairing import cenario_instituicao  # noqa: F401


@pytest.fixture
def machine(cenario_instituicao):
    return MachinePairingService().criar_maquina(
        sala=cenario_instituicao["sala"], apelido="PC-01", autor_id=cenario_instituicao["user"].id
    )


@pytest.fixture
def admin_client(client, cenario_instituicao):
    client.force_login(cenario_instituicao["user"])
    return client


def machines_page(admin_client):
    return admin_client.get(reverse("institution:infraestrutura") + "?aba=maquinas").content.decode()


@override_settings(EXECUTAVEL_DOWNLOAD_URL="https://exemplo.test/ADSUM-Sala.zip")
def test_admin_sees_where_to_download_the_room_executable(admin_client, machine):
    html = machines_page(admin_client)

    assert "https://exemplo.test/ADSUM-Sala.zip" in html
    assert "Baixar executável" in html
    assert 'id="endereco-servidor">http://testserver<' in html


def test_new_machine_waits_for_pairing(admin_client, machine):
    assert "Aguardando pareamento" in machines_page(admin_client)


def test_machine_that_talked_to_the_server_recently_is_online(admin_client, machine):
    token = MachinePairingService().emitir_token(machine)
    MachinePairingService().autenticar(token)

    html = machines_page(admin_client)

    assert "Online" in html
    assert "Desconectar" in html


def test_paired_machine_that_went_quiet_is_shown_as_paired(admin_client, machine):
    MachinePairingService().emitir_token(machine)
    Machine.objects.filter(pk=machine.pk).update(visto_em=timezone.now() - timedelta(minutes=10))

    assert "Pareada" in machines_page(admin_client)


def test_admin_disconnects_the_executable(admin_client, machine, cenario_instituicao):
    token = MachinePairingService().emitir_token(machine)

    admin_client.post(reverse("institution:desparear_maquina", args=[machine.id]))

    assert MachinePairingService().autenticar(token) is None
    assert AuditLog.objects.filter(acao="MAQUINA_DESPAREADA", linha_tabela_id=machine.id).exists()


def test_new_pairing_code_disconnects_the_old_executable(machine, cenario_instituicao):
    service = MachinePairingService()
    token = service.emitir_token(machine)

    service.regenerar_codigo(maquina_id=machine.id, autor_id=cenario_instituicao["user"].id)

    assert service.autenticar(token) is None


def test_last_seen_is_not_written_on_every_request(machine):
    service = MachinePairingService()
    token = service.emitir_token(machine)
    service.autenticar(token)
    first_seen = Machine.objects.get(pk=machine.pk).visto_em

    service.autenticar(token)

    assert Machine.objects.get(pk=machine.pk).visto_em == first_seen
