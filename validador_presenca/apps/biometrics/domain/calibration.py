import math
from dataclasses import dataclass

LIVENESS_STATUS_OK = "ok"


def _clamp_to_range(value: float, lower_limit: float = 0.0, upper_limit: float = 1.0) -> float:
    
    return max(lower_limit, min(upper_limit, value))


def cosine_to_score(cosine: float, min_cosine: float, max_cosine: float) -> float:
    
    if max_cosine <= min_cosine:
        raise ValueError("max_cosine deve ser maior que min_cosine")
    position_in_range = (cosine - min_cosine) / (max_cosine - min_cosine)
    return _clamp_to_range(position_in_range)


@dataclass(frozen=True)
class LivenessReading:
    
    score: float
    approved: bool
    reason: str = ""


def liveness_to_score(
    live_score,
    status: str = LIVENESS_STATUS_OK,
    challenge_passed=None,
    approval_threshold: float = 0.80,
) -> LivenessReading:

    if challenge_passed is False:
        return LivenessReading(0.0, False, "Desafio de prova de vida não cumprido")

    if status != LIVENESS_STATUS_OK or live_score is None:
        return LivenessReading(0.0, False, "Prova de vida não pôde ser avaliada")

    try:
        raw_score = float(live_score)
    except (TypeError, ValueError):
        return LivenessReading(0.0, False, "Prova de vida inválida")

    if not math.isfinite(raw_score):
        return LivenessReading(0.0, False, "Prova de vida inválida")

    score = _clamp_to_range(raw_score)
    if score < approval_threshold:
        
        return LivenessReading(score, False, "Prova de vida abaixo do esperado")

    return LivenessReading(score, True, "")