import numpy as np

from biometrics.capture import CaptureConfig
from biometrics.challenge import ChallengeConfig, Direction
from biometrics.models import LIVENESS_STATUS_OK, FaceModel
from room_app.capture_session import MODE_CHECKIN, MODE_ENROLLMENT, run_face_capture

EMBEDDING_SIZE = 512
ANY_FRAME = object()


def embedding(seed, base=None):
    vector = np.random.default_rng(seed).normal(size=EMBEDDING_SIZE)
    if base is not None:
        vector = base + 0.02 * vector
    return (vector / np.linalg.norm(vector)).astype(np.float32)


STUDENT = embedding(1)
SOMEONE_ELSE = embedding(2)


def reading(face=STUDENT, yaw=0.0, seed=0):
    return FaceModel(
        embedding=embedding(seed + 100, base=face), detection_score=0.9,
        bounding_box=(100.0, 80.0, 231.0, 211.0), live_score=0.95, live_status=LIVENESS_STATUS_OK, yaw=yaw,
    )


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 0.1
        return self.now


def scripted_engine(*frames):
    remaining = list(frames)

    def analyze(frame):
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]
    return analyze


FRONT = [[reading(seed=seed)] for seed in range(5)]
TURN_RIGHT_THEN_LEFT = [[reading(yaw=-30.0)], [reading(yaw=0.0)], [reading(yaw=30.0)]]


def test_checkin_capture_with_challenge_builds_the_checkin_payload():
    instructions = []

    outcome = run_face_capture(lambda: ANY_FRAME, scripted_engine(*FRONT, *TURN_RIGHT_THEN_LEFT), MODE_CHECKIN,
                               on_instruction=instructions.append,
                               challenge_steps=(Direction.RIGHT, Direction.LEFT), clock=FakeClock())

    assert outcome.success
    assert outcome.challenge_passed is True
    assert set(outcome.payload) == {"embedding", "liveness_score", "liveness_status", "challenge_passed"}
    assert "Vire a cabeça para a direita." in instructions
    assert instructions[-1] == "Prova de vida concluída."


def test_enrollment_capture_sends_every_sample():
    outcome = run_face_capture(lambda: ANY_FRAME, scripted_engine(*FRONT, *TURN_RIGHT_THEN_LEFT), MODE_ENROLLMENT,
                               challenge_steps=(Direction.RIGHT, Direction.LEFT), clock=FakeClock())

    assert len(outcome.payload["samples"]) == 5


def test_another_person_cannot_do_the_challenge_for_the_student():
    swapped = [[reading(face=SOMEONE_ELSE, yaw=-30.0)], [reading(face=SOMEONE_ELSE, yaw=0.0)],
               [reading(face=SOMEONE_ELSE, yaw=30.0)]]

    outcome = run_face_capture(lambda: ANY_FRAME, scripted_engine(*FRONT, *swapped), MODE_CHECKIN,
                               challenge_config=ChallengeConfig(step_timeout_seconds=2.0),
                               challenge_steps=(Direction.RIGHT, Direction.LEFT), clock=FakeClock())

    assert outcome.challenge_passed is False
    assert outcome.payload["challenge_passed"] is False


def test_failed_capture_has_no_payload():
    outcome = run_face_capture(lambda: ANY_FRAME, scripted_engine([]), MODE_CHECKIN,
                               capture_config=CaptureConfig(timeout_seconds=1.0), clock=FakeClock())

    assert not outcome.success
    assert outcome.payload is None
    assert outcome.capture.reason == "Nenhum rosto detectado."
