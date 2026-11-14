from django.utils import timezone

from .factory import build_engine
from apps.validator.models import PresencaRecord
from apps.audit.domain.log_register import LogRegister
from apps.checkin.models import ChamadaSession
from apps.institution.models import Machine
from apps.accounts.models import Usuario


def try_checkin(results_pack: dict):
    return register_checkin(results_pack).veredict


def register_checkin(results_pack: dict) -> PresencaRecord:
    engine = build_engine()
    veredict, results, final_score, reason = engine.calculate(results_pack)

    sessao = ChamadaSession.objects.filter(pk=results_pack.get("sessao_id")).first()
    maquina = Machine.objects.filter(pk=results_pack.get("maquina_id")).first()
    usuario = Usuario.objects.filter(pk=results_pack.get("aluno_id")).first()

    new_register = PresencaRecord.objects.create(
        sessao=sessao,
        maquina=maquina,
        usuario=usuario,
        qr_token_hash=results_pack.get("qr_token_hash", ""),
        score_facial=_score_of(results, "facial"),
        score_vida=_score_of(results, "liveness"),
        geo_valida=results_pack.get("geo_valida", False),
        score_final=final_score,
        aprovado=(veredict.value == "APPROVED"),
        status=veredict.value,
        origem="qr",
        motivo=reason,
    )

    LogRegister().register({
        "autor_id": results_pack.get("aluno_id"),
        "origem": "checkin",
        "acao": veredict.value,
        "tabela": "registro_presenca",
        "linha_tabela_id": new_register.id,
        "payload": {
            "score_final": float(final_score),
            "status": veredict.value,
            "motivo": reason,
            "qr_token_hash": results_pack.get("qr_token_hash"),
        },
    })

    new_register.veredict = veredict
    return new_register


def reevaluate_checkin(record: PresencaRecord, results_pack: dict):
    engine = build_engine()
    veredict, results, final_score, reason = engine.calculate(results_pack)

    record.score_facial = _score_of(results, "facial")
    record.score_vida = _score_of(results, "liveness")
    record.score_final = final_score
    record.aprovado = veredict.value == "APPROVED"
    record.status = veredict.value
    record.motivo = reason
    record.origem = "qr+facial"
    record.data_decisao = timezone.now()
    record.save(update_fields=[
        "score_facial", "score_vida", "score_final", "aprovado",
        "status", "motivo", "origem", "data_decisao", "data_atualizacao",
    ])

    LogRegister().register({
        "autor_id": results_pack.get("aluno_id"),
        "origem": "checkin",
        "acao": f"REAVALIADO_COM_ROSTO_{veredict.value}",
        "tabela": "registro_presenca",
        "linha_tabela_id": record.id,
        "payload": {
            "score_final": float(final_score),
            "status": veredict.value,
            "motivo": reason,
            "maquina_id": results_pack.get("maquina_id"),
        },
    })
    return veredict


def _score_of(results, factor_name: str):
    return next(result.score for result in results if result.name == factor_name)
