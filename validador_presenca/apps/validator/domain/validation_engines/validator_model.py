from abc import ABC, abstractmethod
from ..values.factor_result import FactorResult

class ValidatorModel(ABC):
    name: str
    weight: float
    block: bool

    @abstractmethod # a seta aqui serve para demosntrar o padrão que a resposta desse metodo irá seguir, ma snão é uma regra e nem trava nada.
    def validate(self, factor_result: str) -> FactorResult:
        raise NotImplementedError
