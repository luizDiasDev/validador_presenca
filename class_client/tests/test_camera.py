import cv2
import numpy as np

from biometrics.camera import is_real_frame


def test_black_frame_is_not_real():
    assert not is_real_frame(np.zeros((720, 1280, 3), dtype=np.uint8))


def test_loading_spinner_is_not_real():
    spinner = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(spinner, (640, 360), 65, (255, 255, 255), 14)

    assert not is_real_frame(spinner)


def test_lit_room_is_real():
    assert is_real_frame(np.full((720, 1280, 3), 90, dtype=np.uint8))


def test_missing_frame_is_not_real():
    assert not is_real_frame(None)
