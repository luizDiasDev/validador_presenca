import hashlib
import json
import pytest

from io import StringIO

from django.core.management import CommandError, call_command

from apps.audit.domain.log_register import CURRENT_HASH_VERSION, LogRegister, verify_chain
from apps.audit.models import AuditLog


@pytest.mark.django_db
def test_first_log():
    LogRegister().register({
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
    LogRegister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "CRIADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "APPROVED"},
    })
    primeiro_log = AuditLog.objects.first()

    LogRegister().register({
        "autor_id": 1,
        "origem": "teste",
        "acao": "REVISADO",
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": {"status": "REJECTED"},
    })
    segundo_log = AuditLog.objects.order_by("-id").first()

    assert segundo_log.hash_anterior == primeiro_log.hash_atual

def register(acao="CRIADO", payload=None, autor_id=1):
    return LogRegister().register({
        "autor_id": autor_id,
        "origem": "teste",
        "acao": acao,
        "tabela": "registro_presenca",
        "linha_tabela_id": 10,
        "payload": payload if payload is not None else {"status": "APPROVED"},
    })


@pytest.mark.django_db
def test_hash_covers_every_field_of_the_event():
    log = register()
    log.refresh_from_db()

    content = json.dumps(
        {
            "hash_anterior": log.hash_anterior,
            "autor_id": log.autor_id,
            "ocorrido_em": log.ocorrido_em.isoformat(),
            "origem": log.origem,
            "acao": log.acao,
            "tabela": log.tabela,
            "linha_tabela_id": log.linha_tabela_id,
            "payload": log.payload,
        },
        sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    )

    assert log.hash_atual == hashlib.sha256(content.encode()).hexdigest()
    assert log.hash_version == CURRENT_HASH_VERSION


@pytest.mark.django_db
def test_an_untouched_chain_is_intact():
    register(payload={"b": 2, "a": 1, "texto": "presença"})
    register(acao="ALTERADO")
    register(acao="EXCLUIDO", payload={})

    result = verify_chain()

    assert result.intact
    assert result.checked == 3


@pytest.mark.django_db
@pytest.mark.parametrize("field, value", [
    ("acao", "OUTRA_ACAO"),
    ("autor_id", 99),
    ("tabela", "outra_tabela"),
    ("linha_tabela_id", 11),
    ("payload", {"status": "REJECTED"}),
])
def test_changing_any_field_breaks_the_chain_at_that_record(field, value):
    register()
    tampered = register(acao="ALTERADO")
    register(acao="EXCLUIDO")
    AuditLog.objects.filter(pk=tampered.pk).update(**{field: value})

    result = verify_chain()

    assert result.broken_id == tampered.pk
    assert "alterado" in result.reason


@pytest.mark.django_db
def test_deleting_a_record_breaks_the_chain_at_the_next_one():
    register()
    removed = register(acao="ALTERADO")
    following = register(acao="EXCLUIDO")
    AuditLog.objects.filter(pk=removed.pk).delete()

    result = verify_chain()

    assert result.broken_id == following.pk


@pytest.mark.django_db
def test_legacy_records_are_skipped_and_the_chain_continues_from_them():
    legacy = register()
    AuditLog.objects.filter(pk=legacy.pk).update(hash_version=1, payload={"reordered": True})
    register(acao="ALTERADO")

    result = verify_chain()

    assert result.intact
    assert result.legacy == 1
    assert result.checked == 1


@pytest.mark.django_db
def test_verify_command_reports_success_and_failure():
    register()
    tampered = register(acao="ALTERADO")
    out = StringIO()

    call_command("verify_audit_chain", stdout=out)
    assert "Cadeia íntegra: 2" in out.getvalue()

    AuditLog.objects.filter(pk=tampered.pk).update(acao="APAGADO")
    with pytest.raises(CommandError, match=f"#{tampered.pk}"):
        call_command("verify_audit_chain", stdout=StringIO())
