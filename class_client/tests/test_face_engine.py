from types import SimpleNamespace

import numpy as np
import pytest

from biometrics.face_engine import FaceEngine
from biometrics.models import LIVENESS_STATUS_OK, LIVENESS_STATUS_UNAVAILABLE


def fake_insightface_face(**overrides):
    face = {
        "normed_embedding": np.ones(512, dtype=np.float32) / np.sqrt(512),
        "embedding": np.ones(512, dtype=np.float32),
        "det_score": 0.88,
        "bbox": np.array([10.0, 20.0, 210.0, 240.0]),
        "liveness": {"status": "ok", "is_live": True, "live_score": 0.93},
        "pose": np.array([-5.0, 12.0, 1.5]),   # pitch, yaw, roll
    }
    face.update(overrides)
    return SimpleNamespace(**face)


def test_converts_every_field():
    reading = FaceEngine._to_face_model(fake_insightface_face())

    assert reading.embedding.shape == (512,)
    assert reading.detection_score == pytest.approx(0.88)
    assert reading.bounding_box == (10.0, 20.0, 210.0, 240.0)
    assert reading.live_score == pytest.approx(0.93)
    assert reading.live_status == LIVENESS_STATUS_OK
    assert (reading.pitch, reading.yaw, reading.roll) == (-5.0, 12.0, 1.5)


def test_normalizes_embedding_when_library_does_not():
    reading = FaceEngine._to_face_model(fake_insightface_face(normed_embedding=None))

    assert np.linalg.norm(reading.embedding) == pytest.approx(1.0, abs=1e-6)


def test_missing_liveness_becomes_unavailable():
    reading = FaceEngine._to_face_model(fake_insightface_face(liveness=None))

    assert reading.live_status == LIVENESS_STATUS_UNAVAILABLE
    assert reading.live_score is None


def test_unknown_liveness_status_becomes_unavailable():
    reading = FaceEngine._to_face_model(fake_insightface_face(liveness={"status": "weird"}))

    assert reading.live_status == LIVENESS_STATUS_UNAVAILABLE


def test_missing_head_pose_leaves_angles_empty():
    reading = FaceEngine._to_face_model(fake_insightface_face(pose=None))

    assert reading.yaw is None and reading.pitch is None and reading.roll is None


def test_analyze_returns_one_reading_per_detected_face():
    engine = FaceEngine()
    # injeta um "InsightFace" falso para não carregar modelo
    engine._face_analysis = SimpleNamespace(
        get=lambda frame: [fake_insightface_face(), fake_insightface_face(det_score=0.7)]
    )

    readings = engine.analyze(np.zeros((480, 640, 3), dtype=np.uint8))

    assert [round(r.detection_score, 2) for r in readings] == [0.88, 0.7]
