from .factory import buid_engine
from apps.validator.models import PresencaRecord


def try_checkin(results_pack: dict):
    engine = buid_engine()
    veredict, results, final_score, reason = engine.calculate(results_pack)

    PresencaRecord.objects.create(
        score_facial=next(result.score for result in results if result.name == "facial"),
        score_vida=next(result.score for result in results if result.name == "liveness"),
        geo_valida=results_pack.get("geo_valida", False),
        score_final=final_score,
        aprovado=(veredict.value == "APPROVED"),
        status=veredict.value,
        origem="qr",
        motivo=reason,
    )

    return veredict