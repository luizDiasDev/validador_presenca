from dataclasses import dataclass

#Dataclass para criar uma classe simplificada apenas para armazenar informações de forma padronizada
#Frozen=True é para bloquear as alterações dos valores depois de inseridos
@dataclass(frozen=True)
class FactorResult:
    """
    Armazena os dados individuais de cada validação de forma padronizada
    """
    name: str
    passed: bool
    block: bool
    score: float
    weight: float
    reason: str = ""

#---NOTA: Se for testar, testa via Django Shell que é melhor, tem que importar desse jeito: from apps.validator.domain.factor_result import FactorResult