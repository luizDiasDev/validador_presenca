from dataclasses import dataclass

from .models import LIVENESS_STATUS_OK, FaceModel


@dataclass(frozen=True)
class QualityConfig:
    
    min_detection_score: float = 0.60
    min_face_width_px: float = 75.0
    max_abs_yaw_degrees: float = 25.0


def check_quality(
    reading: FaceModel,
    config: QualityConfig = QualityConfig(),
    require_frontal: bool = True,
    require_liveness: bool = False,
) -> str | None:
    
    if reading.detection_score < config.min_detection_score:
        return "Rosto pouco nítido. Melhore a iluminação e olhe para a câmera."

    if reading.face_width() < config.min_face_width_px:
        return "Aproxime-se da câmera."

    head_turned_too_much = reading.yaw is not None and abs(reading.yaw) > config.max_abs_yaw_degrees
    if require_frontal and head_turned_too_much:
        return "Olhe de frente para a câmera."

    if require_liveness and reading.live_status != LIVENESS_STATUS_OK:
        
        return "Centralize o rosto e afaste-se um pouco da câmera."

    return None