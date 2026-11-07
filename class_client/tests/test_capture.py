import numpy as np
import pytest

from biometrics.capture import CaptureConfig, collect_samples
from biometrics.models import LIVENESS_STATUS_OK, LIVENESS_STATUS_REJECTED, FaceModel

EMBEDDING_SIZE = 512
ANY_FRAME = object()


def face_embedding(seed, base=None, noise=0.0):
    
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=EMBEDDING_SIZE) if base is None else base + noise * rng.normal(size=EMBEDDING_SIZE)
    return (vector / np.linalg.norm(vector)).astype(np.float32)


def make_reading(embedding=None, detection_score=0.9, face_width=131.0, live_score=0.95,
                 live_status=LIVENESS_STATUS_OK, yaw=0.0):
    return FaceModel(
        embedding=face_embedding(1) if embedding is None else embedding,
        detection_score=detection_score,
        bounding_box=(100.0, 80.0, 100.0 + face_width, 80.0 + face_width),
        live_score=live_score,
        live_status=live_status,
        yaw=yaw,
    )


class FakeClock:
    
    def __init__(self, step=0.1):
        self.now = 0.0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


def fake_engine(*results_per_frame):
    
    remaining = list(results_per_frame)

    def analyze(frame):
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]
    return analyze


SAME_PERSON = face_embedding(7)


def same_person_reading(seed):
    return make_reading(embedding=face_embedding(seed, base=SAME_PERSON, noise=0.02))


def test_collects_the_requested_samples_and_returns_unit_mean():
    analyze = fake_engine(*[[same_person_reading(seed)] for seed in range(10, 20)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=5), clock=FakeClock())

    assert result.success
    assert len(result.sample_embeddings) == 5
    assert np.linalg.norm(result.mean_embedding) == pytest.approx(1.0, abs=1e-5)
    assert float(np.dot(result.mean_embedding, SAME_PERSON)) > 0.95


def test_skips_frames_without_face_or_with_bad_quality():
    analyze = fake_engine(
        [],                                    # nenhum rosto
        [make_reading(face_width=50.0)],       # longe demais
        [make_reading(detection_score=0.3)],   # borrado
        [same_person_reading(1)],
        [same_person_reading(2)],
        [same_person_reading(3)],
    )

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=3), clock=FakeClock())

    assert result.success
    assert result.frames_read == 6


def test_two_faces_in_the_frame_do_not_count():
    analyze = fake_engine([make_reading(), make_reading()])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(timeout_seconds=1.0), clock=FakeClock())

    assert not result.success
    assert result.reason == "Apenas uma pessoa deve aparecer na câmera."


def test_timeout_reports_the_last_problem_to_the_student():
    analyze = fake_engine([make_reading(face_width=50.0)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(timeout_seconds=1.0), clock=FakeClock())

    assert not result.success
    assert result.reason == "Aproxime-se da câmera."


def test_readings_from_different_people_are_rejected():
    first_person, second_person = face_embedding(1), face_embedding(2)
    
    analyze = fake_engine(*[[make_reading(embedding=first_person if i % 2 else second_person)] for i in range(5)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=4), clock=FakeClock())

    assert not result.success
    assert "mesma pessoa" in result.reason


def test_camera_without_image_respects_the_timeout():
    result = collect_samples(lambda: None, fake_engine([]), CaptureConfig(timeout_seconds=1.0), clock=FakeClock())

    assert not result.success
    assert result.frames_read == 0
    assert result.reason == "Tempo esgotado sem capturar o rosto."


def test_liveness_not_evaluated_is_discarded_when_required():
    analyze = fake_engine([make_reading(live_status=LIVENESS_STATUS_REJECTED, live_score=None)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(timeout_seconds=1.0), clock=FakeClock())

    assert not result.success
    assert "afaste-se" in result.reason


def test_liveness_not_evaluated_is_kept_when_not_required():
    analyze = fake_engine([make_reading(live_status=LIVENESS_STATUS_REJECTED, live_score=None)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=3),
                             require_liveness=False, clock=FakeClock())

    assert result.success
    assert result.live_status == LIVENESS_STATUS_REJECTED
    assert result.live_score is None


def test_live_score_is_the_median_so_one_odd_reading_does_not_pull_it():
    scores = [0.95, 0.96, 0.10, 0.94, 0.97]
    analyze = fake_engine(*[[make_reading(embedding=face_embedding(i, base=SAME_PERSON, noise=0.02), live_score=s)]
                            for i, s in enumerate(scores)])

    result = collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=5), clock=FakeClock())

    assert result.live_score == pytest.approx(0.95)


def test_progress_is_reported_on_every_frame():
    progress_updates = []
    analyze = fake_engine([], [same_person_reading(1)], [same_person_reading(2)])

    collect_samples(lambda: ANY_FRAME, analyze, CaptureConfig(samples_needed=2), clock=FakeClock(),
                    on_progress=lambda collected, needed, hint: progress_updates.append((collected, needed, hint)))

    assert progress_updates == [(0, 2, "Nenhum rosto detectado."), (1, 2, ""), (2, 2, "")]