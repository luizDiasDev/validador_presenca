from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import LogRegister
from apps.checkin.models import AgendamentoChamada, ChamadaSession
from apps.institution.models import Room

# Duração padrão que o popup do QR Code fica aberto na tela (5 minutos)
DURACAO_PADRAO_MIN = 5


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
        return (
            ChamadaSession.objects.select_related(
                "aula__disciplina", "professor__usuario"
            )
            .filter(
                sala_id=sala_id,
                abre_em__lte=agora,
                fecha_em__gt=agora,
            )
            .first()
        )

    @transaction.atomic
    def abrir_agendada(self, sala_id: int) -> ChamadaSession | None:
        agora = timezone.localtime(self.clock())
        agendamentos = AgendamentoChamada.objects.select_related("aula__disciplina__professor").filter(
            aula__disciplina__turma__sala_id=sala_id,
            aula__dia_semana=agora.weekday(),
            horario__lte=agora.time(),
        )
        for agendamento in agendamentos:
            abre_em = timezone.make_aware(datetime.combine(agora.date(), agendamento.horario))
            fecha_em = abre_em + timedelta(minutes=agendamento.duracao_min)
            if agora >= fecha_em:
                continue

            Room.objects.select_for_update().get(pk=sala_id)
            if ChamadaSession.objects.filter(agendamento=agendamento, abre_em=abre_em).exists():
                continue
            if self.sessao_aberta_da_sala(sala_id):
                return None

            professor = agendamento.aula.disciplina.professor
            sessao = ChamadaSession.objects.create(
                sala_id=sala_id,
                professor=professor,
                aula=agendamento.aula,
                agendamento=agendamento,
                sequencia=ChamadaSession.objects.filter(sala_id=sala_id).count() + 1,
                tempos_cobertos=agendamento.tempos_cobertos,
                limite_por_maquina=agendamento.limite_por_maquina,
                abre_em=abre_em,
                fecha_em=fecha_em,
            )
            self._auditar("SESSAO_ABERTA", sessao, professor)
            return sessao
        return None

    def abrir_agendadas_do_professor(self, professor) -> list[ChamadaSession]:
        salas = (
            AgendamentoChamada.objects.filter(aula__disciplina__professor=professor)
            .values_list("aula__disciplina__turma__sala_id", flat=True)
            .distinct()
        )
        abertas = [self.abrir_agendada(sala_id) for sala_id in salas]
        return [sessao for sessao in abertas if sessao]

    # Garante que se o log ou o banco falharem, desfaz tudo (rollback).
    @transaction.atomic
    def abrir(
        self,
        sala_id: int,
        professor,
        aula=None,
        duracao_min: int = DURACAO_PADRAO_MIN,
        duracao_qr_s: int = 5,
        tempos_cobertos: int = 1,
        limite_por_maquina: int = 1,
    ) -> ChamadaSession:
        if duracao_min <= 0:
            raise ValueError("A duração da chamada deve ser maior que zero")
        if limite_por_maquina <= 0:
            raise ValueError("O limite de alunos por computador deve ser maior que zero")

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
            aula=aula,
            sequencia=sequencia,
            tempos_cobertos=tempos_cobertos,
            limite_por_maquina=limite_por_maquina,
            duracao_qr_s=duracao_qr_s,
            abre_em=agora,
            fecha_em=agora + timedelta(minutes=duracao_min),
        )

        self._auditar("SESSAO_ABERTA", sessao, professor)
        return sessao

    @transaction.atomic
    def encerrar(self, sessao_id: int, professor) -> ChamadaSession:
        sessao = ChamadaSession.objects.select_for_update().get(pk=sessao_id)

        if sessao.professor_id != professor.id:
            raise ChamadaSemPermissaoError(
                "Só o professor que abriu a chamada pode encerrá-la"
            )

        if not self.esta_aberta(sessao):
            raise ChamadaJaEncerradaError(f"A chamada #{sessao.pk} já está encerrada")

        sessao.fecha_em = self.clock()
        sessao.save(update_fields=["fecha_em", "data_atualizacao"])

        self._auditar("SESSAO_ENCERRADA", sessao, professor)
        return sessao

    def _auditar(self, acao: str, sessao: ChamadaSession, professor):
        self.log_register.register(
            {
                "autor_id": professor.usuario_id,
                "origem": "checkin",
                "acao": acao,
                "tabela": "sessao_chamada",
                "linha_tabela_id": sessao.id,
                "payload": {
                    "sala_id": sessao.sala_id,
                    "aula_id": sessao.aula_id,
                    "sequencia": sessao.sequencia,
                    "tempos_cobertos": sessao.tempos_cobertos,
                    "limite_por_maquina": sessao.limite_por_maquina,
                    "agendamento_id": sessao.agendamento_id,
                    "abre_em": sessao.abre_em.isoformat(),
                    "fecha_em": sessao.fecha_em.isoformat(),
                },
            }
        )


def maquina_lotada(sessao: ChamadaSession, maquina_id: int, exceto_usuario_id: int | None = None) -> bool:
    from apps.validator.models import PresencaRecord

    alunos = PresencaRecord.objects.filter(sessao=sessao, maquina_id=maquina_id).exclude(status="REJECTED")
    if exceto_usuario_id:
        alunos = alunos.exclude(usuario_id=exceto_usuario_id)
    return alunos.values("usuario_id").distinct().count() >= sessao.limite_por_maquina
