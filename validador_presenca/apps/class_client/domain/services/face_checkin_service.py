from apps.accounts.models import Usuario
from apps.biometrics import conf
from apps.biometrics.domain.embedding import average_embedding
from apps.biometrics.domain.services.biometric_service import (
    BiometricService,
    EnrollmentRejectedError,
    MissingConsentError,
)
from apps.validator.domain.case import reevaluate_checkin
from apps.validator.models import PresencaRecord

from .face_authorization_service import MODE_ENROLLMENT, FaceAuthorization

LIVENESS_FIELDS = ("liveness_score", "liveness_status", "challenge_passed")


class FaceCheckinError(Exception):
    pass


class FaceCheckinService:
    def __init__(self, biometric_service: BiometricService | None = None):
        self.biometric_service = biometric_service or BiometricService()

    def complete(self, authorization: FaceAuthorization, face_payload: dict) -> PresencaRecord:
        record = PresencaRecord.objects.get(pk=authorization.presenca_id)
        results_pack = {**authorization.base_pack, **_liveness_fields(face_payload)}

        if authorization.mode == MODE_ENROLLMENT:
            results_pack.update(self._enroll(authorization, record, face_payload))
        else:
            if "embedding" not in face_payload:
                raise FaceCheckinError("Envio sem o vetor do rosto.")
            results_pack["embedding"] = face_payload["embedding"]

        reevaluate_checkin(record, results_pack)
        record.refresh_from_db()
        return record

    def _enroll(self, authorization, record, face_payload) -> dict:
        samples = face_payload.get("samples")
        if not samples:
            raise FaceCheckinError("Envio de cadastro sem as amostras do rosto.")

        student = Usuario.objects.get(pk=authorization.aluno_id)
        try:
            self.biometric_service.enroll(
                student,
                samples,
                face_payload.get("liveness_score"),
                face_payload.get("liveness_status"),
                face_payload.get("challenge_passed"),
            )
        except (EnrollmentRejectedError, MissingConsentError) as error:
            record.motivo = f"Cadastro facial não concluído: {error}"
            record.save(update_fields=["motivo", "data_atualizacao"])
            raise FaceCheckinError(str(error)) from error

        # o rosto do dia do cadastro é comparado com ele mesmo; por isso o motor manda para revisão
        mean = average_embedding(samples, conf.get_setting("EMBEDDING_SIZE"))
        return {"embedding": mean.tolist(), "biometric_enrolled_in_this_checkin": True}


def _liveness_fields(face_payload: dict) -> dict:
    return {field: face_payload.get(field) for field in LIVENESS_FIELDS}
