from types import SimpleNamespace

import pytest

from apps.biometrics.domain.services.biometric_service import (
    COMPARISON_DONE,
    COMPARISON_INVALID_CAPTURE,
    COMPARISON_NOT_ENROLLED,
    COMPARISON_UNREADABLE_TEMPLATE,
    ComparisonResult,
)
from apps.validator.domain.validation_engines.facial_validator import FacialValidator

ANY_EMBEDDING = [0.0] * 512


def validator_with_comparison(comparison: ComparisonResult) -> FacialValidator:
    fake_service = SimpleNamespace(compare=lambda student_id, embedding: comparison)
    return FacialValidator(service=fake_service)


def checkin_pack(**extra_fields):
    return {"aluno_id": 7, "embedding": ANY_EMBEDDING, **extra_fields}


def test_matching_face_passes_with_its_score():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 0.92, cosine=0.62))

    result = validator.validate(checkin_pack())

    assert result.passed and not result.needs_review
    assert result.score == pytest.approx(0.92)
    assert result.weight == pytest.approx(0.70)


def test_different_face_blocks():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 0.0, cosine=0.06))

    result = validator.validate(checkin_pack())

    assert not result.passed and result.block and not result.needs_review
    assert result.reason == "Rosto não confere com o cadastro"


def test_score_exactly_at_the_safeguard_passes():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 0.40, cosine=0.41))

    assert validator.validate(checkin_pack()).passed


@pytest.mark.parametrize("status, reason", [
    (COMPARISON_NOT_ENROLLED, "Biometria não cadastrada"),
    (COMPARISON_UNREADABLE_TEMPLATE, "Template biométrico ilegível; é preciso cadastrar o rosto de novo"),
    (COMPARISON_INVALID_CAPTURE, "Captura inválida: ..."),
])
def test_when_comparison_is_impossible_it_asks_for_review(status, reason):
    validator = validator_with_comparison(ComparisonResult(status, 0.0, reason=reason))

    result = validator.validate(checkin_pack())

    assert result.needs_review
    assert result.reason == reason


def test_missing_face_capture_asks_for_review():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 1.0))

    result = validator.validate({"aluno_id": 7})

    assert result.needs_review
    assert "Rosto não capturado" in result.reason


def test_missing_student_rejects():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 1.0))

    result = validator.validate({"embedding": ANY_EMBEDDING})

    assert not result.passed and not result.needs_review
    assert result.reason == "Aluno não identificado"


def test_checkin_of_the_enrollment_day_asks_for_review_even_with_a_perfect_match():
    validator = validator_with_comparison(ComparisonResult(COMPARISON_DONE, 1.0, cosine=0.99))

    result = validator.validate(checkin_pack(biometric_enrolled_in_this_checkin=True))

    assert result.needs_review
    assert result.score == 1.0
    assert "Primeiro check-in após o cadastro facial" in result.reason