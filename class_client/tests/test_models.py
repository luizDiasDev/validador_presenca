import numpy as np

from biometrics.models import LIVENESS_STATUS_UNAVAILABLE, FaceReading


def test_face_width_is_right_minus_left_edge():
    reading = FaceReading(
        embedding=np.zeros(512, dtype=np.float32),
        detection_score=0.9,
        bounding_box=(100.0, 50.0, 260.0, 230.0),
    )

    assert reading.face_width == 160.0


def test_liveness_defaults_to_unavailable():
    reading = FaceReading(np.zeros(512, dtype=np.float32), 0.9, (0, 0, 10, 10))

    assert reading.live_status == LIVENESS_STATUS_UNAVAILABLE
    assert reading.live_score is None
