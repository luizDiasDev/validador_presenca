from collections import defaultdict

from django.utils import timezone

from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno, Disciplina, Turma
from apps.validator.models import PresencaRecord

PRESENTE = "presente"
PENDENTE = "pendente"
FALTA = "falta"

SITUACAO_POR_STATUS = {"APPROVED": PRESENTE, "PENDING": PENDENTE}
PRIORIDADE_STATUS = {"APPROVED": 3, "PENDING": 2, "REJECTED": 1}


def _novo_placar():
    return {PRESENTE: 0, PENDENTE: 0, FALTA: 0}


def _frequencia(tempos: dict) -> float:
    total = sum(tempos.values())
    return round(tempos[PRESENTE] / total * 100, 1) if total else 0.0


class DashboardService:
    def __init__(self, clock=timezone.now):
        self.clock = clock

    def gerar_dados(
        self, professor=None, turma_id: int | None = None, data_inicio=None, data_fim=None
    ) -> dict:
        disciplinas = Disciplina.objects.select_related("turma").order_by("nome")
        if professor:
            disciplinas = disciplinas.filter(professor=professor)

        turmas = Turma.objects.order_by("codigo")
        if professor:
            turmas = turmas.filter(disciplinas__professor=professor).distinct()

        if turma_id:
            disciplinas = disciplinas.filter(turma_id=turma_id)

        sessoes = ChamadaSession.objects.filter(
            aula__disciplina__in=disciplinas,
            fecha_em__lte=self.clock(),
        ).select_related("aula__disciplina")
        if data_inicio:
            sessoes = sessoes.filter(abre_em__date__gte=data_inicio)
        if data_fim:
            sessoes = sessoes.filter(abre_em__date__lte=data_fim)
        sessoes = list(sessoes)

        alunos = list(
            Aluno.objects.filter(turma__disciplinas__in=disciplinas)
            .distinct()
            .select_related("usuario", "turma")
            .order_by("turma__codigo", "matricula")
        )
        alunos_por_turma = defaultdict(list)
        for aluno in alunos:
            alunos_por_turma[aluno.turma_id].append(aluno)

        melhor_status = self._melhor_status_por_aluno(sessoes)

        chamadas = _novo_placar()
        tempos_geral = _novo_placar()
        tempos_por_aluno = defaultdict(_novo_placar)
        tempos_por_disciplina = defaultdict(_novo_placar)
        chamadas_por_disciplina = defaultdict(int)

        for sessao in sessoes:
            disciplina = sessao.aula.disciplina
            chamadas_por_disciplina[disciplina.id] += 1
            for aluno in alunos_por_turma[disciplina.turma_id]:
                status = melhor_status.get((sessao.id, aluno.usuario_id))
                situacao = SITUACAO_POR_STATUS.get(status, FALTA)
                chamadas[situacao] += 1
                tempos_geral[situacao] += sessao.tempos_cobertos
                tempos_por_aluno[aluno.id][situacao] += sessao.tempos_cobertos
                tempos_por_disciplina[disciplina.id][situacao] += sessao.tempos_cobertos

        resumo_disciplinas = [
            {
                "nome": disciplina.nome,
                "turma_nome": disciplina.turma.nome,
                "chamadas": chamadas_por_disciplina[disciplina.id],
                "tempos": tempos_por_disciplina[disciplina.id],
                "frequencia": _frequencia(tempos_por_disciplina[disciplina.id]),
            }
            for disciplina in disciplinas
        ]

        resumo_alunos = [
            {
                "matricula": aluno.matricula,
                "nome": aluno.usuario.get_full_name() or aluno.usuario.email,
                "turma_nome": aluno.turma.nome,
                "tempos": tempos_por_aluno[aluno.id],
                "tempos_total": sum(tempos_por_aluno[aluno.id].values()),
                "frequencia": _frequencia(tempos_por_aluno[aluno.id]),
            }
            for aluno in alunos
        ]

        return {
            "turmas": turmas,
            "turma_selecionada": turma_id,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "total_chamadas": len(sessoes),
            "presencas_esperadas": sum(chamadas.values()),
            "aprovados": chamadas[PRESENTE],
            "pendentes": chamadas[PENDENTE],
            "faltas": chamadas[FALTA],
            "frequencia_media": _frequencia(tempos_geral),
            "resumo_disciplinas": resumo_disciplinas,
            "resumo_alunos": resumo_alunos,
        }

    def _melhor_status_por_aluno(self, sessoes) -> dict:
        melhor = {}
        registros = PresencaRecord.objects.filter(
            sessao__in=sessoes, usuario__isnull=False
        ).values_list("sessao_id", "usuario_id", "status")
        for sessao_id, usuario_id, status in registros:
            chave = (sessao_id, usuario_id)
            atual = melhor.get(chave)
            if atual is None or PRIORIDADE_STATUS[status] > PRIORIDADE_STATUS[atual]:
                melhor[chave] = status
        return melhor
