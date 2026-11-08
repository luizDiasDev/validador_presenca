import secrets
import string
from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import LogRegister
from apps.institution.models import Machine, Room


class CodigoPareamentoInvalidoError(Exception):
    pass


class MachinePairingService:

    def __init__(self, log_register=None, clock=timezone.now):
        self.log_register = log_register or LogRegister()
        self.clock = clock

    def gerar_codigo_unico(self) -> str:
        # Gera codigo de 4 digitos numericos que ainda nao esteja em uso
        alfabeto = string.digits
        for _ in range(50):
            codigo = "".join(secrets.choice(alfabeto) for _ in range(4))
            if not Machine.objects.filter(codigo_pareamento=codigo).exists():
                return codigo
        raise RuntimeError("Nao foi possivel gerar um codigo de pareamento livre")

    @transaction.atomic
    def criar_maquina(self, sala: Room, apelido: str, autor_id: int) -> Machine:
        codigo = self.gerar_codigo_unico()
        maquina = Machine.objects.create(
            sala=sala,
            apelido=apelido.strip(),
            codigo_pareamento=codigo,
        )

        self.log_register.register(
            {
                "autor_id": autor_id,
                "origem": "institution",
                "acao": "MAQUINA_CRIADA",
                "tabela": "maquina",
                "linha_tabela_id": maquina.id,
                "payload": {
                    "sala_id": sala.id,
                    "apelido": maquina.apelido,
                    "codigo_pareamento": maquina.codigo_pareamento,
                },
            }
        )
        return maquina

    @transaction.atomic
    def regenerar_codigo(self, maquina_id: int, autor_id: int) -> Machine:
        maquina = Machine.objects.select_for_update().get(pk=maquina_id)
        novo_codigo = self.gerar_codigo_unico()
        maquina.codigo_pareamento = novo_codigo
        maquina.save(update_fields=["codigo_pareamento", "data_atualizacao"])

        self.log_register.register(
            {
                "autor_id": autor_id,
                "origem": "institution",
                "acao": "CODIGO_PAREAMENTO_REGENERADO",
                "tabela": "maquina",
                "linha_tabela_id": maquina.id,
                "payload": {
                    "sala_id": maquina.sala_id,
                    "apelido": maquina.apelido,
                    "novo_codigo": novo_codigo,
                },
            }
        )
        return maquina

    @transaction.atomic
    def parear_cliente(self, codigo_pareamento: str, ip: str | None = None) -> Machine:
        codigo = (codigo_pareamento or "").strip()
        maquina = (
            Machine.objects.select_for_update()
            .select_related("sala__campus")
            .filter(codigo_pareamento=codigo)
            .first()
        )
        if not maquina:
            raise CodigoPareamentoInvalidoError("Codigo de pareamento nao encontrado")

        maquina.visto_em = self.clock()
        if ip:
            maquina.ip = ip
        maquina.save(update_fields=["ip", "visto_em", "data_atualizacao"])

        self.log_register.register(
            {
                "autor_id": 0,
                "origem": "institution",
                "acao": "MAQUINA_PAREADA",
                "tabela": "maquina",
                "linha_tabela_id": maquina.id,
                "payload": {
                    "sala_id": maquina.sala_id,
                    "apelido": maquina.apelido,
                    "ip": maquina.ip,
                    "visto_em": maquina.visto_em.isoformat(),
                },
            }
        )
        return maquina
