from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult

class LivenessValidator(ValidatorModel):
    name = "liveless"
    weight = 0.2
    block = True

    def validate(self, factor_parameter: str) -> FactorResult:
        factor_parameter

        return FactorResult(
            name = self.name,
            passed = False,
            block = self.block,
            score = 0.0,
            weight = self.weight,
            reason = ""
        )