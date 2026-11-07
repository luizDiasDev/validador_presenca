from apps.biometrics import conf
from apps.biometrics.domain.calibration import LIVENESS_STATUS_OK, liveness_to_score

from ..values.factor_result import FactorResult
from .validator_model import ValidatorModel

class LivenessValidator(ValidatorModel):
    name = "liveness"
    weight = 0.30
    block = False

    def validate(self, factor_parameter: dict) -> FactorResult:
        reading = liveness_to_score(
            factor_parameter.get("liveness_score"),
            factor_parameter.get("liveness_status", LIVENESS_STATUS_OK),
            factor_parameter.get("challenge_passed"),
            approval_threshold=conf.get_setting("LIVENESS_APPROVAL"),
        )
        return FactorResult(
            name=self.name,
            passed=reading.approved,
            block=self.block,
            score=reading.score,
            weight=self.weight,
            reason=reading.reason,
        )