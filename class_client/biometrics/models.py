from dataclasses import dataclass

import numpy as np

LIVENESS_STATUS_OK = "ok"
LIVENESS_STATUS_REJECTED = "input_rejected"
LIVENESS_STATUS_UNAVAILABLE = "unavailable"

@dataclass(frozen=True)
class FaceModel:
    embedding: np.ndarray            # 512 números com comprimento 1: o "resumo" do rosto
    detection_score: float           # certeza do detector de que aquilo é um rosto (0 a 1)
    bounding_box: tuple              # retângulo do rosto na imagem: (guarda x1, y1, x2, y2) em pixels
    live_score: float | None = None  # probabilidade de ser pessoa real (0 a 1)
    live_status: str = LIVENESS_STATUS_UNAVAILABLE
    yaw: float | None = None         # graus: cabeça virando para os lados
    pitch: float | None = None       # graus: cabeça para cima ou para baixo
    roll: float | None = None        # graus: cabeça inclinada (orelha em direção ao ombro)

    def face_width(self) -> float:
        left, _, right, _ = self.bounding_box
        return float(right - left)