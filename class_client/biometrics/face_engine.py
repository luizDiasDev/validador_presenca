import numpy as np

from .models import (
    LIVENESS_STATUS_OK,
    LIVENESS_STATUS_REJECTED,
    LIVENESS_STATUS_UNAVAILABLE,
    FaceModel,
)


class FaceEngine:
    def __init__(
        self,
        model_name: str = "buffalo_l",
        detection_size: tuple = (640, 640),
        use_liveness: bool = True,
        providers: tuple = ("CPUExecutionProvider",),
    ):
        self.model_name = model_name
        self.detection_size = detection_size
        self.use_liveness = use_liveness
        self.providers = list(providers)
        self._face_analysis = None

    def is_loaded(self) -> bool:
        return self._face_analysis is not None

    def load(self) -> "FaceEngine":
        from insightface.app import FaceAnalysis

        options = {"name": self.model_name, "providers": self.providers}

        if self.use_liveness:
            options.update(addons=["liveness"], liveness_mode="observe")

        # ** monta um dicionario com os mesmos parametros de options
        self._face_analysis = FaceAnalysis(**options)

        # ctx_id=-1 = rodar na CPU
        self._face_analysis.prepare(ctx_id=-1, det_size=self.detection_size)
        
        return self

    def analyze(self, frame_bgr) -> list[FaceModel]:
        
        if not self.is_loaded:
            self.load()

        detected_faces = self._face_analysis.get(frame_bgr)

        return [self._to_face_model(face) for face in detected_faces]

    @staticmethod
    def _to_face_model(face) -> FaceModel:
        
        embedding = getattr(face, "normed_embedding", None)
        
        if embedding is None:

            # garante comprimento 1 mesmo se a biblioteca não devolver o vetor já normalizado
            raw_embedding = np.asarray(face.embedding, dtype=np.float32)
            
            embedding = raw_embedding / np.linalg.norm(raw_embedding)

        liveness = getattr(face, "liveness", None) or {}

        live_status = liveness.get("status", LIVENESS_STATUS_UNAVAILABLE)

        if live_status not in (LIVENESS_STATUS_OK, LIVENESS_STATUS_REJECTED):
            live_status = LIVENESS_STATUS_UNAVAILABLE

        pitch = yaw = roll = None

        head_pose = getattr(face, "pose", None)

        if head_pose is not None:
            # o InsightFace devolve em graus
            pitch, yaw, roll = (float(angle) for angle in head_pose)

        return FaceModel(
            embedding=np.asarray(embedding, dtype=np.float32),
            detection_score=float(face.det_score),
            bounding_box=tuple(float(coordinate) for coordinate in face.bbox),
            live_score=liveness.get("live_score"),
            live_status=live_status,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )
