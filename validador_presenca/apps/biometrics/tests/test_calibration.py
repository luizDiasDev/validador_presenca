import json
import uuid

import numpy as np
import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.accounts.models import Usuario
from apps.audit.models import AuditLog
from apps.biometrics.domain.services.biometric_service import (
    COMPARISON_DONE,
    COMPARISON_INVALID_CAPTURE,
    COMPARISON_NOT_ENROLLED,
    COMPARISON_UNREADABLE_TEMPLATE,
    BiometricService,
    BiometricTermUnavailableError,
    EnrollmentRejectedError,
    MissingConsentError,
)
from apps.biometrics.models import Biometria
from apps.institution.models import Institution
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD, Termo

pytestmark = pytest.mark.django_db

EMBEDDING_SIZE = 512
GOOD_LIVENESS = {"live_score": 0.95, "live_status": "ok", "challenge_passed": True}


# ---------- helpers ----------

def unit_vector(seed, base=None, noise=0.0):
    random_generator = np.random.default_rng(seed)
    if base is None:
        vector = random_generator.normal(size=EMBEDDING_SIZE)
    else:
        vector = base + noise * random_generator.normal(size=EMBEDDING_SIZE)
    return vector / np.linalg.norm(vector)


STUDENT_FACE = unit_vector(1)
OTHER_FACE = unit_vector(2)


def samples_of(face, count=5):
    return [list(unit_vector(seed, base=face, noise=0.02)) for seed in range(100, 100 + count)]


def create_student():
    suffix = uuid.uuid4().hex[:8]
    institution = Institution.objects.create(nome=f"UMC {suffix}", cnpj=suffix.ljust(14, "0"))
    return Usuario.objects.create_user(
        email=f"aluno.{suffix}@umc.br", password="SenhaForte123", instituicao=institution,
    )


def publish_biometric_term(institution):
    return Termo.objects.create(
        instituicao=institution, tipo=Termo.TIPO_BIOMETRICO, versao="1.0",
        titulo="Termo biométrico", conteudo="Conteúdo", documento_hash="a" * 64, ativo=True,
    )


def student_with_consent():
    student = create_student()
    publish_biometric_term(student.instituicao)
    BiometricService().grant_consent(student)
    return student


def enrolled_student(face=STUDENT_FACE):
    student = student_with_consent()
    BiometricService().enroll(student, samples_of(face), **GOOD_LIVENESS)
    return student


# ---------- consentimento ----------

def test_grant_consent_creates_the_acceptance_and_audits_it():
    student = create_student()
    publish_biometric_term(student.instituicao)

    consent = BiometricService().grant_consent(student, evidence={"ip": "10.0.0.1"})

    assert consent.termo.tipo == Termo.TIPO_BIOMETRICO
    assert AuditLog.objects.filter(acao="CONSENTIMENTO_BIOMETRICO", autor_id=student.id).exists()


def test_granting_consent_twice_does_not_duplicate():
    student = student_with_consent()

    BiometricService().grant_consent(student)

    assert AceiteTermo.objects.filter(usuario=student, termo__tipo=Termo.TIPO_BIOMETRICO).count() == 1


def test_grant_consent_without_published_term_fails():
    with pytest.raises(BiometricTermUnavailableError):
        BiometricService().grant_consent(create_student())


def test_revoked_consent_is_not_active():
    student = student_with_consent()
    AceiteTermo.objects.filter(usuario=student).update(data_revogada="2026-11-01T00:00:00Z")

    assert BiometricService().get_active_consent(student) is None


# ---------- cadastro ----------

def test_enroll_without_consent_is_refused():
    with pytest.raises(MissingConsentError):
        BiometricService().enroll(create_student(), samples_of(STUDENT_FACE), **GOOD_LIVENESS)


def test_enroll_stores_only_the_encrypted_vector():
    student = enrolled_student()

    biometria = Biometria.objects.get(usuario=student)
    assert biometria.qtd_amostras == 5
    assert biometria.dimensao == EMBEDDING_SIZE
    assert biometria.algoritmo_usado == "insightface-buffalo_l"
    assert len(bytes(biometria.embedding_cifrado)) > EMBEDDING_SIZE * 4


def test_audit_log_never_contains_the_vector():
    student = enrolled_student()

    log = AuditLog.objects.get(acao="BIOMETRIA_CADASTRADA", autor_id=student.id)
    assert "embedding" not in json.dumps(log.payload)
    assert len(json.dumps(log.payload)) < 300


def test_enrolling_again_replaces_the_template():
    student = enrolled_student(face=STUDENT_FACE)

    BiometricService().enroll(student, samples_of(OTHER_FACE), **GOOD_LIVENESS)

    assert Biometria.objects.filter(usuario=student).count() == 1
    assert BiometricService().compare(student.id, OTHER_FACE).score == 1.0


@pytest.mark.parametrize("weak_liveness", [
    {"live_score": 0.10, "live_status": "ok", "challenge_passed": True},     # foto na tela
    {"live_score": 0.95, "live_status": "ok", "challenge_passed": False},    # não virou a cabeça
    {"live_score": None, "live_status": "input_rejected", "challenge_passed": True},
], ids=["photo", "challenge_failed", "not_evaluated"])
def test_enroll_requires_proof_of_life(weak_liveness):
    student = student_with_consent()

    with pytest.raises(EnrollmentRejectedError):
        BiometricService().enroll(student, samples_of(STUDENT_FACE), **weak_liveness)

    assert not Biometria.objects.filter(usuario=student).exists()


def test_enroll_refuses_samples_from_different_people():
    student = student_with_consent()
    mixed_samples = samples_of(STUDENT_FACE, count=3) + samples_of(OTHER_FACE, count=2)

    with pytest.raises(EnrollmentRejectedError):
        BiometricService().enroll(student, mixed_samples, **GOOD_LIVENESS)


def test_enroll_refuses_invalid_vector_and_saves_nothing():
    student = student_with_consent()

    with pytest.raises(Exception):
        BiometricService().enroll(student, [[1.0] * 10], **GOOD_LIVENESS)

    assert not Biometria.objects.filter(usuario=student).exists()


# ---------- comparação ----------

def test_same_face_gets_a_high_score():
    student = enrolled_student()

    result = BiometricService().compare(student.id, list(unit_vector(500, base=STUDENT_FACE, noise=0.02)))

    assert result.status == COMPARISON_DONE
    assert result.cosine > 0.8
    assert result.score == 1.0


def test_other_face_gets_zero():
    student = enrolled_student()

    result = BiometricService().compare(student.id, list(OTHER_FACE))

    assert result.status == COMPARISON_DONE
    assert result.score == 0.0


def test_compare_without_enrollment_says_so():
    result = BiometricService().compare(create_student().id, list(STUDENT_FACE))

    assert result.status == COMPARISON_NOT_ENROLLED
    assert result.reason == "Biometria não cadastrada"


def test_compare_with_invalid_capture_does_not_crash():
    student = enrolled_student()

    result = BiometricService().compare(student.id, [float("nan")] * EMBEDDING_SIZE)

    assert result.status == COMPARISON_INVALID_CAPTURE
    assert result.score == 0.0


def test_template_encrypted_with_another_key_is_reported_as_unreadable():
    student = enrolled_student()

    with override_settings(BIOMETRIC_ENCRYPTION_KEY=Fernet.generate_key()):
        result = BiometricService().compare(student.id, list(STUDENT_FACE))

    assert result.status == COMPARISON_UNREADABLE_TEMPLATE


def test_compare_follows_the_configured_calibration():
    student = enrolled_student()
    capture = list(unit_vector(500, base=STUDENT_FACE, noise=0.02))

    with override_settings(BIOMETRICS={"MIN_COSINE": 0.95, "MAX_COSINE": 0.99}):
        strict_result = BiometricService().compare(student.id, capture)

    assert strict_result.score < 1.0


def test_missing_encryption_key_fails_with_a_clear_message():
    with override_settings(BIOMETRIC_ENCRYPTION_KEY=None):
        with pytest.raises(ImproperlyConfigured, match="BIOMETRIC_ENCRYPTION_KEY"):
            BiometricService().cipher


# ---------- revogação ----------

def test_revoke_deletes_template_revokes_consent_and_audits():
    student = enrolled_student()

    assert BiometricService().revoke(student) is True

    assert not Biometria.objects.filter(usuario=student).exists()
    assert BiometricService().get_active_consent(student) is None
    assert AuditLog.objects.filter(acao="BIOMETRIA_REVOGADA", autor_id=student.id).exists()


def test_after_revoking_a_new_enrollment_needs_new_consent():
    student = enrolled_student()
    BiometricService().revoke(student)

    with pytest.raises(MissingConsentError):
        BiometricService().enroll(student, samples_of(STUDENT_FACE), **GOOD_LIVENESS)


def test_revoke_with_nothing_enrolled_does_not_audit():
    student = create_student()

    assert BiometricService().revoke(student) is False
    assert not AuditLog.objects.filter(acao="BIOMETRIA_REVOGADA", autor_id=student.id).exists()


def test_fulfilling_a_revocation_request_closes_it():
    student = enrolled_student()
    request = SolicitacaoLGPD.objects.create(usuario=student, tipo=SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA)

    BiometricService().fulfill_revocation_request(request)

    request.refresh_from_db()
    assert request.status == SolicitacaoLGPD.STATUS_ATENDIDA
    assert request.data_resposta is not None
    assert not Biometria.objects.filter(usuario=student).exists()


def test_request_of_another_type_is_not_fulfilled_here():
    student = create_student()
    request = SolicitacaoLGPD.objects.create(usuario=student, tipo=SolicitacaoLGPD.TIPO_EXPORTAR_DADOS)

    with pytest.raises(ValueError):
        BiometricService().fulfill_revocation_request(request)