import math

import pytest

from apps.biometrics.domain.calibration import cosine_to_score, liveness_to_score


# ---------- cosine_to_score ----------

@pytest.mark.parametrize("cosine, expected_score", [
    (0.25, 0.0),    # no mínimo
    (0.45, 0.5),    # no meio da faixa
    (0.65, 1.0),    # no máximo
    (0.06, 0.0),    # outra pessoa
    (0.86, 1.0),    # você de frente
])
def test_cosine_maps_linearly_and_is_clamped(cosine, expected_score):
    assert cosine_to_score(cosine, min_cosine=0.25, max_cosine=0.65) == pytest.approx(expected_score)


def test_inverted_cosine_range_is_rejected():
    with pytest.raises(ValueError):
        cosine_to_score(0.5, min_cosine=0.65, max_cosine=0.25)


# ---------- liveness_to_score ----------

def test_real_person_above_threshold_is_approved():
    reading = liveness_to_score(0.94)

    assert reading.approved
    assert reading.score == pytest.approx(0.94)


def test_weak_liveness_keeps_the_score_but_is_not_approved():
    reading = liveness_to_score(0.50)

    assert not reading.approved
    assert reading.score == pytest.approx(0.50)
    assert reading.reason == "Prova de vida abaixo do esperado"


@pytest.mark.parametrize("live_score, status", [
    (None, "ok"),
    (0.95, "input_rejected"),
    ("abc", "ok"),
    (math.nan, "ok"),
    (math.inf, "ok"),
])
def test_liveness_that_cannot_be_trusted_scores_zero(live_score, status):
    reading = liveness_to_score(live_score, status)

    assert reading.score == 0.0
    assert not reading.approved


def test_failed_head_turn_challenge_scores_zero_even_with_high_passive_score():
    reading = liveness_to_score(0.99, challenge_passed=False)

    assert reading.score == 0.0
    assert reading.reason == "Desafio de prova de vida não cumprido"


def test_passed_challenge_does_not_change_the_passive_score():
    assert liveness_to_score(0.90, challenge_passed=True).score == pytest.approx(0.90)


def test_score_above_one_is_clamped():
    assert liveness_to_score(1.3).score == 1.0