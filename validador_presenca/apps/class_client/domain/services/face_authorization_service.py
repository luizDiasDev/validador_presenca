from dataclasses import asdict, dataclass

AUTHORIZATION_TTL_SECONDS = 120
MODE_CHECKIN = "checkin"      # o aluno já tem rosto cadastrado: comparar
MODE_ENROLLMENT = "cadastro"  # primeiro check-in: cadastrar o rosto


@dataclass(frozen=True)
class FaceAuthorization:
    presenca_id: int
    aluno_id: int
    mode: str
    base_pack: dict  # fatores já avaliados no celular (QR, localização, sessão, máquina)


class FaceAuthorizationService:
    def __init__(self, cache, ttl_seconds: int = AUTHORIZATION_TTL_SECONDS):
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    def authorize(self, maquina_id: int, authorization: FaceAuthorization) -> None:
        # uma liberação por máquina: um novo aluno na mesma máquina substitui a anterior
        self.cache.set(self._machine_key(maquina_id), asdict(authorization), self.ttl_seconds)
        self.cache.set(self._record_key(authorization.presenca_id), maquina_id, self.ttl_seconds)

    def pending_for(self, maquina_id: int) -> FaceAuthorization | None:
        data = self.cache.get(self._machine_key(maquina_id))
        return FaceAuthorization(**data) if data else None

    def is_waiting(self, presenca_id: int) -> bool:
        maquina_id = self.cache.get(self._record_key(presenca_id))
        if maquina_id is None:
            return False
        pending = self.pending_for(maquina_id)
        return pending is not None and pending.presenca_id == presenca_id

    def consume(self, maquina_id: int, presenca_id: int) -> FaceAuthorization | None:
        pending = self.pending_for(maquina_id)
        if pending is None or pending.presenca_id != presenca_id:
            return None
        self.cache.delete(self._machine_key(maquina_id))
        self.cache.delete(self._record_key(presenca_id))
        return pending

    @staticmethod
    def _machine_key(maquina_id: int) -> str:
        return f"adsum:maquina:{maquina_id}:liberacao_rosto"

    @staticmethod
    def _record_key(presenca_id: int) -> str:
        return f"adsum:presenca:{presenca_id}:maquina_liberada"
