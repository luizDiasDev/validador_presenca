from unittest.mock import MagicMock

import pytest

from apps.validator.domain.engine import Engine
from apps.validator.domain.values.factor_result import FactorResult
from apps.validator.domain.values.verdict import Verdict


def validator_returning(**factor_fields):
    defaults = {"name": "factor", "passed": True, "block": True, "score": 1.0, "weight": 1.0, "reason": ""}
    validator = MagicMock()
    validator.validate.return_value = FactorResult(**{**defaults, **factor_fields})
    return validator


def test_factor_asking_for_review_makes_the_checkin_pending_even_with_high_score():
    qr = validator_returning(name="qr_code", weight=0.0)
    facial = validator_returning(name="facial", passed=False, score=0.0, weight=0.7,
                                 reason="Biometria não cadastrada", needs_review=True)
    liveness = validator_returning(name="liveness", block=False, weight=0.3)

    verdict, _, _, reason = Engine([qr, facial, liveness]).calculate({})

    assert verdict == Verdict.PENDING
    assert reason == "Biometria não cadastrada"


def test_blocking_failure_wins_over_a_review_request():
    invalid_qr = validator_returning(name="qr_code", passed=False, score=0.0, weight=0.0,
                                     reason="Token inválido ou expirado")
    facial = validator_returning(name="facial", passed=False, score=0.0, weight=1.0,
                                 reason="Biometria não cadastrada", needs_review=True)

    verdict, _, final_score, reason = Engine([invalid_qr, facial]).calculate({})

    assert verdict == Verdict.REJECTED
    assert final_score == 0.0
    assert reason == "Token inválido ou expirado"


def test_review_reasons_are_joined():
    first = validator_returning(name="facial", passed=False, needs_review=True, reason="Rosto não capturado")
    second = validator_returning(name="other", passed=False, needs_review=True, reason="Outro motivo")

    _, _, _, reason = Engine([first, second]).calculate({})

    assert reason == "Rosto não capturado; Outro motivo"


def test_pending_still_reports_the_computed_score():
    facial = validator_returning(name="facial", passed=False, score=0.9, weight=0.7,
                                 needs_review=True, reason="Primeiro check-in após o cadastro facial")
    liveness = validator_returning(name="liveness", block=False, score=1.0, weight=0.3)

    _, _, final_score, _ = Engine([facial, liveness]).calculate({})

    assert final_score == pytest.approx(0.93)