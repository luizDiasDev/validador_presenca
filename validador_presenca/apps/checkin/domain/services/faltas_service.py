from django.db import transaction
from django.utils import timezone

from apps.audit.domain.log_register import registrar_acao
from apps.checkin.models import ChamadaSession
from apps.teacher_panel.models import Aluno
from apps.validator.models import PresencaRecord

ORIGEM_FALTA = "ausencia"
MOTIVO_FALTA = "Falta: nenhum check-in nesta chamada"


def registrar_faltas_pendentes(clock=timezone.now) -> int:
    agora = clock()
    total = 0
    sessoes = ChamadaSession.objects.filter(fecha_em__lte=agora, faltas_registradas=False).select_related(
        "aula__disciplina__professor"
    )
    for sessao in sessoes:
        total += _registrar_faltas_da_sessao(sessao.id, agora)
    return total


@transaction.atomic
def _registrar_faltas_da_sessao(sessao_id: int, agora) -> int:
    sessao = (
        ChamadaSession.objects.select_for_update(of=("self",))
        .select_related("aula__disciplina__professor__usuario")
        .get(pk=sessao_id)
    )
    if sessao.faltas_registradas:
        return 0

    faltas = []
    if sessao.aula_id:
        com_registro = PresencaRecord.objects.filter(sessao=sessao).values("usuario_id")
        ausentes = Aluno.objects.filter(turma_id=sessao.aula.disciplina.turma_id).exclude(usuario_id__in=com_registro)
        faltas = PresencaRecord.objects.bulk_create(
            PresencaRecord(
                sessao=sessao, usuario_id=aluno.usuario_id, qr_token_hash="", score_facial=0, score_vida=0,
                geo_valida=False, score_final=0, aprovado=False, status="REJECTED", origem=ORIGEM_FALTA,
                motivo=MOTIVO_FALTA, data_decisao=agora,
            )
            for aluno in ausentes
        )

    sessao.faltas_registradas = True
    sessao.save(update_fields=["faltas_registradas", "data_atualizacao"])
    if faltas:
        registrar_acao(
            None, "checkin", "FALTAS_REGISTRADAS", "sessao_chamada", sessao.id,
            {"faltas": len(faltas)},
        )
    return len(faltas)
