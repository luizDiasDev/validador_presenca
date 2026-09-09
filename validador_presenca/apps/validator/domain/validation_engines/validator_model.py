from abc import ABC, abstractmethod
from ..values.factor_result import FactorResult

class ValidatorModel(ABC):
    name: str
    weight: float
    block: bool

    @abstractmethod
    def validate(self, factor_parameter: str) -> FactorResult:
        raise NotImplementedError
