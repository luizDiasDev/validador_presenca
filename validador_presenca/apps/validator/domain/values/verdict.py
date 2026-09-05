from enum import Enum

#Enum para definir valores mapeados e fixos
class Verdict(Enum):
    """
    Disponibiliza os valores fixos do veredito das validações realizadas
    """
    APPROVED ="APPROVED"
    PENDING = "PENDING"
    REJECTED ="REJECTED"