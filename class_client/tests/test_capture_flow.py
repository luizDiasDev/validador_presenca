import itertools
import threading
import time

import numpy as np

from biometrics.camera import CameraUnavailableError
from room_app.capture_flow import ENROLLMENT_DONE, capture_and_send
from room_app.capture_session import MODE_CHECKIN, MODE_ENROLLMENT
from room_app.config import RoomConfig
from room_app.live_camera import LiveCamera
from tests.test_room_capture_session import reading


class FakeCamera:
    def __init__(self):
        self.counter = itertools.count(1)
        self.released = threading.Event()

    def read(self):
        time.sleep(0.002)
        return True, np.full((4, 4, 3), next(self.counter), dtype=np.uint8)

    def release(self):
        self.released.set()


class FakeApi:
    def __init__(self, answer):
        self.answer = answer
        self.sent = []

    def send_face(self, presenca_id, payload):
        self.sent.append((presenca_id, payload))
        return self.answer


class CooperativeEngine:
    def __init__(self):
        self.calls = 0

    def analyze(self, frame):
        self.calls += 1
        if self.calls <= 5:
            return [reading(seed=self.calls)]
        yaw = (-30.0, 0.0, 30.0, 0.0)[self.calls % 4]
        return [reading(yaw=yaw, seed=self.calls)]


class BrokenEngine:
    def analyze(self, frame):
        raise RuntimeError("modelo corrompido")


def run(engine, mode, camera, api=None):
    frames, instructions = [], []
    status, message = capture_and_send(
        api or FakeApi({"status": "APPROVED", "mensagem": "Presença confirmada."}),
        engine, RoomConfig(), {"modo": mode, "presenca_id": 7}, lambda index, backend: camera,
        on_frame=frames.append, on_instruction=instructions.append,
    )
    return status, message, frames, instructions


def test_live_camera_hands_out_only_new_frames_and_previews_them():
    camera = FakeCamera()
    previews = []
    live = LiveCamera(camera, on_frame=previews.append)

    first = live.next_frame()
    second = live.next_frame()
    live.stop()

    assert first is not None and second is not None
    assert second[0, 0, 0] > first[0, 0, 0]
    assert previews
    assert camera.released.is_set()


def test_checkin_capture_sends_the_face_and_shows_the_server_answer():
    camera = FakeCamera()
    api = FakeApi({"status": "APPROVED", "mensagem": "Presença confirmada."})

    status, message, frames, instructions = run(CooperativeEngine(), MODE_CHECKIN, camera, api)

    assert (status, message) == ("APPROVED", "Presença confirmada.")
    assert api.sent[0][0] == 7
    assert "embedding" in api.sent[0][1]
    assert any(text.startswith("Prova de vida:") for text in instructions)
    assert frames
    assert camera.released.is_set()


def test_enrollment_explains_that_the_teacher_confirms_the_first_presence():
    status, message, _, instructions = run(
        CooperativeEngine(), MODE_ENROLLMENT, FakeCamera(),
        FakeApi({"status": "PENDING", "mensagem": "Presença registrada. O professor vai confirmar."}),
    )

    assert (status, message) == ("PENDING", ENROLLMENT_DONE)
    assert instructions[0].startswith("Cadastrando o seu rosto: leitura 1 de 5")


def test_an_engine_error_ends_the_capture_instead_of_freezing_the_screen():
    camera = FakeCamera()

    status, message, _, _ = run(BrokenEngine(), MODE_CHECKIN, camera)

    assert status == "PENDING"
    assert "modelo corrompido" in message
    assert camera.released.is_set()


def test_missing_camera_keeps_the_presence_pending():
    def no_camera(index, backend):
        raise CameraUnavailableError("Câmera 0 (auto) não abriu.")

    status, message = capture_and_send(
        FakeApi({}), CooperativeEngine(), RoomConfig(), {"modo": MODE_CHECKIN, "presenca_id": 7}, no_camera,
        on_frame=lambda frame: None, on_instruction=lambda text: None,
    )

    assert status == "PENDING"
    assert "Câmera indisponível" in message
