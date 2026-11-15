import logging
import time

from biometrics.camera import CameraUnavailableError

from .api import ApiError
from .capture_session import MODE_ENROLLMENT, run_face_capture
from .live_camera import LiveCamera

logger = logging.getLogger("adsum.captura")

ENROLLMENT_DONE = "Rosto cadastrado! Nesta primeira vez, o professor confirma a sua presença."


def capture_and_send(api, engine, config, authorization, camera_factory, on_frame, on_instruction,
                     clock=time.perf_counter):
    mode = authorization["modo"]
    try:
        camera = camera_factory(config.camera_index, config.camera_backend)
    except CameraUnavailableError as error:
        logger.warning("Câmera indisponível: %s", error)
        return "PENDING", f"Câmera indisponível: {error}"

    live_camera = LiveCamera(camera, on_frame=on_frame)

    def analyze(frame):
        started_at = clock()
        faces = engine.analyze(frame)
        logger.info("análise: %d rosto(s) em %.0f ms", len(faces), (clock() - started_at) * 1000)
        return faces

    try:
        outcome = run_face_capture(live_camera.next_frame, analyze, mode, on_instruction=on_instruction)
        if not outcome.success:
            logger.info("captura sem sucesso: %s", outcome.capture.reason)
            return "PENDING", outcome.capture.reason
        logger.info(
            "captura concluída: vida=%s (%s), desafio=%s",
            outcome.capture.live_score, outcome.capture.live_status, outcome.challenge_passed,
        )
        answer = api.send_face(authorization["presenca_id"], outcome.payload)
    except ApiError as error:
        logger.warning("servidor recusou o envio: %s", error)
        return "PENDING", str(error)
    except Exception as error:  # noqa: BLE001
        logger.exception("falha na captura")
        return "PENDING", f"Falha na captura do rosto: {error}"
    finally:
        live_camera.stop()

    status = answer.get("status", "PENDING")
    if mode == MODE_ENROLLMENT and status == "PENDING":
        return status, ENROLLMENT_DONE
    return status, answer.get("mensagem", "")
