from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult

class QrCodeValidator(ValidatorModel):
    name = "qr_code"
    weight = 0.3
    block = True

    def validate(self, factor_result: str):
        factor_result

        return FactorResult(
            name = self.name,
            passed = False,
            block = self.block,
            score = 0.0,
            weight = self.weight,
            reason = ""
        )