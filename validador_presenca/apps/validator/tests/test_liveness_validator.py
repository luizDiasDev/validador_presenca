import pytest

from apps.validator.domain.validation_engines.liveness_validator import LivenessValidator


def test_real_person_passes_with_weight_0_30_and_never_blocks():
    result = LivenessValidator().validate({"liveness_score": 0.95, "liveness_status": "ok", "challenge_passed": True})

    assert result.passed
    assert result.score == pytest.approx(0.95)
    assert result.weight == pytest.approx(0.30)
    assert result.block is False


def test_photo_on_screen_scores_zero_but_does_not_block():
    result = LivenessValidator().validate({"liveness_score": 0.0, "liveness_status": "ok"})

    assert not result.passed
    assert result.score == 0.0
    assert result.block is False


def test_failed_head_turn_challenge_scores_zero():
    result = LivenessValidator().validate({"liveness_score": 0.99, "challenge_passed": False})

    assert result.score == 0.0
    assert result.reason == "Desafio de prova de vida não cumprido"


def test_missing_liveness_data_scores_zero():
    result = LivenessValidator().validate({})

    assert result.score == 0.0
    assert not result.passed