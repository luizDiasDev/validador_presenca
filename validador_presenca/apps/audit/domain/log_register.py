from apps.audit.models import AuditLog
from django.utils import timezone
import hashlib
import json


class LogResister:

    def register(self, data_log: dict):
        last_log = AuditLog.objects.order_by("-id").first()
        last_hash = last_log.hash_atual if last_log else "0" * 64

        payload = data_log.get("payload", {})

        new_hash = self._calculate_hash(
            last_hash=last_hash,
            payload=payload,
            time =  str(timezone.now())
        )

        AuditLog.objects.create(
            autor_id = data_log.get("autor_id", 0),
            origem = data_log.get("origem", ""),
            acao = data_log.get("acao", ""),
            tabela = data_log.get("tabela", ""),
            linha_tabela_id = data_log.get("linha_tabela_id", 0),
            payload = payload,
            hash_anterior = last_hash,
            hash_atual = new_hash
        )

    def _calculate_hash(self, last_hash, payload, time):
        concat = last_hash + json.dumps(payload) + time  
        #encode vai transformar o valor em bytes
        #sha256 transforma os bytes em um hash 
        #hexdigest pega o resultado de tudo e transforma em um hash de 64 caracteres
        return hashlib.sha256(concat.encode()).hexdigest()