import uuid

import numpy as np
import pytest

from apps.accounts.models import Usuario
from apps.audit.models import AuditLog
from apps.biometrics.domain.services.biometric_service import BiometricService
from apps.institution.models import Institution
from apps.privacy.models import Termo
from apps.validator.domain.case import try_checkin
from apps.validator.domain.values.verdict import Verdict
from apps.validator.models import PresencaRecord

pytestmark = pytest.mark.django_db

EMBEDDING_SIZE = 512
REAL_PERSON = {"liveness_score": 0.95, "liveness_status": "ok", "challenge_passed": True}
PHOTO_ON_SCREEN = {"liveness_score": 0.0, "liveness_status": "ok", "challenge_passed": True}


def unit_vector(seed, base=None, noise=0.0):
    random_generator = np.random.default_rng(seed)
    if base is None:
        vector = random_generator.normal(size=EMBEDDING_SIZE)
    else:
        vector = base + noise * random_generator.normal(size=EMBEDDING_SIZE)
    return vector / np.linalg.norm(vector)


STUDENT_FACE = unit_vector(1)
SOMEONE_ELSE_FACE = unit_vector(2)


def capture_of(face, seed=900):
    return [float(value) for value in unit_vector(seed, base=face, noise=0.02)]


def create_student():
    suffix = uuid.uuid4().hex[:8]
    institution = Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))
    Termo.objects.create(
        instituicao=institution, tipo=Termo.TIPO_BIOMETRICO, versao="1.0",
        titulo="Termo biométrico", conteudo="Conteúdo", documento_hash="a" * 64, ativo=True,
    )
    return Usuario.objects.create_user(
        email=f"aluno.{suffix}@umc.br", password="SenhaForte123", instituicao=institution,
    )


def enrolled_student():
    student = create_student()
    service = BiometricService()
    service.grant_consent(student)
    samples = [[float(value) for value in unit_vector(seed, base=STUDENT_FACE, noise=0.02)] for seed in range(5)]
    service.enroll(student, samples, live_score=0.95, live_status="ok", challenge_passed=True)
    return student


def checkin_pack(student, face=None, liveness=REAL_PERSON, **overrides):
    pack = {
        "aluno_id": student.id,
        "qr_code": True,
        "qr_token_hash": "f" * 64,
        "geo_valida": True,
        "geo_motivo": "",
        **liveness,
    }
    if face is not None:
        pack["embedding"] = capture_of(face)
    pack.update(overrides)
    return pack


def test_enrolled_student_with_matching_face_is_approved_and_recorded():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE))

    assert verdict == Verdict.APPROVED
    record = PresencaRecord.objects.get()
    assert record.status == "APPROVED" and record.aprovado
    assert float(record.score_facial) == pytest.approx(1.0)
    assert float(record.score_vida) == pytest.approx(0.95)
    assert record.qr_token_hash == "f" * 64
    assert AuditLog.objects.filter(origem="checkin", acao="APPROVED", autor_id=student.id).exists()


def test_someone_else_in_front_of_the_camera_is_rejected():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=SOMEONE_ELSE_FACE))

    assert verdict == Verdict.REJECTED
    assert PresencaRecord.objects.get().motivo == "Rosto não confere com o cadastro"


def test_photo_on_screen_goes_to_the_professor():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE, liveness=PHOTO_ON_SCREEN))

    assert verdict == Verdict.PENDING
    record = PresencaRecord.objects.get()

    assert float(record.score_final) == pytest.approx(0.70)


def test_student_without_biometrics_goes_to_the_professor():
    student = create_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE))

    assert verdict == Verdict.PENDING
    assert PresencaRecord.objects.get().motivo == "Biometria não cadastrada"


def test_webcam_failure_goes_to_the_professor():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=None))

    assert verdict == Verdict.PENDING
    assert "Rosto não capturado" in PresencaRecord.objects.get().motivo


def test_checkin_of_the_enrollment_day_goes_to_the_professor():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE, biometric_enrolled_in_this_checkin=True))

    assert verdict == Verdict.PENDING
    assert "Primeiro check-in após o cadastro facial" in PresencaRecord.objects.get().motivo


def test_student_who_revoked_biometrics_goes_to_the_professor():
    student = enrolled_student()
    BiometricService().revoke(student)

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE))

    assert verdict == Verdict.PENDING


def test_invalid_qr_code_is_rejected_even_with_a_matching_face():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE, qr_code=False))

    assert verdict == Verdict.REJECTED
    assert PresencaRecord.objects.get().motivo == "Token inválido ou expirado"


def test_outside_the_campus_is_rejected_even_with_a_matching_face():
    student = enrolled_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE,
                                       geo_valida=False, geo_motivo="Localização fora do raio do campus"))

    assert verdict == Verdict.REJECTED
    assert PresencaRecord.objects.get().motivo == "Localização fora do raio do campus"


def test_invalid_qr_code_wins_over_missing_biometrics():
    student = create_student()

    verdict = try_checkin(checkin_pack(student, face=STUDENT_FACE, qr_code=False))

    assert verdict == Verdict.REJECTED