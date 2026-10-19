from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import LogRegister
from apps.checkin.models import ChamadaSession
from apps.institution.models import Room

DURACAO_PADRAO_MIN = 50


class ChamadaJaAbertaError(Exception):
    pass


class ChamadaJaEncerradaError(Exception):
    pass


class ChamadaSemPermissaoError(Exception):
    pass


class ChamadaService:

    def __init__(self, log_register=None, clock=timezone.now):
        self.log_register = log_register or LogRegister()
        self.clock = clock

    def esta_aberta(self, sessao: ChamadaSession) -> bool:
        agora = self.clock()
        return sessao.abre_em <= agora < sessao.fecha_em

    def sessao_aberta_da_sala(self, sala_id: int) -> ChamadaSession | None:
        agora = self.clock()
        return ChamadaSession.objects.filter(
            sala_id=sala_id,
            abre_em__lte=agora,
            fecha_em__gt=agora,
        ).first()

    # Garante que se o log ou o banco falharem, desfaz tudo (rollback).
    @transaction.atomic
    def abrir(self, sala_id: int, professor, duracao_min: int = DURACAO_PADRAO_MIN) -> ChamadaSession:
        if duracao_min <= 0:
            raise ValueError("A duração da chamada deve ser maior que zero")

        Room.objects.select_for_update().get(pk=sala_id)

        sessao_existente = self.sessao_aberta_da_sala(sala_id)
        if sessao_existente:
            raise ChamadaJaAbertaError(
                f"Já existe uma chamada aberta nesta sala (#{sessao_existente.pk})"
            )

        agora = self.clock()
        sequencia = ChamadaSession.objects.filter(sala_id=sala_id).count() + 1

        sessao = ChamadaSession.objects.create(
            sala_id=sala_id,
            professor=professor,
            sequencia=sequencia,
            abre_em=agora,
            fecha_em=agora + timedelta(minutes=duracao_min),
        )

        self._auditar("SESSAO_ABERTA", sessao, professor)
        return sessao

    @transaction.atomic
    def encerrar(self, sessao_id: int, professor) -> ChamadaSession:
        sessao = ChamadaSession.objects.select_for_update().get(pk=sessao_id)

        if sessao.professor_id != professor.id:
            raise ChamadaSemPermissaoError("Só o professor que abriu a chamada pode encerrá-la")

        if not self.esta_aberta(sessao):
            raise ChamadaJaEncerradaError(f"A chamada #{sessao.pk} já está encerrada")

        sessao.fecha_em = self.clock()
        sessao.save(update_fields=["fecha_em", "data_atualizacao"])

        self._auditar("SESSAO_ENCERRADA", sessao, professor)
        return sessao

    def _auditar(self, acao: str, sessao: ChamadaSession, professor):
        self.log_register.register({
            "autor_id": professor.usuario_id,
            "origem": "checkin",
            "acao": acao,
            "tabela": "sessao_chamada",
            "linha_tabela_id": sessao.id,
            "payload": {
                "sala_id": sessao.sala_id,
                "sequencia": sessao.sequencia,
                "abre_em": sessao.abre_em.isoformat(),
                "fecha_em": sessao.fecha_em.isoformat(),
            },
        })