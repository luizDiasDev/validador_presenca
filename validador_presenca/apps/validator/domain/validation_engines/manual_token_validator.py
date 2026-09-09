from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult

class ManualTokenValidator(ValidatorModel):
    name = "manual_token"
    weight = 0.2
    block = True

    def validate(self, factor_parameter: str) -> FactorResult:
        factor_parameter

        return FactorResult(
            name = self.name,
            passed = True,
            block = self.block,
            score = 1.0,
            weight = self.weight,
            reason = ""
        )