import numpy as np
import pytest

from biometrics.models import LIVENESS_STATUS_OK, LIVENESS_STATUS_REJECTED, FaceModel
from biometrics.quality import QualityConfig, check_quality


def make_reading(detection_score=0.9, face_width=131.0, yaw=0.0, live_status=LIVENESS_STATUS_OK):
    
    left, top = 100.0, 80.0
    return FaceModel(
        embedding=np.zeros(512, dtype=np.float32),
        detection_score=detection_score,
        bounding_box=(left, top, left + face_width, top + face_width),
        live_score=0.95,
        live_status=live_status,
        yaw=yaw,
    )


def test_good_reading_is_accepted():
    assert check_quality(make_reading()) is None


def test_farthest_acceptable_distance_is_accepted():
    
    assert check_quality(make_reading(face_width=77.0)) is None


@pytest.mark.parametrize("reading, expected_message", [
    (make_reading(detection_score=0.4), "Rosto pouco nítido. Melhore a iluminação e olhe para a câmera."),
    (make_reading(face_width=60.0), "Aproxime-se da câmera."),
    (make_reading(yaw=40.0), "Olhe de frente para a câmera."),
    (make_reading(yaw=-40.0), "Olhe de frente para a câmera."),
], ids=["blurry", "too_far", "turned_left", "turned_right"])
def test_bad_readings_get_a_message_for_the_student(reading, expected_message):
    assert check_quality(reading) == expected_message


def test_most_basic_problem_is_reported_first():
    blurry_and_far = make_reading(detection_score=0.4, face_width=60.0)

    assert check_quality(blurry_and_far).startswith("Rosto pouco nítido")


def test_turned_head_is_fine_when_frontal_is_not_required():
    
    assert check_quality(make_reading(yaw=40.0), require_frontal=False) is None


def test_missing_yaw_does_not_block():
    assert check_quality(make_reading(yaw=None)) is None


def test_rejected_liveness_only_matters_when_required():
    reading = make_reading(live_status=LIVENESS_STATUS_REJECTED)

    assert check_quality(reading) is None
    assert check_quality(reading, require_liveness=True) == "Centralize o rosto e afaste-se um pouco da câmera."


def test_limits_can_be_changed():
    strict = QualityConfig(min_face_width_px=150.0)

    assert check_quality(make_reading(face_width=131.0), config=strict) == "Aproxime-se da câmera."