import hashlib
import json
import pytest

from apps.audit.domain.log_register import LogResister
from apps.audit.models import AuditLog


@pytest.mark.django_db
def test_first_log():
    LogResister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "CRIADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "APPROVED"},
    })

    log = AuditLog.objects.first()

    assert log.hash_anterior == "0" * 64


@pytest.mark.django_db
def test_second_hash():
    LogResister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "CRIADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "APPROVED"},
    })
    primeiro_log = AuditLog.objects.first()

    LogResister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "REVISADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "REJECTED"},
    })
    segundo_log = AuditLog.objects.order_by("-id").first()

    assert segundo_log.hash_anterior == primeiro_log.hash_atual

@pytest.mark.django_db
def test_validate_hash():
    LogResister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "CRIADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "APPROVED"},
    })
    log = AuditLog.objects.first()

    concat = log.hash_anterior + json.dumps(log.payload) + str(log.ocorrido_em)
    hash_esperado = hashlib.sha256(concat.encode()).hexdigest()

    assert log.hash_atual == hash_esperado