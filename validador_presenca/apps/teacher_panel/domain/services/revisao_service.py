from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import LogRegister
from apps.validator.models import PresencaRecord


class RevisaoPresencaService:

    def __init__(self, log_register=None, clock=timezone.now):
        self.log_register = log_register or LogRegister()
        self.clock = clock

    @transaction.atomic
    def revisar(
        self,
        registro_id: int,
        autor_id: int,
        novo_status: str,
        motivo: str,
    ) -> PresencaRecord:
        if novo_status not in ("APPROVED", "REJECTED"):
            raise ValueError("Status de revisao invalido")

        motivo_limpo = (motivo or "").strip()
        if len(motivo_limpo) < 5:
            raise ValueError("A justificativa deve ter pelo menos 5 caracteres")

        # Trava a linha do registro para evitar revisao concorrente
        registro = PresencaRecord.objects.select_for_update().get(pk=registro_id)
        agora = self.clock()

        registro.status = novo_status
        registro.aprovado = novo_status == "APPROVED"
        registro.motivo = motivo_limpo
        registro.revisado_por = autor_id
        registro.data_revisao = agora
        registro.data_decisao = agora
        registro.save(
            update_fields=[
                "status",
                "aprovado",
                "motivo",
                "revisado_por",
                "data_revisao",
                "data_decisao",
                "data_atualizacao",
            ]
        )

        # Registra decisao na tabela de auditoria
        self.log_register.register(
            {
                "autor_id": autor_id,
                "origem": "teacher_panel",
                "acao": "REVISAO_MANUAL_PRESENCA",
                "tabela": "registro_presenca",
                "linha_tabela_id": registro.id,
                "payload": {
                    "novo_status": novo_status,
                    "aprovado": registro.aprovado,
                    "motivo": motivo_limpo,
                },
            }
        )

        return registro
