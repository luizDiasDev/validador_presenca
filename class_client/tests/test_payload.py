import json

import numpy as np
import pytest

from biometrics.capture import CaptureResult
from biometrics.models import LIVENESS_STATUS_OK
from biometrics.payload import build_checkin_payload, build_enrollment_payload

EMBEDDING_SIZE = 512


def unit_vector(seed):
    vector = np.random.default_rng(seed).normal(size=EMBEDDING_SIZE)
    return (vector / np.linalg.norm(vector)).astype(np.float32)


def successful_capture(samples_count=5):
    samples = tuple(unit_vector(seed) for seed in range(samples_count))
    mean = np.mean(samples, axis=0)
    return CaptureResult(
        success=True,
        sample_embeddings=samples,
        mean_embedding=(mean / np.linalg.norm(mean)).astype(np.float32),
        live_score=np.float32(0.95),
        live_status=LIVENESS_STATUS_OK,
        frames_read=7,
    )


def test_checkin_payload_has_the_face_and_the_liveness_fields():
    payload = build_checkin_payload(successful_capture(), challenge_passed=True)

    assert set(payload) == {"embedding", "liveness_score", "liveness_status", "challenge_passed"}
    assert len(payload["embedding"]) == EMBEDDING_SIZE
    assert payload["liveness_score"] == pytest.approx(0.95)
    assert payload["liveness_status"] == "ok"
    assert payload["challenge_passed"] is True


def test_enrollment_payload_sends_every_sample_and_the_liveness_fields():
    payload = build_enrollment_payload(successful_capture(samples_count=5), challenge_passed=True)

    assert set(payload) == {"samples", "liveness_score", "liveness_status", "challenge_passed"}
    assert len(payload["samples"]) == 5
    assert all(len(sample) == EMBEDDING_SIZE for sample in payload["samples"])


@pytest.mark.parametrize("build_payload", [build_checkin_payload, build_enrollment_payload])
def test_payloads_can_be_written_as_json(build_payload):
    payload = build_payload(successful_capture(), challenge_passed=None)

    json.dumps(payload)


@pytest.mark.parametrize("build_payload", [build_checkin_payload, build_enrollment_payload])
def test_payloads_never_say_who_the_student_is(build_payload):
    payload = build_payload(successful_capture(), challenge_passed=True)

    text = json.dumps(payload).lower()
    assert "aluno" not in text and "student" not in text and "user" not in text


def test_challenge_not_done_is_sent_as_none():
    payload = build_checkin_payload(successful_capture(), challenge_passed=None)

    assert payload["challenge_passed"] is None


def test_missing_live_score_is_sent_as_none():
    capture = CaptureResult(success=True, sample_embeddings=(unit_vector(1),),
                            mean_embedding=unit_vector(1), live_score=None, live_status="input_rejected")

    payload = build_checkin_payload(capture, challenge_passed=True)

    assert payload["liveness_score"] is None
    assert payload["liveness_status"] == "input_rejected"


@pytest.mark.parametrize("build_payload", [build_checkin_payload, build_enrollment_payload])
def test_failed_capture_cannot_become_a_payload(build_payload):
    failed = CaptureResult(success=False, reason="Aproxime-se da câmera.")

    with pytest.raises(ValueError):
        build_payload(failed, challenge_passed=True)