from .validator_model import ValidatorModel
from ..values.factor_result import FactorResult


class GeoValidator(ValidatorModel):

    name = "geo"
    weight = 0.0 # Info bloqueante, por isso da 0.0, o peso em si não é relevante
    block = True # Se não tiver dentro do raio, nao deixa prosseguir para os demais validadores

    def validate(self, factor_parameter: dict) -> FactorResult:
        geo_valida = factor_parameter.get("geo_valida", False) # Consome o campo 'geo_valida'
        motivo_bruto = factor_parameter.get("geo_motivo", "")

        return FactorResult(
            name=self.name,
            passed=geo_valida,
            block=self.block,
            score=1.0 if geo_valida else 0.0, # esperado pelo FactorResult
            weight=self.weight,
            reason="" if geo_valida else (
                motivo_bruto or "Localização fora do raio do campus"
            ),
        )