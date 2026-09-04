from dataclasses import dataclass
from enum import Enum

#Enum para definir valores mapeados e fixos
class Veridict(Enum):
    """
    Disponibiliza os valores fixos do veredito das validações realizadas
    """
    APPROVED ="APPROVED"
    PENDING = "PENDING"
    REJECTED ="REJECTED"

#Dataclass para criar uma classe simplificada apenas para armazenar informações de forma padronizada
#Frozen=True é para bloquear as alterações dos valores depois de inseridos
@dataclass(frozen=True)
class ValidationResponseStorage:
    """
    Armazena os dados individuais de cada validação de forma padronizada
    """
    name: str
    passed: bool
    block: bool
    score: float
    weight: float
    reason: str = ""

#---NOTA: Se for testar, testa via Django Shell que é melhor, tem que importar desse jeito: from validator.domain.values import ValidationResponseStorage