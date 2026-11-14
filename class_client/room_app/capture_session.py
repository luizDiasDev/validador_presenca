import time
from dataclasses import dataclass

import numpy as np

from biometrics.capture import CaptureConfig, CaptureResult, collect_samples
from biometrics.challenge import ChallengeConfig, ChallengeState, HeadTurnChallenge, draw_challenge
from biometrics.payload import build_checkin_payload, build_enrollment_payload

MODE_CHECKIN = "checkin"
MODE_ENROLLMENT = "cadastro"
# o rosto do desafio tem que ser o mesmo das leituras (impede trocar de pessoa no meio)
MIN_COSINE_SAME_PERSON = 0.50


@dataclass(frozen=True)
class FaceCaptureOutcome:
    capture: CaptureResult
    challenge_passed: bool | None
    payload: dict | None   # pronto para enviar; None quando a captura não deu certo

    @property
    def success(self) -> bool:
        return self.payload is not None


def run_face_capture(
    read_frame,
    analyze_frame,
    mode: str,
    on_instruction=lambda text: None,
    capture_config: CaptureConfig = CaptureConfig(),
    challenge_config: ChallengeConfig = ChallengeConfig(),
    challenge_steps=None,
    clock=time.monotonic,
) -> FaceCaptureOutcome:
    # 1) leituras de frente: o vetor do rosto e a nota de prova de vida
    if mode == MODE_ENROLLMENT:
        capture_config = CaptureConfig(
            samples_needed=max(capture_config.samples_needed, 5),
            timeout_seconds=capture_config.timeout_seconds,
            min_pairwise_cosine=capture_config.min_pairwise_cosine,
            quality=capture_config.quality,
        )

    def report_progress(collected, needed, hint):
        on_instruction(hint or f"Olhe para a câmera ({collected}/{needed})")

    capture = collect_samples(read_frame, analyze_frame, capture_config, require_liveness=True,
                              clock=clock, on_progress=report_progress)
    if not capture.success:
        on_instruction(capture.reason)
        return FaceCaptureOutcome(capture, None, None)

    # 2) desafio de virar a cabeça, com o mesmo rosto
    challenge = HeadTurnChallenge(challenge_steps or draw_challenge(), challenge_config, clock=clock)
    on_instruction(challenge.instruction)
    while challenge.state is ChallengeState.IN_PROGRESS:
        frame = read_frame()
        yaw = _yaw_of_the_same_person(analyze_frame(frame), capture.mean_embedding) if frame is not None else None
        challenge.update(yaw)
        on_instruction(challenge.instruction)

    challenge_passed = challenge.state is ChallengeState.PASSED
    build = build_enrollment_payload if mode == MODE_ENROLLMENT else build_checkin_payload
    return FaceCaptureOutcome(capture, challenge_passed, build(capture, challenge_passed))


def _yaw_of_the_same_person(faces, reference_embedding) -> float | None:
    if len(faces) != 1:
        return None
    face = faces[0]
    if float(np.dot(face.embedding, reference_embedding)) < MIN_COSINE_SAME_PERSON:
        return None
    return face.yaw
