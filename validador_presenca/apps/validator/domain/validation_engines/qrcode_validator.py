from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult

class QrCodeValidator(ValidatorModel):
    name = "qr_code"
    weight = 0.3
    block = True


    def validate(self, factor_parameter: str)  -> FactorResult:
        token_exists =  factor_parameter.get("qr_code", False)

        return FactorResult(
            name = self.name,
            passed = token_exists,
            block = self.block,
            score = 1.0 if token_exists else 0.0,
            weight = self.weight,
            reason = "" if token_exists else "Token inválido ou expirado"
        )