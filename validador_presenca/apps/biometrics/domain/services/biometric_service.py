
from dataclasses import dataclass

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from apps.accounts.domain.cipher import Cipher
from apps.audit.domain.log_register import LogRegister
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD, Termo

from ... import conf
from ...models import Biometria
from ..calibration import cosine_to_score, liveness_to_score
from ..embedding import (
    InvalidEmbeddingError,
    average_embedding,
    bytes_to_embedding,
    cosine_similarity,
    embedding_to_bytes,
    validate_and_normalize,
)

AUDIT_ORIGIN = "biometria"

MIN_COSINE_BETWEEN_ENROLLMENT_SAMPLES = 0.50


class MissingConsentError(Exception):
    pass


class BiometricTermUnavailableError(Exception):
    pass


class EnrollmentRejectedError(Exception):
    pass

COMPARISON_DONE = "compared"
COMPARISON_NOT_ENROLLED = "not_enrolled"
COMPARISON_INVALID_CAPTURE = "invalid_capture"
COMPARISON_UNREADABLE_TEMPLATE = "unreadable_template"


@dataclass(frozen=True)
class ComparisonResult:
    status: str
    score: float
    cosine: float | None = None
    reason: str = ""


class BiometricService:

    def __init__(self, cipher=None, audit_log=None):
        
        self._cipher = cipher
        self._audit_log = audit_log or LogRegister()

    @property
    def cipher(self) -> Cipher:
        if self._cipher is None:
            key = getattr(settings, "BIOMETRIC_ENCRYPTION_KEY", None)
            if not key:
                raise ImproperlyConfigured(
                    "Defina BIOMETRIC_ENCRYPTION_KEY (Fernet.generate_key()) no ambiente."
                )
            
            self._cipher = Cipher(key)
        return self._cipher

    # ---------- consentimento ----------

    def get_active_consent(self, user) -> AceiteTermo | None:
        
        return (
            AceiteTermo.objects.filter(
                usuario=user,
                termo__tipo=Termo.TIPO_BIOMETRICO,
                termo__ativo=True,
                concedido=True,
                data_revogada__isnull=True,
            )
            .order_by("-data_concedido")
            .first()
        )

    def grant_consent(self, user, evidence: dict | None = None) -> AceiteTermo:
        
        existing_consent = self.get_active_consent(user)
        if existing_consent:
            return existing_consent

        active_terms = Termo.objects.filter(tipo=Termo.TIPO_BIOMETRICO, ativo=True)
        if user.instituicao_id:
            active_terms = active_terms.filter(instituicao_id=user.instituicao_id)
        term = active_terms.order_by("-data_publicacao").first()
        if term is None:
            raise BiometricTermUnavailableError("Nenhum termo biométrico ativo publicado.")

        consent = AceiteTermo.objects.create(
            usuario=user, termo=term, concedido=True, evidencia=evidence or {},
        )
        self._audit(user.id, "CONSENTIMENTO_BIOMETRICO", "aceite_termo", consent.id,
                    {"termo_versao": term.versao})
        return consent

    # ---------- cadastro ----------

    @transaction.atomic
    def enroll(self, user, samples, live_score, live_status, challenge_passed) -> Biometria:

        if self.get_active_consent(user) is None:
            raise MissingConsentError("Consentimento biométrico ausente ou revogado.")

        liveness = liveness_to_score(
            live_score, live_status, challenge_passed,
            approval_threshold=conf.get_setting("LIVENESS_APPROVAL"),
        )
        if not liveness.approved:
            raise EnrollmentRejectedError(liveness.reason)

        embedding_size = conf.get_setting("EMBEDDING_SIZE")
        normalized_samples = [validate_and_normalize(sample, embedding_size) for sample in samples]
        
        self._ensure_samples_are_the_same_person(normalized_samples)

        template = average_embedding(normalized_samples, embedding_size)
        encrypted_template = self.cipher.encrypt_bytes(embedding_to_bytes(template))

        biometria, created = Biometria.objects.update_or_create(
            usuario=user,
            defaults={
                "embedding_cifrado": encrypted_template,
                "algoritmo_usado": conf.get_setting("ALGORITHM"),
                "dimensao": embedding_size,
                "qtd_amostras": len(normalized_samples),
            },
        )
        self._audit(user.id, "BIOMETRIA_CADASTRADA", "biometria", biometria.id, {
            "algoritmo": biometria.algoritmo_usado,
            "qtd_amostras": biometria.qtd_amostras,
            "substituiu_anterior": not created,
        })
        return biometria

    @staticmethod
    def _ensure_samples_are_the_same_person(normalized_samples) -> None:
        for first_index, first_sample in enumerate(normalized_samples):
            for second_sample in normalized_samples[first_index + 1:]:
                if cosine_similarity(first_sample, second_sample) < MIN_COSINE_BETWEEN_ENROLLMENT_SAMPLES:
                    raise EnrollmentRejectedError("As amostras do cadastro não parecem ser da mesma pessoa.")

    # ---------- comparação ----------

    def get_template(self, user_id):
        
        biometria = Biometria.objects.filter(usuario_id=user_id).first()
        if biometria is None:
            return None
        raw_bytes = self.cipher.decrypt_bytes(biometria.embedding_cifrado)
        return bytes_to_embedding(raw_bytes, biometria.dimensao)

    def compare(self, user_id, captured_embedding) -> ComparisonResult:
        
        try:
            capture = validate_and_normalize(captured_embedding, conf.get_setting("EMBEDDING_SIZE"))
        except InvalidEmbeddingError as error:
            return ComparisonResult(COMPARISON_INVALID_CAPTURE, 0.0, reason=f"Captura inválida: {error}")

        try:
            template = self.get_template(user_id)
        except (InvalidToken, InvalidEmbeddingError):
            return ComparisonResult(COMPARISON_UNREADABLE_TEMPLATE, 0.0,
                                    reason="Template biométrico ilegível; é preciso cadastrar o rosto de novo")
        if template is None:
            return ComparisonResult(COMPARISON_NOT_ENROLLED, 0.0, reason="Biometria não cadastrada")

        cosine = cosine_similarity(capture, template)
        score = cosine_to_score(cosine, conf.get_setting("MIN_COSINE"), conf.get_setting("MAX_COSINE"))
        return ComparisonResult(COMPARISON_DONE, score, cosine=cosine)

    # ---------- revogação ----------

    @transaction.atomic
    def revoke(self, user, origin: str = "titular") -> bool:
        
        biometria = Biometria.objects.filter(usuario=user).first()
        deleted_biometria_id = biometria.id if biometria else 0
        if biometria:
            biometria.delete()

        now = timezone.now()
        revoked_consents = AceiteTermo.objects.filter(
            usuario=user,
            termo__tipo=Termo.TIPO_BIOMETRICO,
            concedido=True,
            data_revogada__isnull=True,
        ).update(data_revogada=now, data_atualizacao=now)

        if biometria or revoked_consents:
            self._audit(user.id, "BIOMETRIA_REVOGADA", "biometria", deleted_biometria_id, {
                "origem": origin,
                "template_apagado": biometria is not None,
                "consentimentos_revogados": revoked_consents,
            })
        return biometria is not None

    @transaction.atomic
    def fulfill_revocation_request(self, lgpd_request: SolicitacaoLGPD) -> SolicitacaoLGPD:
        
        if lgpd_request.tipo != SolicitacaoLGPD.TIPO_REVOGAR_BIOMETRIA:
            raise ValueError("A solicitação não é de revogação de biometria.")

        self.revoke(lgpd_request.usuario, origin="solicitacao_lgpd")

        lgpd_request.status = SolicitacaoLGPD.STATUS_ATENDIDA
        if not lgpd_request.data_resposta:
            lgpd_request.data_resposta = timezone.now()
        if not lgpd_request.resposta_dpo:
            lgpd_request.resposta_dpo = "Template biométrico apagado e consentimento revogado."
        lgpd_request.save()
        return lgpd_request

    # ---------- auditoria ----------

    def _audit(self, author_id, action, table, row_id, payload):
        self._audit_log.register({
            "autor_id": author_id,
            "origem": AUDIT_ORIGIN,
            "acao": action,
            "tabela": table,
            "linha_tabela_id": row_id,
            "payload": payload,
        })