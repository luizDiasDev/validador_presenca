import json
import secrets
from ..values.qr_token import QrToken

TTL_BASE = 5

class QrTokenService:
    def __init__(self,cache):
        self.cache = cache

    def gerar(self, sessao_id: int, maquina_id: int, ttl_s: int = TTL_BASE) -> QrToken:
        token = secrets.token_urlsafe(24)
        payload = json.dumps({"sessao_id": sessao_id, "maquina_id": maquina_id})
        self.cache.set(token, payload, ttl_s)
        return QrToken(
            token=token,
            sessao_id=sessao_id,
            maquina_id=maquina_id,
            ttl_s=ttl_s,
        )

    def consumir(self, token: str) -> QrToken | None:
        valor = self.cache.get(token)
        if not valor:
            return None

        if not self.cache.delete(token):
            return None

        dados = json.loads(valor)
        return QrToken(
            token=token,
            sessao_id=dados["sessao_id"],
            maquina_id=dados["maquina_id"],
        )