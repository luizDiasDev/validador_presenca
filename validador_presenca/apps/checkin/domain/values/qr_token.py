from dataclasses import dataclass

@dataclass(frozen=True)
class QrToken:
    token: str
    sessao_id: int
    maquina_id: int
    ttl_s: int | None = None