from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult

class QrCodeValidator(ValidatorModel):
    name = "qr_code"
    weight = 0.3
    block = True

    def __init__(self, cache_qrtokens):
        self.cache_qrtokens = cache_qrtokens

    def validate(self, factor_parameter: str)  -> FactorResult:
        token_exists =  self.cache_qrtokens.exists(factor_parameter.get("qr_code", ""))

        return FactorResult(
            name = self.name,
            passed = bool(token_exists),
            block = self.block,
            score = 1.0 if token_exists else 0.0,
            weight = self.weight,
            reason = "" if token_exists else "Token inválido ou expirado"
        )