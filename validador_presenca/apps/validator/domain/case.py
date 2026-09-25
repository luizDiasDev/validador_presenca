from .factory import buid_engine
from apps.validator.models import PresencaRecord
from apps.audit.domain.log_register import LogResister


def try_checkin(results_pack: dict):
    engine = buid_engine()
    veredict, results, final_score, reason = engine.calculate(results_pack)

    new_register = PresencaRecord.objects.create(
        score_facial=next(result.score for result in results if result.name == "facial"),
        score_vida=next(result.score for result in results if result.name == "liveness"),
        geo_valida=results_pack.get("geo_valida", False),
        score_final=final_score,
        aprovado=(veredict.value == "APPROVED"),
        status=veredict.value,
        origem="qr",
        motivo=reason,
    )

    LogResister().register({
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

    return veredict