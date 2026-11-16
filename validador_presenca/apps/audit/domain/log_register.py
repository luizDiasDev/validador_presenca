import hashlib
import json
from dataclasses import dataclass

from django.db import connection, transaction
from django.utils import timezone

from apps.audit.models import AuditLog

GENESIS_HASH = "0" * 64
CURRENT_HASH_VERSION = 2
AUDIT_LOCK_ID = 7_421_001


def chained_hash(previous_hash: str, autor_id: int, ocorrido_em, origem: str, acao: str,
                 tabela: str, linha_tabela_id: int, payload: dict) -> str:
    content = json.dumps(
        {
            "hash_anterior": previous_hash,
            "autor_id": autor_id,
            "ocorrido_em": ocorrido_em.isoformat(),
            "origem": origem,
            "acao": acao,
            "tabela": tabela,
            "linha_tabela_id": linha_tabela_id,
            "payload": payload,
        },
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode()).hexdigest()


def _lock_chain() -> None:
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [AUDIT_LOCK_ID])


class LogRegister:

    @transaction.atomic
    def register(self, data_log: dict) -> AuditLog:
        _lock_chain()
        last_log = AuditLog.objects.order_by("-id").first()
        previous_hash = last_log.hash_atual if last_log else GENESIS_HASH

        fields = {
            "autor_id": data_log.get("autor_id", 0),
            "ocorrido_em": timezone.now(),
            "origem": data_log.get("origem", ""),
            "acao": data_log.get("acao", ""),
            "tabela": data_log.get("tabela", ""),
            "linha_tabela_id": data_log.get("linha_tabela_id", 0),
            "payload": json.loads(json.dumps(data_log.get("payload", {}))),
        }
        return AuditLog.objects.create(
            **fields,
            hash_anterior=previous_hash,
            hash_atual=chained_hash(previous_hash, **fields),
            hash_version=CURRENT_HASH_VERSION,
        )


@dataclass(frozen=True)
class ChainVerification:
    checked: int
    legacy: int
    broken_id: int | None
    reason: str

    @property
    def intact(self) -> bool:
        return self.broken_id is None


def verify_chain() -> ChainVerification:
    checked = legacy = 0
    previous = None
    for log in AuditLog.objects.order_by("id").iterator():
        if log.hash_version < CURRENT_HASH_VERSION:
            legacy += 1
            previous = log
            continue
        expected_previous = previous.hash_atual if previous else GENESIS_HASH
        if log.hash_anterior != expected_previous:
            return ChainVerification(checked, legacy, log.id, "O registro não aponta para o hash do registro anterior.")
        expected_hash = chained_hash(
            log.hash_anterior, log.autor_id, log.ocorrido_em, log.origem, log.acao,
            log.tabela, log.linha_tabela_id, log.payload,
        )
        if log.hash_atual != expected_hash:
            return ChainVerification(checked, legacy, log.id, "O conteúdo do registro foi alterado depois de gravado.")
        checked += 1
        previous = log
    return ChainVerification(checked, legacy, None, "")


def registrar_acao(autor, origem: str, acao: str, tabela: str, linha_tabela_id: int, payload: dict | None = None):
    LogRegister().register(
        {
            "autor_id": getattr(autor, "id", None) or 0,
            "origem": origem,
            "acao": acao,
            "tabela": tabela,
            "linha_tabela_id": linha_tabela_id or 0,
            "payload": payload or {},
        }
    )
