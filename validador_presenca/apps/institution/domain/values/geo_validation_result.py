from dataclasses import dataclass

@dataclass(frozen=True)
class GeoValidationResult:
    valida: bool # aluno está dentro ou não do raio
    distancia_m: float
    campus_id: int
    motivo: str = ""