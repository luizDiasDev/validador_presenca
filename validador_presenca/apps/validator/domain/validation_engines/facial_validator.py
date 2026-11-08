from apps.biometrics import conf
from apps.biometrics.domain.services.biometric_service import COMPARISON_DONE, BiometricService

from ..values.factor_result import FactorResult
from .validator_model import ValidatorModel

class FacialValidator(ValidatorModel):
    name = "facial"
    weight = 0.70
    block = True

    def __init__(self, service: BiometricService | None = None):
        self._service = service

    @property
    def service(self) -> BiometricService:
        if self._service is None:
            self._service = BiometricService()
        return self._service

    def validate(self, factor_parameter: dict) -> FactorResult:
        student_id = factor_parameter.get("aluno_id")
        captured_embedding = factor_parameter.get("embedding")

        if not student_id:
            return self._result(passed=False, score=0.0, reason="Aluno não identificado")

        if captured_embedding is None:
            return self._needs_review("Rosto não capturado (falha na webcam ou no executável)")

        comparison = self.service.compare(student_id, captured_embedding)
        if comparison.status != COMPARISON_DONE:
            return self._needs_review(comparison.reason)

        if factor_parameter.get("biometric_enrolled_in_this_checkin"):
            
            return self._needs_review(
                "Primeiro check-in após o cadastro facial: confirmar a identidade do aluno",
                score=comparison.score,
            )

        if comparison.score < conf.get_setting("FACIAL_SAFEGUARD"):
            return self._result(passed=False, score=comparison.score, reason="Rosto não confere com o cadastro")

        return self._result(passed=True, score=comparison.score, reason="")

    def _result(self, passed: bool, score: float, reason: str) -> FactorResult:
        return FactorResult(
            name=self.name, passed=passed, block=self.block,
            score=score, weight=self.weight, reason=reason,
        )

    def _needs_review(self, reason: str, score: float = 0.0) -> FactorResult:
        return FactorResult(
            name=self.name, passed=False, block=self.block,
            score=score, weight=self.weight, reason=reason, needs_review=True,
        )