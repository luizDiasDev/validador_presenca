from apps.audit.models import AuditLog
import hashlib
import json


class LogResister:

    def register(self, data_log: dict):

        AuditLog.objects.create(
            autor_id = data_log.get("autor_id", ""),
            origem = data_log.get("origem", ""),
            acao = data_log.get("acao", ""),
            tabela = data_log.get("tabela", ""),
            linha_tabela_id = data_log.get("linha_tabela_id", ""),
            payload = data_log.get("payload"),
        )

    def calculate_hash(self, last_hash, time):
        concat = last_hash + json.dumps(self.data_log["payload"]) + time
        return hashlib.sha256(concat.encode()).hexdigest()